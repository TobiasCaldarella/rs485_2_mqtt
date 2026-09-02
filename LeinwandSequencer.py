#!/usr/bin/python3
import os

class LeinwandSequencer:
    def __init__(self):
        #self.reg = register
        self.rs485   = None
        self.sensor1 = 0
        self.sensor2 = 0
        self.motor   = 0
        self.state   = 0
        
    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev
        
        self.rs485.mqtt.register_topic(self.rs485.topic + "/command", lambda client, userdata, msg: self.send_command_to_device(msg.payload.decode("utf-8")))
    
    def send_command_to_device(self, command):
        print("issueing command '%s' to LeinwandSequencer" % command)
        if command in ["open", "Open", "OPEN", "up", "Up", "UP", "0"]:
            cmd = 0x01
        elif command in ["close", "Close", "CLOSE", "down", "Down", "DOWN", "100"]:
            cmd = 0x02
        elif command in ["stop", "Stop", "STOP", "X", "x"]:
            cmd = 0x00
        else:
            print("invalid command")
            return
        
        req = bytes([0x08, 0x00, cmd]) 
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        if rsp is None:
            print('Did not get any response!')
        elif rsp[0] != 0x08 or rsp[2] != cmd:
            print("did not get expected response")

    def send_mqtt_sensor_update(self, bank, pin, bank_val):
        if (bank_val & (1 << pin)) == 0:
            val = '1'
        else:
            val = '0'

        self.rs485.mqtt.pub(self.rs485.topic + '/sensor/' + str(bank) + '/' + str(pin), val)

        SENSORS = [['KLAPPE_UNTEN_RECHTS','KLAPPE_UNTEN_LINKS','SEGEL_VORNE_RECHTS','SEGEL_VORNE_LINKS','SEGEL_HINTEN_RECHTS','SEGEL_HINTEN_LINKS','LW_UNTEN','LW_OBEN'],['TUER','LW_MITTE','KLAPPE_OBEN_RECHTS','KLAPPE_OBEN_LINKS','n-a','n-a','n-a','n-a']]
        self.rs485.mqtt.pub(self.rs485.topic + '/sensor/' + SENSORS[bank][pin], val)

    def send_mqtt_motor_active_update(self, bank_val):
        MOTORS = {4:'KLAPPEN_RUNTER',5:'KLAPPEN_RAUF',6:'LW_RUNTER',8:'LW_RAUF',7:'SEGEL_VOR',9:'SEGEL_RUECK',15:'LW_RUNTER2',16:'LW_RAUF2',0xff:'NONE'}
        if bank_val not in MOTORS:
            active = 'INVALID'
        else:
            active = MOTORS[bank_val]
        self.rs485.mqtt.pub(self.rs485.topic + '/motor_active', active)

    def send_mqtt_state_update(self, state):
        self.rs485.mqtt.pub(self.rs485.topic + '/state_num', state)
        if state > 9:
            print("Invalid state %d" % state)
            return
        # 'IDLE' = leinwand unten, 'IDLE2' = leinwand oben
        STATES = [['IDLE',100], ['BEGIN',95], ['KLAPPEN_1',85], ['SEGEL_1',70], ['LW',50], ['LW2',45], ['SEGEL_2',25], ['KLAPPEN_2',10], ['END',5], ['IDLE2',0]]
        self.rs485.mqtt.pub(self.rs485.topic + '/state', STATES[state][0])
        self.rs485.mqtt.pub(self.rs485.topic + '/position', STATES[state][1])
        if os.environ.get('DEBUG'):
            print("State: '%s'" % (STATES[state]))
        

    def send_mqtt_direction_update(self, direction):
        DIRECTIONS = ['STOP', 'UP', 'DOWN']
        if direction > 2:
            print("ERR: direction = %i" % direction)
            return
        self.rs485.mqtt.pub(self.rs485.topic + '/direction', DIRECTIONS[direction])
        if os.environ.get('DEBUG'):
            print("Direction: '%s'" % (DIRECTIONS[direction]))

    def send_mqtt_button_short_pressed(self):
        self.rs485.mqtt.pub(self.rs485.topic + '/button', '1')
        self.rs485.mqtt.pub(self.rs485.topic + '/button', '0')

    def update(self, force):
        req = bytes([0x0, 0x0, 0x0]) # send ping
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        # todo: force has to request everything, override response with 0xff?
        if rsp is None or len(rsp) < 2:
            print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x0))
            return False
        else:
            ret = True
            val = rsp[2]
            if val & 0x40:
                if os.environ.get('DEBUG'):
                    print("got button short pressed")
                self.send_mqtt_button_short_pressed()
            if val & 0x01 or force:
                if os.environ.get('DEBUG'):
                    print("Sensor state changed or update forced")
                req = bytes([0x01, 0x0, 0x0])
                rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x01))
                    ret = False
                else:
                    val1 = rsp[2] #sic
                    val2 = rsp[1] # sic!
                    if force is True or self.sensor1 != val1:
                        for i in range(0,8):
                            if force is True or (val1 & (1<<i)) != (self.sensor1 & (1<<i)):
                                self.send_mqtt_sensor_update(0, i, val1)
                    
                    if force is True or self.sensor2 != val2:
                        for i in range(0,8):
                            if force is True or (val2 & (1<<i)) != (self.sensor2 & (1<<i)):
                                self.send_mqtt_sensor_update(1, i, val2)
                    self.sensor1 = val1
                    self.sensor2 = val2
            
            if val & 0x02 or force:
                if os.environ.get('DEBUG'):
                    print("Motor state changed or update forced")
                req = bytes([0x02, 0x0, 0x0])
                rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x01))
                    ret = False
                else:
                    new_motor = rsp[2]
                    if force is True or self.motor != new_motor:
                        self.send_mqtt_motor_active_update(new_motor)
                        self.motor = new_motor

            if val & 0x04 or force:
                if os.environ.get('DEBUG'):
                    print("State-machine changed or update forced")
                req = bytes([0x04, 0x0, 0x0])
                rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x01))
                    ret = False
                else:
                    new_state = rsp[2]
                    if force is True or (new_state & (0b11 << 4)) != (self.state & (0b11 << 4)):
                        self.send_mqtt_direction_update((new_state>>4)&0b11)
                    if force is True or (new_state & 0x0f) != (self.state & 0x0f):
                        self.send_mqtt_state_update(new_state&0x0f)
                    self.state = new_state;

            if val & 0x10:
                req = bytes([0x10, 0x0, 0x0])
                rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
                print("Got error: 0x%x" % rsp[2])
            
            return ret

