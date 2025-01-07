#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import time
import datetime
import logging
import os
import csv

import serial
import time
import serial.tools.list_ports
import numpy as np
import platform
# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class ESP301(Device):

    def init_device(self):
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        Device.init_device(self)
        self.set_state(DevState.INIT)
        # com_obj = self.find_com_number()
        # if com_obj is not None:
        #     com_number = com_obj.device
        try:
            self.device = serial.Serial(
                port="com1", baudrate=19200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self._read_time = "N/A"

            # print(
            #     f'ESP301 is connected. Model: {self._model}. Serial number: {self._serial_number}')
            self.set_status("Gentec device is connected.")
        except:
            print("Could NOT connect to  Genotec-eo")
            self.set_state(DevState.OFF)

    user_defined_name = attribute(
        label="name",
        dtype=str,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_user_defined_name(self):
        return self._user_defined_name

    def write_user_defined_name(self, value):
        self._user_defined_name = value
        self.logger = LoggerAdapter(value, self.get_logger)

    def find_com_number(self):
        all_ports = serial.tools.list_ports.comports()
        filtered_ports = [
            p for p in all_ports if p.manufacturer == 'Gentec-EO']
        if len(filtered_ports) == 1:
            return filtered_ports[0]
        elif self.friendly_name == "QE12":
            filtered_ports = [
                p for p in filtered_ports if p.serial_number == '23869B4602001200']
        elif self.friendly_name == "QE195":
            filtered_ports = [
                p for p in filtered_ports if p.serial_number == '27869B461E002000']
        return filtered_ports[0]

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    read_time = attribute(
        label="read time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_read_time(self):
        return self._read_time

    ax1_position = attribute(
        label="axis 1 position",
        dtype=float,
        unit='mm',
        format='8.4f',
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_ax1_position(self):
        self.dev.write(b"1TP\r")
        self._ax1_position = float(self.dev.readline())
        return self._ax1_position

    def write_ax1_position(self, value):
        self.dev.write(f"1PA{value:.4f}".encode())

    error_message = attribute(
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_error_message(self):
        self.dev.write(b"TE?\r")
        return float(self.dev.readline())

    @command(dtype_in=int)
    def home(self, axis=1):
        self.dev.write(f"{axis}OR\r".encode())

    @command(dtype_in=int)
    def stop(self, axis=1):
        self.dev.write(f"{axis}AB\r".encode())


if __name__ == "__main__":
    ESP301.run_server()
