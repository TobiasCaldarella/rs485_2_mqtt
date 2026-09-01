#!/usr/bin/python3
import struct

class BM280:
    def __init__(self):
        self.tr = None
        self.idx = 0
        self.succ_cnt = 0
        self.err_cnt = 0

    def set_transceiver(self, transceiver):
        self.tr = transceiver

    def send_mqtt_update(self, temp, press, mqtt, topic):
        mqtt.pub(topic + '/BM280/temp', temp)
        mqtt.pub(topic + '/BM280/press', press)

    def update(self, addr, mqtt, topic, force):
        if not force:
            return
        req = bytes([0x08, self.idx, 0x0])
        rsp = self.tr.req_resp(addr, req, False)
        #print(rsp)
        if rsp is None:
            self.err_cnt = self.err_cnt + 1
            #mqtt.pub(topic + '/error_counter', self.err_cnt)
            
            #print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, self.reg))
        #elif rsp[1] != self.idx:
        #    print("Wrong idx in response: expected: %d got: %d; addr 0x%x!" % (self.idx, rsp[1], addr))
        else:
            if rsp[0] != 0x08:
                print("response type 0x%x from 0x%x not expected!" % (rsp[0], addr))
                return

            self.succ_cnt = self.succ_cnt + 1
            
            temp = struct.unpack_from('f',rsp,1)[0]
            press = struct.unpack_from('f',rsp,5)[0]
            #mqtt.pub(topic + '/success_counter', self.succ_cnt)
            #print("val: %x" % val)
            self.send_mqtt_update(temp, press, mqtt, topic)
       
        #if self.idx % 32 == 0:
        #    mqtt.pub(topic + '/error_rate', (self.err_cnt*100)/(self.err_cnt + self.succ_cnt))
        #    self.err_cnt = 0
        #    self.succ_cnt = 0
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

