#!/usr/bin/python3

class Dimmers:
    def __init__(self, num_channels):
        #self.reg = register
        self.rs485 = None
        self.num_channels = num_channels
        
    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev
        # register mqtt topics
        for i in range(0,self.num_channels):
            topic = self.rs485.topic + '/Dimmers/set/' + str(i)
            self.rs485.mqtt.register_topic(topic, lambda client, userdata, msg, i=i: self.set_value(i,int(float(msg.payload.decode("utf-8")))))

    def set_value(self, channel, val):
        if channel >= 8 or val > 255:
            print("channel %i or value %i invalid" % (channel, val))
        else:
            print("setting channel %i to %i" % (channel, val))
            req = bytes([0x80, channel, val])
            rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
            if rsp is None:
                print('Did not get any response!')
            elif rsp[0] != 0x80 or rsp[1] != channel:
                print("did not get expected response. got: 0x%x 0x%x 0x%x" % (rsp[0], rsp[1], rsp[2]))

    def send_mqtt_update(self, channel, val, mqtt, topic):
        mqtt.pub(topic + '/Dimmers/' + str(channel), val)

    def update(self, force):
        req = bytes([0x0, 0x0, 0x0])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        if rsp is None or len(rsp) < 2:
            print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x0))
            return False
        else:
            val = rsp[2]
            if val == 0x4:
                channel = rsp[1]
                print("got new value ping for channel %i" % channel)
                req = bytes([0x4, channel, 0x0])
                rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (self.rs485.addr, 0x4))
                else:
                    val = rsp[2]
                    self.send_mqtt_update(channel, val, self.rs485.mqtt, self.rs485.topic)
        return True
