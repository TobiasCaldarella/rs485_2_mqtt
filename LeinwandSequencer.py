#!/usr/bin/python3
import os

class LeinwandSequencer:
    def __init__(self):
        #self.reg = register
        self.tr = None
        self.sensor1 = 0
        self.sensor2 = 0
        self.motor   = 0
        self.state   = 0

        # register mqtt topics
        #for i in range(0,self.num_channels):
        #    topic = self.topic + '/Dimmers/set/' + str(i)
        #    self.mqtt.register_topic(topic, lambda client, userdata, msg, i=i: self.set_value(i,int(float(msg.payload.decode("utf-8")))))

    def set_transceiver(self, transceiver):
        self.tr = transceiver
        
#    def set_value(self, channel, val):
#        if channel >= 8 or val > 255:
#            print("channel %i or value %i invalid" % (channel, val))
#        else:
#            print("setting channel %i to %i" % (channel, val))
#            req = bytes([0x80, channel, val])
#            rsp = self.tr.req_resp(self.addr, req, False)
#            if rsp is None:
#                print('Did not get any response!')
#            elif rsp[0] != 0x80 or rsp[1] != channel:
#                print("did not get expected response. got: 0x%x 0x%x 0x%x" % (rsp[0], rsp[1], rsp[2]))

    def send_mqtt_update(self, channel, val, mqtt, topic):
        mqtt.pub(topic + str(channel), val)

    def send_mqtt_sensor_update(self, bank, pin, bank_val, mqtt, topic):
        if (bank_val & (1 << pin)) == 0):
            val = '1'
        else:
            val = '0'

        mqtt.pub(topic + '/sensor/' + str(bank) + '/' + str(pin), val)

        SENSORS = [['KLAPPE_UNTEN_RECHTS','KLAPPE_UNTEN_LINKS','SEGEL_VORNE_RECHTS','SEGEL_VORNE_LINKS','SEGEL_HINTEN_RECHTS','SEGEL_HINTEN_LINKS','LW_UNTEN','LW_OBEN'],['TUER','LW_MITTE','KLAPPE_OBEN_RECHTS','KLAPPE_OBEN_LINKS','n-a','n-a','n-a','n-a']]
        mqtt.pub(topic + '/sensor/' + SENSORS[bank][pin], val)

    def send_mqtt_motor_active_update(self, bank_val, mqtt, topic):
        MOTORS = {4:'KLAPPEN_RUNTER',5:'KLAPPEN_RAUF',6:'LW_RUNTER',8:'LW_RAUF',7:'SEGEL_VOR',9:'SEGEL_RUECK',15:'LW_RUNTER2',16:'LW_RAUF2',0xff:'NONE'}
        if bank_val not in MOTORS:
            active = 'INVALID'
        else:
            active = MOTORS[bank_val]
        mqtt.pub(topic + '/motor_active', active)

    def send_mqtt_state_update(self, state, mqtt, topic):
        mqtt.pub(topic + '/state_num', state)
        STATES = ['IDLE', 'BEGIN', 'KLAPPEN_1',	'SEGEL_1', 'LW', 'LW2',	'SEGEL_2', 'KLAPPEN_2',	'END', 'IDLE2']
        mqtt.pub(topic + '/state', STATES[state])
        if os.environ.get('DEBUG'):
            print("State: '%s'" % (STATES[state]))

    def send_mqtt_direction_update(self, direction, mqtt, topic):
        DIRECTIONS = ['STOPP', 'LW_RAUF', 'LW_RUNTER']
        if direction > 2:
            print("ERR: direction = %i" % direction)
            return
        mqtt.pub(topic + '/direction', DIRECTIONS[direction])
        if os.environ.get('DEBUG'):
            print("Direction: '%s'" % (DIRECTIONS[direction]))

    def send_mqtt_button_short_pressed(self, mqtt, topic):
        mqtt.pub(topic + '/button', '1')
        mqtt.pub(topic + '/button', '0')

    def update(self, addr, mqtt, topic, force):
        req = bytes([0x0, 0x0, 0x0]) # send ping
        rsp = self.tr.req_resp(addr, req, False)
        # todo: force has to request everything, override response with 0xff?
        if rsp is None or len(rsp) < 2:
            print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x0))
            return False
        else:
            ret = True
            val = rsp[2]
            if val & 0x40:
                if os.environ.get('DEBUG'):
                    print("got button short pressed")
                self.send_mqtt_button_short_pressed(mqtt, topic)
            if val & 0x01 or force:
                if os.environ.get('DEBUG'):
                    print("Sensor state changed or update forced")
                req = bytes([0x01, 0x0, 0x0])
                rsp = self.tr.req_resp(addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x01))
                    ret = False
                else:
                    val1 = rsp[2] #sic
                    val2 = rsp[1] # sic!
                    if force is True or self.sensor1 != val1:
                        for i in range(0,8):
                            if force is True or (val1 & (1<<i)) != (self.sensor1 & (1<<i)):
                                self.send_mqtt_sensor_update(0, i, val1, mqtt, topic)
                    
                    if force is True or self.sensor2 != val2:
                        for i in range(0,8):
                            if force is True or (val2 & (1<<i)) != (self.sensor2 & (1<<i)):
                                self.send_mqtt_sensor_update(1, i, val2, mqtt, topic)
                    self.sensor1 = val1
                    self.sensor2 = val2
            
            if val & 0x02 or force:
                if os.environ.get('DEBUG'):
                    print("Motor state changed or update forced")
                req = bytes([0x02, 0x0, 0x0])
                rsp = self.tr.req_resp(addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x01))
                    ret = False
                else:
                    val = rsp[2]
                    if force is True or self.motor != val:
                        self.send_mqtt_motor_active_update(val, mqtt, topic)

            if val & 0x04 or force:
                if os.environ.get('DEBUG'):
                    print("State-machine changed or update forced")
                req = bytes([0x04, 0x0, 0x0])
                rsp = self.tr.req_resp(addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x01))
                    ret = False
                else:
                    val = rsp[2]
                    if force is True or (val & (0b11 << 4)) != (self.state & (0b11 << 4)):
                        self.send_mqtt_direction_update((val&(0b11<<4)>>4), mqtt, topic)
                    if force is True or (val & 0x0f) != (self.state & 0x0f):
                        self.send_mqtt_state_update(val&0x0f, mqtt, topic)

            if val & 0x10:
                req = bytes([0x10, 0x0, 0x0])
                rsp = self.tr.req_resp(addr, req, False)
                print("Got error: 0x%x" % rsp[2])
            
            return ret

