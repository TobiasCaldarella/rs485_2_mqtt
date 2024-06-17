#!/usr/bin/python3

class RS485_Device:
    def __init__(self, transceiver, addr, name):
        self.tr = transceiver
        self.addr = addr
        self.modules = []
        self.topic_suffix = name

    def add_module(self, module):
        module.set_transceiver(self.tr)
        self.modules.append(module)

    def update(self, mqtt, force):
        for m in self.modules:
            m.update(self.addr, mqtt, self.topic_suffix, force)
