#!/usr/bin/python3
import struct
import os

class TwoFloat:
    def __init__(self, name, channel1, channel2):
        self.rs485 = None
        self.idx = 0
        self.name = name
        self.channel1 = channel1
        self.channel2 = channel2

    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev

    def send_mqtt_update(self, channel1, channel2):
        self.rs485.mqtt.pub(self.rs485.topic + '/' + self.name + '/' + self.channel1, channel1)
        self.rs485.mqtt.pub(self.rs485.topic + '/' + self.name + '/' + self.channel2, channel2)

    def update(self, force, ping_result, slow_request):
        ret = True
        if not force:
            return True
        req = bytes([0x08, self.idx, 0x0])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, slow_request)
        if rsp is None:
            print("No (valid) response received, addr 0x%x!" % (self.rs485.addr))
            ret = False
        else:
            if rsp[0] != 0x08:
                print("response type 0x%x from 0x%x not expected!" % (rsp[0], self.rs485.addr))
                return False

            if os.environ.get('DEBUG'):
                print("TwoFloat got: %s" % rsp.hex(' '))            
            
            channel1 = struct.unpack_from('f',rsp,1)[0]
            channel2 = struct.unpack_from('f',rsp,5)[0]
            self.send_mqtt_update(channel1, channel2)
       
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

        return ret

