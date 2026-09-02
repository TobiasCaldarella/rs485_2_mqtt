#!/usr/bin/python3
import serial
import serial.rs485
from threading import Lock
import time
import os
from crccheck.crc import Crc16Modbus

class Transceiver_CRC16:
    def __init__(self, port, baudrate, myID):
        #ser = serial.Serial(port, baudrate, timeout=0.01)
        ser = serial.Serial(port, baudrate, timeout=0.05)
        rs485_settings = serial.rs485.RS485Settings(rts_level_for_tx=True, rts_level_for_rx=False, loopback=False, delay_before_tx=0.05, delay_before_rx=0.005)
#        ser.rs485_mode = rs485_settings
        self.serial = ser
        self.myID = myID
        self.mtx = Lock()

    def _recv(self, otherID, sent_ms, slow_query):
        rsp = ResponseTelegram(self.myID, otherID)
        complete = False
        while complete == False:
            r = []
            if slow_query:
                rpt_cnt = 5
            else:
                rpt_cnt = 1

            while len(r) == 0 and rpt_cnt > 0:
                r = self.serial.read(1)
                rpt_cnt = rpt_cnt - 1

            if len(r) == 0:
                if os.environ.get('DEBUG'):
                    print('first/single-byte timeout')
                return None
            if ((round(time.time() * 1000) - sent_ms) > 200): # overall timeout: 200ms for complete telegram
                print("Telegram completion timeout! (addr=%x)" % otherID)
                #time.sleep(0.5)
                return None
            else:
                if os.environ.get('DEBUG'):
                    print("0x%x " % r[0], end='')
                complete = rsp.add_byte(r[0])
            
        if os.environ.get('DEBUG'):
            print("time: %d ms" % (round(time.time()*1000 - sent_ms)))
        return rsp 

    def _send_recv(self, otherID, data_to_send, retry_cnt, slow_request):
        self.serial.write(data_to_send)
        sent_ms = round(time.time() * 1000)
        
        rsp = None
        while rsp is None or not rsp.is_for_me() or not rsp.is_from_expected_sender():
            rsp = self._recv(otherID, sent_ms, slow_request)
            if rsp is None:
                return (None, False) #timeout, no response, do not retry
            if not rsp.is_crc_ok():
                if os.environ.get('DEBUG'):
                    print("CRC Error in received frame!")
                return (None, True)
    
            if not rsp.is_for_me() or not rsp.is_from_expected_sender():
                #try to receive next packet (w/o sending new request!), maybe this was an old/delayed response?
                if os.environ.get('DEBUG'):
                    print("packet nor for me or not from expected sender")
                rsp = None

            elif rsp.is_nak():
                if os.environ.get('DEBUG'):
                    print("NAK (addr=%x, try=%d)" % (otherID, retry_cnt))
                    return (None, True)
        
        if os.environ.get('DEBUG'):
            print("OK (addr=%x, try=%d)" % (otherID, retry_cnt))
#        time.sleep(0.1)
        return (rsp.get_data(), False)
    
    # sends a request and returns the response
    def req_resp(self, receiver: int, request: bytes, slow_request):
        # package
        #  0x01
        #  receiver
        #  sender
        #  msg_length
        #  request...
        #  crc (2byte)
        if receiver > 0xff or receiver < 0:
            raise ValueError("receiver must be < 255, not 0x%x" % receiver)

        pack = bytearray([0x01, receiver, self.myID, len(request)]) + request
        crc = Crc16Modbus.calc(pack)
        pack = pack + crc.to_bytes(2,'big')
        if os.environ.get('DEBUG'):
            print("Sending: " + pack.hex(' '))
        
        with self.mtx:
            retry_cnt = 1
            while retry_cnt <= 3:
                rsp_data, retry = self._send_recv(receiver, pack, retry_cnt, slow_request)
                if rsp_data is not None:
                    return rsp_data
                if retry is False:
                    if os.environ.get('DEBUG'):
                        print('no retry!')
                    return None
                retry_cnt = retry_cnt + 1
                if os.environ.get('DEBUG'):
                    print('retry')
            return None

class ResponseTelegram:
    def __init__(self, myID, otherID):
        self.state = 0
        self.sender = 0 # actual sender of telegram
        self.msgLen = 0
        self.chksum = 0
        self.myID = myID 
        self.otherID = otherID # expected sender of telegram
        self.rsp = None
        self.forMe = False
        self.crc_rx = 0

    def add_byte(self, r):
        if self.state == 0:
            if r == 0x01 or r ==0x00: # workaround for "strange" rs485 transceiver that start's with a zero...
                self.state = 1
                self.rsp = bytearray()
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
            if len(self.rsp) == self.msgLen:
                self.state = 5
            else:
                self.rsp.append(r)
        if self.state == 5:
            self.crc_rx = r << 8
            self.state = 6
        elif self.state == 6:
            self.crc_rx |= r
            
            #if not self.forMe:
            #    self.state = 0 #not for me, back to start
            #if self.sender != self.otherID:
            #    self.state = 0 #not from expected sender, back to start
            #else:
            self.state = 7 #don't touch this any more
            return True

        return False # not complete yet

    def get_data(self):
        return self.rsp

    def is_nak(self):
        if len(self.rsp) and self.rsp[0] == 0xff:
            return True
        else:
            return False
    
    def is_crc_ok(self):
        if self.crc_rx == Crc16Modbus.calc(bytes([0x01, self.myID, self.sender, self.msgLen]) + self.rsp):
            return True
        else:
            return False
    
    def is_for_me(self):
        return self.forMe

    def is_from_expected_sender(self):
        return self.sender == self.otherID

    def is_empty():
        return self.rsp is None or (len(self.rsp) == 0)
