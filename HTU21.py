#!/usr/bin/python3

from TwoFloat import TwoFloat

class HTU21:
    def __init__(self):
        self.TwoFloat = TwoFloat('HTU21', 'temp', 'humid')

    def set_transceiver(self, transceiver):
        self.TwoFloat.set_transceiver(transceiver)

    def update(self, addr, mqt, topic, force):
        self.TwoFloat.update(addr, mqt, topic, force, True)


