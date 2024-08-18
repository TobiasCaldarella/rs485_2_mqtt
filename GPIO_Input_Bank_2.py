#!/usr/bin/python3

class GPIO_Input_Bank_2:
    def __init__(self):
        self.tr = None
        self.last_val = None
        self.idx = 0

    def set_transceiver(self, transceiver):
        self.tr = transceiver

    def send_mqtt_update(self, pin, bank_vals, mqtt, topic):
        val = (bank_vals & (1 << pin)) != 0
        mqtt.pub(topic + '/GPIO/' + str(pin), val)

    def update(self, addr, mqtt, topic, force):
        req = bytes([0x1, 0x0, 0x0])
        rsp = self.tr.req_resp(addr, req)
        if rsp is None:
            pass
            #print("No (valid) response received, addr 0x%x, reg 0x%x!" % (addr, self.reg))
        #elif rsp[1] != self.idx:
        #    print("Wrong idx in response: expected: %d got: %d; addr 0x%x!" % (self.idx, rsp[1], addr))
        else:
            val = rsp[2]
            if val != self.last_val or force is True:
                if self.last_val is None:
                    #print("last val: '<not-set> new val: %x; addr 0x%x, reg 0x%x" % (val, addr, self.reg))
                    for i in range(0,8):
                        self.send_mqtt_update(i, val, mqtt, topic)
                else:
                    #print("last val: %x new val: %x; addr 0x%x, reg 0x%x" % (self.last_val, val, addr, self.reg))
                    for i in range(0,8):
                        new = val & (1<<i)
                        old = self.last_val & (1<<i)
                        if new != old or force is True:
                            self.send_mqtt_update(i, val, mqtt, topic)
                self.last_val = val

        self.idx += 1
        if self.idx > 255:
            self.idx = 0
