#!/usr/bin/python3

from TwoFloat import TwoFloat

class HTU21:
    def __init__(self):
        self.TwoFloat = TwoFloat('HTU21', 'temp', 'humid')

    def set_transceiver(self, rs485_dev):
        self.TwoFloat.set_transceiver(rs485_dev)

    def update(self, force, ping_result):
        return self.TwoFloat.update(force, ping_result, True)


