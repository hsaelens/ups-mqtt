#!/usr/bin/python3
# ups-mqtt.py

import os
import subprocess
import paho.mqtt.publish as mqtt
import time
from time import sleep, localtime, strftime
import datetime
from configparser import ConfigParser
import shutil

if not os.path.exists('conf/config.ini'):
    shutil.copy('config.ini', 'conf/config.ini')

# Load configuration file
config_dir = os.path.join(os.getcwd(), 'conf/config.ini')
config = ConfigParser(delimiters=('=', ), inline_comment_prefixes=('#'))
config.optionxform = str
config.read(config_dir)

cached_values = {}
base_topic = config['MQTT'].get('base_topic', 'home/ups')
if not base_topic.endswith('/'):
    base_topic += '/'

ups_host = config['UPS'].get('hostname', 'localhost')
ups_instance = config['UPS'].get('instance', 'ups')
mqtt_host = config['MQTT'].get('hostname', 'localhost')
mqtt_port = config['MQTT'].getint('port', 1883)
mqtt_user = config['MQTT'].get('username', None)
mqtt_password = config['MQTT'].get('password', None)
interval = config['General'].getint('interval', 60)
topic_str = config['MQTT'].get('topics', '*')
if topic_str == '*':
    topic_str = None
    #  topic_str = 'battery.voltage;battery.charge;ups.model;ups.mfr;input.voltage;output.voltage;ups.status;ups.load'
if not topic_str:
    topics = None
else:
    topics = tuple(topic_str.split(';'))


def process():
    ups = subprocess.run(["upsc", ups_instance + "@" + ups_host], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    lines = ups.stdout.decode('utf-8').split('\n')

    msgs = []

    for line in lines:
        fields = line.split(':')
        if len(fields) < 2:
            continue

        key = fields[0].strip()
        if topics and not key.startswith(topics):
            continue
        value = fields[1].strip()
        #  print(f"{key}-{value}")
        if cached_values.get(key, None) != value:
            cached_values[key] = value
            topic = base_topic + key.replace('.', '/').replace(' ', '_')
            msgs.append((topic, value, 0, True))
            #  print(f"Add {topic} {value}")
    if len(msgs) > 0:
        #  print(f'Send {len(msgs)}')
        timestamp = time.time()
        msgs.append((base_topic + 'timestamp', timestamp, 0, True))
        msgs.append((base_topic + 'lastUpdate', datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S %Z'), 0, True))
        mqtt.multiple(msgs, hostname=mqtt_host, port=mqtt_port, auth={'username': mqtt_user, 'password': mqtt_password})


while True:
    process()
    sleep(interval)
    