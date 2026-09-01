#!/usr/bin/python3

class Katzenfenster:
    def __init__(self, mqtt, topic, addr):
        self.tr = None
        self.last_val = None
        self.last_motor_current = None
        self.idx = 0
        self.succ_cnt = 0
        self.err_cnt = 0
        # register mqtt topics
        self.mqtt = mqtt
        self.topic = topic
        self.addr = addr
        self.mqtt.register_topic(self.topic + '/command', lambda client, userdata, msg: self.sendCommand(msg.payload.decode("utf-8")))
        self.mqtt.register_topic(self.topic + '/ignore_sensor_in', lambda client, userdata, msg: self.ignore_sensor('in', msg.payload.decode("utf-8")))
        self.mqtt.register_topic(self.topic + '/ignore_sensor_out', lambda client, userdata, msg: self.ignore_sensor('out', msg.payload.decode("utf-8")))
        self.sensor_mask = 0b11

    def set_transceiver(self, transceiver):
        self.tr = transceiver

    def send_sensor_mask(self):
        req = bytes([0x02, 0xab, self.sensor_mask])
        rsp = self.tr.req_resp(self.addr, req, False)
        print("set sensor mask %d" % self.sensor_mask)
        if rsp is None:
            print('Did not get any response')
        elif rsp != req:
            print("Did not get expected response ('%s'). got: '%s'" % (req, rsp))

    def ignore_sensor(self, sensor, ignore):
        active = ignore not in ["true","True","TRUE","1",1]
        if sensor == "in":
            self.sensor_mask = (self.sensor_mask & 0b10) | active
        elif sensor == "out":
            self.sensor_mask = (self.sensor_mask & 0b01) | active<<1
        else:
            print("sensor '%s' not allowed here" % sensor)
            return

        self.send_sensor_mask()
    
    def sendCommand(self, command):
        print("issueing command '%s' to Katzenklappe" % command)
        cmd = None
        if command in ["open", "Open", "OPEN"]:
            cmd = 0x01
        elif command in ["close", "Close", "CLOSE"]:
            cmd = 0x02
        elif command in ["stop", "Stop", "STOP"]:
            cmd = 0x00
        else:
            print("invalid command")

        if cmd is not None:
            keep_open_min = 10
            req = bytes([0x04, keep_open_min, cmd]) # 0x0a = keep open for 10 long minutes
            rsp = self.tr.req_resp(self.addr, req, False)
            if rsp is None:
                print('Did not get any response!')
            elif rsp[0] != 0x04 or rsp[1] != keep_open_min or rsp[2] != cmd:
                print("did not get expected response. got: 0x%x 0x%x 0x%x" % (rsp[0], rsp[1]))

    def send_mqtt_motor_current(self, current, mqtt, topic):
        mqtt.pub(topic + '/motor_current', int(current))

    def send_mqtt_update(self, pin, bank_vals, mqtt, topic):
        val = (bank_vals & (1 << pin)) != 0
        if pin == 0:
            if val == False:
                to_send = 'Opened'
            else:
                to_send = 'Closed'
            mqtt.pub(topic + '/fensterOeffnung', to_send)
        elif pin == 1:
            mqtt.pub(topic + '/opening', val)
        elif pin == 2:
            mqtt.pub(topic + '/closing', val)
        elif pin == 3:
            mqtt.pub(topic + '/sensorIn', val)
        elif pin == 4:
            mqtt.pub(topic + '/sensorOut', val)
        elif pin == 5:
            mqtt.pub(topic + '/sensorInIgnored', val == False)
        elif pin == 6:    
            mqtt.pub(topic + '/sensorOutIgnored', val == False)

    def send_mqtt_update_movement(self, opening, closing, mqtt, topic):
        movement = 'Stopped'
        if opening:
            movement = 'Opening'
        elif closing:
            movement = 'Closing'
        if opening and closing:
            movement = 'Error'
        mqtt.pub(topic + '/movement', movement)

    def update(self, addr, mqtt, topic, force):
        req = bytes([0x1, self.idx, 0x0])
        rsp = self.tr.req_resp(addr, req, False)
        #print(rsp)
        if rsp is None:
            self.err_cnt = self.err_cnt + 1
            #mqtt.pub(topic + '/error_counter', self.err_cnt)
            
            #print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, self.reg))
        #elif rsp[1] != self.idx:
        #    print("Wrong idx in response: expected: %d got: %d; addr 0x%x!" % (self.idx, rsp[1], addr))
        else:
            val = rsp[2]
            motor_current=rsp[1]
            self.succ_cnt = self.succ_cnt + 1
            update_movement = False;
            #mqtt.pub(topic + '/success_counter', self.succ_cnt)
            #print("val: %x" % val)
            if val != self.last_val or force is True:
                if self.last_val is None or force is True:
                    update_movement = True
                    #print("last val: '<not-set> new val: %x; addr 0x%x, reg 0x%x" % (val, addr, self.reg))
                    for i in range(0,8):
                        self.send_mqtt_update(i, val, mqtt, topic)
                else:
                    #print("last val: %x new val: %x; addr 0x%x, reg 0x%x" % (self.last_val, val, addr, self.reg))
                    for i in range(0,8):
                        new = val & (1<<i)
                        old = self.last_val & (1<<i)
                        if new != old or force is True:
                            self.send_mqtt_update(i, val, mqtt, topic)
                            if i == 1 or i == 2:
                                update_movement = True
                self.last_val = val
            if motor_current != self.last_motor_current or force is True:
                self.send_mqtt_motor_current(motor_current, mqtt, topic)
                self.last_motor_current = motor_current
            if update_movement:
                self.send_mqtt_update_movement(val & 1<<1, val & 1<<2, mqtt, topic)
        
        if self.idx % 32 == 0:
            mqtt.pub(topic + '/error_rate', (self.err_cnt*100)/(self.err_cnt + self.succ_cnt))
            self.err_cnt = 0
            self.succ_cnt = 0
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

