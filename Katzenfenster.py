#!/usr/bin/python3
import time

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
        self.mqtt.register_topic(self.topic + '/max_moving_current', lambda client, userdata, msg: self.set_max_current('moving', msg.payload.decode("utf-8")))
        self.mqtt.register_topic(self.topic + '/max_stop_current', lambda client, userdata, msg: self.set_max_current('stop', msg.payload.decode("utf-8")))
        self.sensor_mask = 0b11

    def set_transceiver(self, transceiver):
        self.tr = transceiver


    def set_max_current(self, current_type, val):
        stop_current = moving_current = 0x0
        if current_type == 'stop':
            stop_current = int(val)
        if current_type == 'moving':
            moving_current = int(val)
        req = bytes([0x10, moving_current, stop_current])
        rsp = self.tr.req_resp(self.addr, req, False)
        if rsp is None:
            print('Did not get any response')
        elif rsp[0] != req[0]:
            print("Did not get expected response ('%s'). got: '%s'. Only first byte must match!" % (req, rsp))
        print("max_moving_current %i max_stop_current %i" % (rsp[1], rsp[2]))

    def send_sensor_mask(self):
        req = bytes([0x02, 0xab, self.sensor_mask])
        rsp = self.tr.req_resp(self.addr, req, False)
        #print("set sensor mask %d" % self.sensor_mask)
        if rsp is None:
            print('Did not get any response')
        elif rsp != req:
            print("Did not get expected response ('%s'). got: '%s'" % (req, rsp))

    def ignore_sensor(self, sensor, ignore):
        active = ignore not in ["true","True","TRUE","1",1,"On","ON","on"]
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
                to_send = 'OPEN'
            else:
                to_send = 'CLOSED'
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
            mqtt.pub(topic + '/sensor_in_ignored', val == False)
        elif pin == 6:    
            mqtt.pub(topic + '/sensor_out_ignored', val == False)

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
        get_state = force
        get_error = force
        if force is False:
            req = bytes([0x0, self.idx, 0x0])
            rsp = self.tr.req_resp(addr, req, False)
            if rsp is None or len(rsp) < 3: 
                self.err_cnt = self.err_cnt + 1
                return
            get_state = rsp[2] & 0x1
            get_error = rsp[2] & 0x8

        if get_state > 0:
            self.get_state(addr, mqtt, topic, force)
        if get_error > 0:
            self.get_error(addr, mqtt, topic, force)

    def get_error(self, addr, mqtt, topic, force):
        req = bytes([0x8, self.idx, 0x0])
        rsp = self.tr.req_resp(addr, req, False)
        if rsp is None or len(rsp) < 3:
            self.err_cnt = self.err_cnt + 1
            return
        err_code = rsp[2]
        if err_code == 0:
            return
        err_time = rsp[1]
        print("Katzenfenster Error! code: %d time_from_movement_start: %d" % (err_code, err_time))
 
    def get_state(self, addr, mqtt, topic, force):
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
            if motor_current > 0 or val & 0b10 or val & 0b100:
                tt = time.time()
                print("time %f, current: %d, value %x" % (tt, motor_current, val))
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

        if force is True:
            self.send_sensor_mask()  # has to be repeated once in a while, will be reset otherwise!

