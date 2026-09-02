#!/usr/bin/python3

import random

class RS485_Device:
    def __init__(self, transceiver, addr, name, mqtt):
        self.tr = transceiver
        self.addr = addr
        self.modules = []
        self.topic = name
        self.error_counter = 0
        self.success_counter = 0
        self.update_offset = random.randrange(100)
        self.update_counter = 0
        self.available = False
        self.mqtt = mqtt

    def add_module(self, module):
        module.set_transceiver(self)
        self.modules.append(module)

    def update(self, force):
        if self.update_counter == 0 or ((self.update_counter + self.update_offset) % 100) == 0:
            force = True

        if self.available is True or force is True:
            for m in self.modules:
                res = m.update(force)
                if res is True: # todo: detailed reporting for multi-telegram updates via double value (succ/errors)?
                    self.success_counter = self.success_counter + 1
                else:
                    self.error_counter = self.error_counter + 1
            
            if self.available == False:
                if self.success_counter > 0:
                    self.mqtt.pub(self.topic + '/availability', 'ONLINE', True)
                    self.available = True
                else:
                    self.mqtt.pub(self.topic + '/availability', 'OFFLINE', True)
                    self.mqtt.pub(self.topic + '/error_rate', 100)
        
            if self.update_counter % 32 == 0:
                if self.error_counter == 32:
                    self.available = False
                    self.mqtt.pub(self.topic + '/availability', 'OFFLINE', True)
                    self.mqtt.pub(self.topic + '/error_rate', 100)
                else:
                    self.mqtt.pub(self.topic + '/error_rate', (self.error_counter*100)/(self.error_counter + self.success_counter))
                
                self.success_counter = self.error_counter = 0
        
        self.update_counter = self.update_counter + 1
