#!/usr/bin/python3
import time

class Katzenfenster:
    def __init__(self):
        self.rs485 = None
        self.last_val = None
        self.last_motor_current = None
        self.idx = 0
        # register mqtt topics
        self.sensor_mask = 0b11

    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev
        self.rs485.mqtt.register_topic(self.rs485.topic + '/command', lambda client, userdata, msg: self.sendCommand(msg.payload.decode("utf-8")))
        self.rs485.mqtt.register_topic(self.rs485.topic + '/ignore_sensor_in', lambda client, userdata, msg: self.ignore_sensor('in', msg.payload.decode("utf-8")))
        self.rs485.mqtt.register_topic(self.rs485.topic + '/ignore_sensor_out', lambda client, userdata, msg: self.ignore_sensor('out', msg.payload.decode("utf-8")))
        self.rs485.mqtt.register_topic(self.rs485.topic + '/max_moving_current', lambda client, userdata, msg: self.set_max_current('moving', msg.payload.decode("utf-8")))
        self.rs485.mqtt.register_topic(self.rs485.topic + '/max_stop_current', lambda client, userdata, msg: self.set_max_current('stop', msg.payload.decode("utf-8")))

    def set_max_current(self, current_type, val):
        stop_current = moving_current = 0x0
        if current_type == 'stop':
            stop_current = int(val)
        if current_type == 'moving':
            moving_current = int(val)
        req = bytes([0x10, moving_current, stop_current])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        if rsp is None:
            print('Did not get any response')
        elif rsp[0] != req[0]:
            print("Did not get expected response ('%s'). got: '%s'. Only first byte must match!" % (req, rsp))
        print("max_moving_current %i max_stop_current %i" % (rsp[1], rsp[2]))

    def send_sensor_mask(self):
        req = bytes([0x02, 0xab, self.sensor_mask])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
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
            rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
            if rsp is None:
                print('Did not get any response!')
            elif rsp[0] != 0x04 or rsp[1] != keep_open_min or rsp[2] != cmd:
                print("did not get expected response.")

    def send_mqtt_motor_current(self, current):
        self.rs485.mqtt.pub(self.rs485.topic + '/motor_current', int(current))

    def send_mqtt_update(self, pin, bank_vals):
        val = (bank_vals & (1 << pin)) != 0
        if pin == 0:
            if val == False:
                to_send = 'OPEN'
            else:
                to_send = 'CLOSED'
            self.rs485.mqtt.pub(self.rs485.topic + '/fensterOeffnung', to_send)
        elif pin == 1:
            self.rs485.mqtt.pub(self.rs485.topic + '/opening', val)
        elif pin == 2:
            self.rs485.mqtt.pub(self.rs485.topic + '/closing', val)
        elif pin == 3:
            self.rs485.mqtt.pub(self.rs485.topic + '/sensorIn', val)
        elif pin == 4:
            self.rs485.mqtt.pub(self.rs485.topic + '/sensorOut', val)
        elif pin == 5:
            self.rs485.mqtt.pub(self.rs485.topic + '/sensor_in_ignored', val == False)
        elif pin == 6:    
            self.rs485.mqtt.pub(self.rs485.topic + '/sensor_out_ignored', val == False)

    def send_mqtt_update_movement(self, opening, closing):
        movement = 'Stopped'
        if opening:
            movement = 'Opening'
        elif closing:
            movement = 'Closing'
        if opening and closing:
            movement = 'Error'
        self.rs485.mqtt.pub(self.rs485.topic + '/movement', movement)

    def update(self, force):
        ret = True
        get_state = force
        get_error = force
        if force is False:
            req = bytes([0x0, self.idx, 0x0])
            rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
            if rsp is None or len(rsp) < 3: 
                return False
            get_state = rsp[2] & 0x1
            get_error = rsp[2] & 0x8

        if get_state > 0:
            ret = self.get_state(force)
        if get_error > 0:
            ret = ret & self.get_error(force)
        return ret

    def get_error(self, force):
        req = bytes([0x8, self.idx, 0x0])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        if rsp is None or len(rsp) < 3:
            return False
        err_code = rsp[2]
        if err_code == 0:
            return True
        err_time = rsp[1]
        print("Katzenfenster Error! code: %d time_from_movement_start: %d" % (err_code, err_time))
        return True
 
    def get_state(self, force):
        req = bytes([0x1, self.idx, 0x0])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        #print(rsp)
        if rsp is None:
            return False
        else:
            val = rsp[2]
            motor_current=rsp[1]
            if motor_current > 0 or val & 0b10 or val & 0b100:
                tt = time.time()
                print("time %f, current: %d, value %x" % (tt, motor_current, val))
            update_movement = False;
            #print("val: %x" % val)
            if val != self.last_val or force is True:
                if self.last_val is None or force is True:
                    update_movement = True
                    for i in range(0,8):
                        self.send_mqtt_update(i, val)
                else:
                    for i in range(0,8):
                        new = val & (1<<i)
                        old = self.last_val & (1<<i)
                        if new != old or force is True:
                            self.send_mqtt_update(i, val)
                            if i == 1 or i == 2:
                                update_movement = True
                self.last_val = val
            if motor_current != self.last_motor_current or force is True:
                self.send_mqtt_motor_current(motor_current)
                self.last_motor_current = motor_current
            if update_movement:
                self.send_mqtt_update_movement(val & 1<<1, val & 1<<2)
       
            if force is True:
                self.send_sensor_mask()  # has to be repeated once in a while, will be reset otherwise!
 
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

        return True

