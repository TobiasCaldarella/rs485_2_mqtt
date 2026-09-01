#!/usr/bin/python3

class Dimmers:
    def __init__(self, num_channels, mqtt, topic, addr):
        #self.reg = register
        self.tr = None
        self.num_channels = num_channels
        self.mqtt = mqtt
        self.topic = topic
        self.addr = addr
        
        # register mqtt topics
        for i in range(0,self.num_channels):
            topic = self.topic + '/Dimmers/set/' + str(i)
            self.mqtt.register_topic(topic, lambda client, userdata, msg, i=i: self.set_value(i,int(float(msg.payload.decode("utf-8")))))

    def set_transceiver(self, transceiver):
        self.tr = transceiver
        
    def set_value(self, channel, val):
        if channel >= 8 or val > 255:
            print("channel %i or value %i invalid" % (channel, val))
        else:
            print("setting channel %i to %i" % (channel, val))
            req = bytes([0x80, channel, val])
            rsp = self.tr.req_resp(self.addr, req, False)
            if rsp is None:
                print('Did not get any response!')
            elif rsp[0] != 0x80 or rsp[1] != channel:
                print("did not get expected response. got: 0x%x 0x%x 0x%x" % (rsp[0], rsp[1], rsp[2]))

    def send_mqtt_update(self, channel, val, mqtt, topic):
        mqtt.pub(topic + '/Dimmers/' + str(channel), val)

    def update(self, addr, mqtt, topic, force):
        req = bytes([0x0, 0x0, 0x0])
        rsp = self.tr.req_resp(addr, req, False)
        if rsp is None or len(rsp) < 2:
            print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x0))
        else:
            val = rsp[2]
            if val == 0x4:
                channel = rsp[1]
                print("got new value ping for channel %i" % channel)
                req = bytes([0x4, channel, 0x0])
                rsp = self.tr.req_resp(addr, req, False)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x4))
                else:
                    val = rsp[2]
                    self.send_mqtt_update(channel, val, mqtt, topic)
            
