#!/usr/bin/python3

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTT_ERR_SUCCESS
from time import sleep
import os

class Mqtt:
    def __init__(self, host, port, user, pw, base_topic):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.username_pw_set(user, pw)
        self.host = host
        self.port = port
        self.client = client
        self.base_topic = base_topic

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected")

    def on_disconnect(self, cloent, userdata, rc):
        print("MQTT disconnected")
        sleep(10)
        print("try reconnect...")
        self.connect()

    def connect(self):
        if self.client.connect(self.host, self.port) is not MQTT_ERR_SUCCESS:
            print("MQTT connection failed!")
        self.client.loop_start()

    def disconnect(self):
        self.client.disconnect()

    def pub(self, topic_suffix, data):
        topic = self.base_topic + '/' + topic_suffix
        if os.environ.get('DEBUG'):
            print("MQTT: publish '%s' to '%s'" % (data, topic))
        self.client.publish(topic, payload=data)
        
    def register_topic(self, topic_suffix, callback):
        topic = self.base_topic + '/' + topic_suffix
        self.client.message_callback_add(topic, callback)
        self.client.subscribe(topic)
        print("MQTT: registerd to '%s'" % topic)
       
    def loop(self):
        pass
#        self.client.loop(0.05)
