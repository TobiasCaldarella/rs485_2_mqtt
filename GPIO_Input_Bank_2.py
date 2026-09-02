#!/usr/bin/python3

class GPIO_Input_Bank_2:
    def __init__(self):
        self.rs485 = None
        self.last_val = None
        self.idx = 0

    def set_transceiver(self, rs485_dev):
        self.rs485 = rs485_dev

    def send_mqtt_update(self, pin, bank_vals):
        val = (bank_vals & (1 << pin)) != 0
        self.rs485.mqtt.pub(self.rs485.topic + '/GPIO/' + str(pin), val)

    def update(self, force, ping_result):
        ping_result = ping_result[0]
        if ping_result & 0x01 or force:
            req = bytes([0x1, self.idx, 0x0])
            rsp = self.rs485.tr.req_resp(self.rs485.addr, req, False)
            #print(rsp)
            if rsp is None or len(rsp) < 2:
                return False
            else:
                val = rsp[2]
                if val != self.last_val or force is True:
                    if self.last_val is None or force is True:
                        for i in range(0,8):
                            self.send_mqtt_update(i, val)
                    else:
                        for i in range(0,8):
                            new = val & (1<<i)
                            old = self.last_val & (1<<i)
                            if new != old or force is True:
                                self.send_mqtt_update(i, val)
                    self.last_val = val
        
            self.idx += 1
            if self.idx > 255:
                self.idx = 0
        return True
        
