#!/usr/bin/python3
import struct
from TwoFloat import TwoFloat

class BM280:
    def __init__(self):
        self.twoFloat = TwoFloat('BM280', 'temp', 'press')

    def set_transceiver(self, rs485_dev):
        self.twoFloat.set_transceiver(rs485_dev)

    def update(self, force, ping_result):
        return self.twoFloat.update(force, ping_result, False)
        
