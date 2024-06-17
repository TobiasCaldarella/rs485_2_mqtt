#!/usr/bin/python3
from RS485_Device import RS485_Device
from Transceiver import Transceiver
from GPIO_Input_Bank import GPIO_Input_Bank
from Mqtt import Mqtt
from time import sleep
import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)

tr = Transceiver('/dev/ttyAMA0',19200, 0x77)
mqtt = Mqtt('localhost', 1883, 'zigbee', 'zigbee', 'rs485')
mqtt.connect()
devs = []

devs.append(RS485_Device(tr, 0x10, 'EG'))
devs[-1].add_module(GPIO_Input_Bank(1))
devs.append(RS485_Device(tr, 0x11, 'OG'))
devs[-1].add_module(GPIO_Input_Bank(1))

i = 0
while(True):
    for dev in devs:
        dev.update(mqtt, force=(i==0))
        sleep(0.1)

    if i%10 == 0:
        GPIO.output(27, True)
    else:
        GPIO.output(27, False)

    #print('.', end='', flush=True)
    i+=1
    if i >= 100:
        i=0
        #print('')

GPIO.cleanup()
