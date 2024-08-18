#!/usr/bin/python3

class Dimmers:
    def __init__(self, num_channels):
        #self.reg = register
        self.tr = None
        self.num_channels = num_channels

    def set_transceiver(self, transceiver):
        self.tr = transceiver

    def send_mqtt_update(self, channel, val, mqtt, topic):
        mqtt.pub(topic + '/Dimmers/' + str(channel), val)

    def update(self, addr, mqtt, topic, force):
        req = bytes([0x0, 0x0, 0x0])
        rsp = self.tr.req_resp(addr, req)
        if rsp is None:
            print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x0))
        else:
            val = rsp[2]
            if val == 0x4:
                channel = rsp[1]
                print("got new value ping for channel %i" % channel)
                req = bytes([0x4, channel, 0x0])
                rsp = self.tr.req_resp(addr, req)
                if rsp is None:
                    print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, 0x4))
                else:
                    val = rsp[2]
                    self.send_mqtt_update(channel, val, mqtt, topic)
            
