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

    com = device_property(dtype=str, default_value='COM1')
    axis = device_property(dtype=str, default_value='1,2')

    def init_device(self):
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        Device.init_device(self)
        self.set_state(DevState.INIT)
        try:
            self.dev = serial.Serial(
                port=self.com, baudrate=19200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self._read_time = "N/A"
            self._user_defined_name = 'esp301'
            self._host_computer = platform.node()
            self.error_table = {'0': 'NO ERRORS.', '1': "PCI COMMUNICATION TIME-OUT.", '4': "EMERGENCY SOP ACTIVATED.",
                                '6': 'COMMAND DOES NOT EXIST.', '7': 'PARAMETER OUT OF RANGE.', 'others': 'Please refer to label tooltip.'}
            self._raw_command_return = ''
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
        self._read_time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        return self._read_time

    def initialize_dynamic_attributes(self):
        ax1_position = attribute(
            name="ax1_position",
            label="axis 1 position",
            dtype=float,
            unit='mm',
            format='8.4f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_position = attribute(
            name="ax2_position",
            label="axis 2 position",
            dtype=float,
            unit='mm',
            format='8.4f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_position = attribute(
            name="ax3_position",
            label="axis 3 position",
            dtype=float,
            unit='mm',
            format='8.4f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        if '1' in self.axis:
            self.add_attribute(ax1_position)
        if '2' in self.axis:
            self.add_attribute(ax2_position)
        if '3' in self.axis:
            self.add_attribute(ax3_position)

    def read_ax1_position(self, attr):
        self.dev.write(b"1TP\r")
        self._ax1_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax1_position

    def write_ax1_position(self, attr):
        self.dev.write(f"1PA{attr.get_write_value():.4f}\r".encode())

    def read_ax2_position(self, attr):
        self.dev.write(b"2TP\r")
        self._ax2_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax2_position

    def write_ax2_position(self, attr):
        self.dev.write(f"2PA{attr.get_write_value():.4f}\r".encode())

    def read_ax3_position(self, attr):
        self.dev.write(b"3TP\r")
        self._ax3_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax3_position

    def write_ax3_position(self, attr):
        self.dev.write(f"3PA{attr.get_write_value():.4f}\r".encode())

    error_message = attribute(
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
        doc="refer to error appendix: https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    )

    def read_error_message(self):
        self.dev.write(b"TE?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        if reply in self.error_table:
            reading = f'{reply} {self.error_table[reply]}'
        else:
            reading = f'{reply} {self.error_table["others"]}'
        return reading

    raw_command = attribute(
        label="raw command",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc="No carriage-return required. https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    )

    def read_raw_command(self):
        return self._raw_command_return

    def write_raw_command(self, value):
        if value != '':
            self.dev.write(f"{value}\r".encode())
            self._raw_command_return = self.dev.readline().decode().replace('\r\n', '')

    @command(dtype_in=int)
    def home(self, axis=1):
        self.dev.write(f"{axis}OR\r".encode())

    @command(dtype_in=int)
    def emergency_stop(self, axis=1):
        axis = self.axis.split(',')
        for a in axis:
            self.dev.write(f"{a}AB\r".encode())

    @command()
    def stop(self):
        axis = self.axis.split(',')
        for a in axis:
            self.dev.write(f"{a}ST\r".encode())

    @command(dtype_in=str)
    def move_relative_axis1(self, rel, plus=True):
        print(rel)
        # self.dev.write(f"1PR{rel:.4f}\r".encode())

    @command(dtype_in=float)
    def move_relative_axis2(self, rel, plus=True):
        self.dev.write(f"2PR{rel:.4f}\r".encode())

    @command(dtype_in=float)
    def move_relative_axis3(self, rel, plus=True):
        self.dev.write(f"3PR{rel:.4f}\r".encode())


if __name__ == "__main__":
    ESP301.run_server()
