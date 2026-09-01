#!/usr/bin/python3
import struct
import os

class TwoFloat:
    def __init__(self, name, channel1, channel2):
        self.tr = None
        self.idx = 0
        self.name = name
        self.channel1 = channel1
        self.channel2 = channel2

    def set_transceiver(self, transceiver):
        self.tr = transceiver

    def send_mqtt_update(self, channel1, channel2, mqtt, topic):
        mqtt.pub(topic + '/' + self.name + '/' + self.channel1, channel1)
        mqtt.pub(topic + '/' + self.name + '/' + self.channel2, channel2)

    def update(self, addr, mqtt, topic, force, slow_request):
        self.update(self, addr, mqtt, topic, force, False)

    def update(self, addr, mqtt, topic, force, slow_request):
        ret = True
        if not force:
            return True
        req = bytes([0x08, self.idx, 0x0])
        rsp = self.tr.req_resp(addr, req, slow_request)
        #print(rsp)
        if rsp is None:
            print("No (valid) response received, addr 0x%x!" % (addr))
            ret = False
        #elif rsp[1] != self.idx:
        #    print("Wrong idx in response: expected: %d got: %d; addr 0x%x!" % (self.idx, rsp[1], addr))
        else:
            if rsp[0] != 0x08:
                print("response type 0x%x from 0x%x not expected!" % (rsp[0], addr))
                return False

            if os.environ.get('DEBUG'):
                print("TwoFloat got: %s" % rsp.hex(' '))            
            
            channel1 = struct.unpack_from('f',rsp,1)[0]
            channel2 = struct.unpack_from('f',rsp,5)[0]
            self.send_mqtt_update(channel1, channel2, mqtt, topic)
       
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

        return ret

