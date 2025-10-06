#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import time
import datetime
import logging
import serial
import time
import serial.tools.list_ports
import platform
from threading import Thread
import functools
import pyvisa

# rm = pyvisa.ResourceManager()
# print(rm.list_resources())
# my_instrument = rm.open_resource('ASRL4::INSTR')
# print(my_instrument.query('*IDN?'))

all_ports = serial.tools.list_ports.comports()
dev = serial.Serial(port=all_ports[0].device, baudrate=9600, bytesize=8,
                    timeout=2, stopbits=serial.STOPBITS_ONE)
dev.write(b'?VERSION\r\n')
print(dev.readline())
a = 1
