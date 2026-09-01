#!/usr/bin/python3
import serial
import serial.rs485
from threading import Lock
import time
import os

class Transceiver:
    def __init__(self, port, baudrate, senderID):
        #ser = serial.Serial(port, baudrate, timeout=0.01)
        ser = serial.Serial(port, baudrate, timeout=0.1)
        rs485_settings = serial.rs485.RS485Settings(rts_level_for_tx=True, rts_level_for_rx=False, loopback=False, delay_before_tx=0.05, delay_before_rx=0.005)
#        ser.rs485_mode = rs485_settings
        self.serial = ser
        self.senderID = senderID
        self.mtx = Lock()

    # sends a request and returns the response
    def req_resp(self, receiver: int, request: bytes):
        # package
        #  0x01
        #  receiver
        #  sender
        #  msg_length
        #  0x02
        #  request...
        #  chksum
        #  0x03
        #  0x04
        if receiver > 0xff or receiver < 0:
            raise ValueError("receiver must be < 255, not 0x%x" % receiver)

        chksum = 0
        for b in request:
            chksum ^= b

        pack = bytes([0x01, receiver, self.senderID, len(request), 0x02]) + request + bytes([chksum, 0x03, 0x04])
        
        with self.mtx:
            self.serial.write(pack)
            #print("Wrote %i bytes to %i, receiving:" % (len(pack), receiver), end='')
            sent_ms = round(time.time() * 1000)
            
            rsp = ResponseTelegram(self.senderID)
            complete = False
            while complete == False:
                r = self.serial.read(1)
                if ((round(time.time() * 1000) - sent_ms) > 200):
                    print("Timeout! (addr=%x)" % receiver)
                    time.sleep(0.1)
                    return None
                if len(r) == 0:
                    print("!", end='')
                else:
                    if os.environ.get('DEBUG'):
                        print("0x%x " % r[0], end='')
                    complete = rsp.add_byte(r[0])
            if os.environ.get('DEBUG'):
                print("OK")
            time.sleep(0.1)
            return rsp.get_data()

class ResponseTelegram:
    def __init__(self, myID):
        self.state = 0
        self.sender = 0
        self.msgLen = 0
        self.chksum = 0
        self.myID = myID
        self.rsp = None
        self.forMe = False

    def add_byte(self, r):
        if self.state == 0:
            if r == 0x01 or r ==0x00: # workaround for "strange" rs485 transceiver that start's with a zero...
                self.state = 1
                self.rsp = None
                self.forMe = False
        elif self.state == 1:
            if r == self.myID:
                self.forMe = True
            self.state = 2
        elif self.state == 2:
            self.sender = r
            self.state = 3
        elif self.state == 3:
            self.msgLen = r
            self.state = 4
        elif self.state == 4:
            if r == 0x02:
                self.state = 5
                self.chksum = 0
                self.rsp = bytearray()
            else:
                self.state = 99
        elif self.state == 5:
            if len(self.rsp) == self.msgLen:
                self.state = 6
            else:
                self.rsp.append(r)
                self.chksum ^= r
        if self.state == 6:
            if r == self.chksum:
                self.state = 7
            else:
                print("chksum bad")
                self.state = 99
        elif self.state == 7:
            if r == 0x03:
                self.state = 8
            else:
                self.state = 99
        elif self.state == 8:
            if r == 0x04:
                self.state = 0
                if self.forMe == True:
                    return True; # telegram complete
                else:
                    print("Transceiver: Package not for me, discarded")
                    self.rsp = bytearray()
            else:
                self.state = 99
        if self.state == 99:
            print("Transceiver: In error state, discarding byte 0x%x. State %d" % (r, self.state))
            time.sleep(0.1)
            self.state = 0 # try to restart
            self.rsp = None
            self.forMe = False
        return False # not complete yet

    def get_data(self):
        return self.rsp


