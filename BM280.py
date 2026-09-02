#!/usr/bin/python3
import struct

class BM280:
    def __init__(self):
        self.rs485 = None
        self.idx = 0

    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev

    def send_mqtt_update(self, temp, press, mqtt, topic):
        mqtt.pub(topic + '/BM280/temp', temp)
        mqtt.pub(topic + '/BM280/press', press)

    def update(self, force, ping_result):
        if not force:
            return True

        req = bytes([0x08, self.idx, 0x0])
        rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
        #print(rsp)
        if rsp is None:
            return False
            
        else:
            if rsp[0] != 0x08:
                print("response type 0x%x from 0x%x not expected!" % (rsp[0], self.rs485.addr))
                return False

            temp = struct.unpack_from('f',rsp,1)[0]
            press = struct.unpack_from('f',rsp,5)[0]
            self.send_mqtt_update(temp, press, self.rs485.mqtt, self.rs485.topic)
        
        self.idx += 1
        if self.idx > 255:
            self.idx = 0

        return True
        
