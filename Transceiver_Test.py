#!/usr/bin/python3

import Transceiver

# rest response class
def response_ok():
    print("response_ok...")
    rsp = Transceiver.ResponseTelegram(0x11)
    data = bytes.fromhex('01112202020264660304')

    complete = False
    for d in data:
        assert(complete == False)
        complete = rsp.add_byte(d)
    assert(complete == True)
    assert(rsp.get_data() is not None)
    assert(rsp.get_data() == bytes([0x02, 0x64]))
    print("OK")

def response_nok_chksum():
    print("response_nok_chksum...")
    rsp = Transceiver.ResponseTelegram(0x11)
    data = bytes.fromhex('01112202020264670304')

    complete = False
    for d in data:
        assert(complete == False)
        complete = rsp.add_byte(d)
    assert(complete == False)
    assert(rsp.get_data() is None)
    print("OK")

def response_ok_after_err():
    print("response_ok_after_err...")
    rsp = Transceiver.ResponseTelegram(0x11)

    data = bytes.fromhex('01112202020264670304')

    complete = False
    for d in data:
        assert(complete == False)
        complete = rsp.add_byte(d)
    assert(complete == False)
    assert(rsp.get_data() is None)

    data = bytes.fromhex('01112202020264660304')

    complete = False
    for d in data:
        assert(complete == False)
        complete = rsp.add_byte(d)
    assert(complete == True)
    assert(rsp.get_data() is not None)
    assert(rsp.get_data() == bytes([0x02, 0x64]))
    print("OK")
    
def response_nok_missing_but01():
    print("response_nok_missing_but01...")
    rsp = Transceiver.ResponseTelegram(0x11)
    data = bytes.fromhex('0111220202026401020102')

    complete = False
    for d in data:
        assert(complete == False)
        complete = rsp.add_byte(d)
    assert(complete == False)
    assert(rsp.get_data() is None)
    print("OK")



response_ok()
response_nok_chksum()
response_ok_after_err()
response_nok_missing_but01()
