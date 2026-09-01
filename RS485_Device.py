#!/usr/bin/python3

import random

class RS485_Device:
    def __init__(self, transceiver, addr, name):
        self.tr = transceiver
        self.addr = addr
        self.modules = []
        self.topic_suffix = name
        self.error_counter = 0
        self.success_counter = 0
        self.update_offset = random.randrange(100)
        self.update_counter = 0

    def add_module(self, module):
        module.set_transceiver(self.tr)
        self.modules.append(module)

    def update(self, mqtt, force):
        if self.update_counter == 0 or ((self.update_counter + self.update_offset) % 100) == 0:
            force = True

        for m in self.modules:
            res = m.update(self.addr, mqtt, self.topic_suffix, force)
            if res is True: # todo: detailed reporting for multi-telegram updates via double value (succ/errors)?
                self.success_counter = self.success_counter + 1
            else:
                self.error_counter = self.error_counter + 1
            
        self.update_counter = self.update_counter + 1
        
        if self.update_counter % 32 == 0:
            mqtt.pub(self.topic_suffix + '/error_rate', (self.error_counter*100)/(self.error_counter + self.success_counter))
            self.success_counter = self.error_counter = 0
        
