#!/usr/bin/python3
from RS485_Device import RS485_Device
from Transceiver_CRC16 import Transceiver_CRC16
from GPIO_Input_Bank import GPIO_Input_Bank
from GPIO_Input_Bank_2 import GPIO_Input_Bank_2
from BM280 import BM280
from HTU21 import HTU21
from Katzenfenster import Katzenfenster
from Mqtt import Mqtt
from time import sleep
from Dimmers import Dimmers
from LeinwandSequencer import LeinwandSequencer

rpi = False

if rpi:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(27, GPIO.OUT)
if rpi:
    #tr = Transceiver_CRC16('/dev/serial/by-id/usb-1a86_USB2.0-Serial-if00-port0',19200, 0x77)
    tr = Transceiver_CRC16('/dev/ttyAMA0', 19200, 0x77)
else:
    tr = Transceiver_CRC16('/dev/ttyUSB1', 19200, 0x77)
mqtt = Mqtt('casa.frugoli.de', 1883, 'zigbee', 'zigbee', 'rs485')
mqtt.connect()
devs = []

#devs.append(RS485_Device(tr, 0x10, 'EG'))
#devs[-1].add_module(GPIO_Input_Bank_2())
#devs.append(RS485_Device(tr, 0x11, 'OG'))
#devs[-1].add_module(GPIO_Input_Bank_2())
#devs.append(RS485_Device(tr, 0x12, 'DG'))
#devs[-1].add_module(GPIO_Input_Bank_2())
#devs[-1].add_module(BM280())

#devs.append(RS485_Device(tr, 0x21, 'Kino'))
#devs[-1].add_module(GPIO_Input_Bank_2())
#devs[-1].add_module(Dimmers(4, mqtt, 'Kino', 0x21))
#devs[-1].add_module(HTU21())

devs.append(RS485_Device(tr, 0x44, 'Leinwand'))
devs[-1].add_module(LeinwandSequencer())
#devs[-1].add_module(Dimmers(4, mqtt, 'Kino', 0x21))
#devs[-1].add_module(HTU21())

#devs.append(RS485_Device(tr, 0x31, 'Katzenfenster'))
#devs[-1].add_module(Katzenfenster(mqtt, 'Katzenfenster', 0x31))

i = 0
while(True):
    for dev in devs:
        dev.update(mqtt, force=(i==0))
        #sleep(0.1)
    if rpi:
        if i%10 == 0:
            GPIO.output(27, True)
        else:
            GPIO.output(27, False)

    #print('.', end='', flush=True)
    i+=1
    if i >= 100:
        i=0
        #print('')
    mqtt.loop()
    #break
GPIO.cleanup()
