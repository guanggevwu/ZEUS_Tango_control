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
    axis = device_property(dtype=str, default_value='1,2,3')

    def init_device(self):
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        super().init_device()
        self.set_state(DevState.INIT)
        try:
            self.dev = serial.Serial(
                port=self.com, baudrate=19200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self._read_time = "N/A"
            self._user_defined_name = 'esp301'
            self._host_computer = platform.node()
            self._ax1_step, self._ax2_step, self._ax3_step, self._ax12_step = 0, 0, 0, 0
            self._raw_command_return = ''
            # print(
            #     f'ESP301 is connected. Model: {self._model}. Serial number: {self._serial_number}')
            self.set_status("ESP301 device is connected.")
        except:
            print("Could NOT connect to  ESP301")
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
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_position = attribute(
            name="ax2_position",
            label="axis 2 position",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_position = attribute(
            name="ax3_position",
            label="axis 3 position",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

        ax12_distance = attribute(
            name="ax12_distance",
            label="ax12 distance",
            dtype=float,
            unit='mm',
            format='6.3f',
            access=AttrWriteType.READ,
        )
        ax1_step = attribute(
            name="ax1_step",
            label="axis 1 step",
            dtype=float,
            unit='mm',
            format='6.3',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_step = attribute(
            name="ax2_step",
            label="axis 2 step",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_step = attribute(
            name="ax3_step",
            label="axis 3 step",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax12_step = attribute(
            name="ax12_step",
            label="ax12 step",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        if '1' in self.axis:
            self.add_attribute(ax1_position)
            self.add_attribute(ax1_step)
        if '2' in self.axis:
            self.add_attribute(ax2_position)
            self.add_attribute(ax2_step)
        if '3' in self.axis:
            self.add_attribute(ax3_position)
            self.add_attribute(ax3_step)
        if '1' in self.axis and '2' in self.axis:
            self.add_attribute(ax12_distance)
            self.add_attribute(ax12_step)

    def read_ax1_position(self, attr):
        self.dev.write(b"1TP\r")
        self._ax1_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax1_position

    # wait for stop has not been tested yet.
    def write_ax1_position(self, attr):
        self._ax1_position = attr.get_write_value()
        self.dev.write(f"1PA{self._ax1_position:.3f}\r".encode())

    def read_ax2_position(self, attr):
        self.dev.write(b"2TP\r")
        self._ax2_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax2_position

    def write_ax2_position(self, attr):
        self._ax2_position = attr.get_write_value()
        self.dev.write(f"2PA{self._ax2_position:.3f}\r".encode())

    def read_ax3_position(self, attr):
        self.dev.write(b"3TP\r")
        self._ax3_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax3_position

    def write_ax3_position(self, attr):
        self._ax3_position = attr.get_write_value()
        self.dev.write(f"3PA{self._ax3_position:.3f}\r".encode())

    def read_ax12_distance(self, attr):
        return float(f'{(self._ax1_position-self._ax2_position):.3f}')

    def read_ax1_step(self, attr):
        return self._ax1_step

    def write_ax1_step(self, attr):
        self._ax1_step = attr.get_write_value()

    def read_ax2_step(self, attr):
        return self._ax2_step

    def write_ax2_step(self, attr):
        self._ax2_step = attr.get_write_value()

    def read_ax3_step(self, attr):
        return self._ax3_step

    def write_ax3_step(self, attr):
        self._ax3_step = attr.get_write_value()

    def read_ax12_step(self, attr):
        return self._ax12_step

    def write_ax12_step(self, attr):
        self._ax12_step = attr.get_write_value()

    error_message = attribute(
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
        doc="refer to error appendix: https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    )

    def read_error_message(self):
        self.dev.write(b"TB?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        return reply.split(', ')[-1]

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

    @command(dtype_in=bool)
    def move_relative_axis1(self, plus=True):
        if plus:
            self.dev.write(f"1PR{self._ax1_step:.3f}\r".encode())
        else:
            self.dev.write(f"1PR{-self._ax1_step:.3f}\r".encode())
        print(f'{self._ax1_step}, {plus}')
        # self.dev.write(f"1PR{rel:.3f}\r".encode())

    @command(dtype_in=bool)
    def move_relative_axis2(self, plus=True):
        if plus:
            self.dev.write(f"2PR{self._ax2_step:.3f}\r".encode())
        else:
            self.dev.write(f"2PR{-self._ax2_step:.3f}\r".encode())

    @command(dtype_in=bool)
    def move_relative_axis3(self, plus=True):
        if plus:
            self.dev.write(f"3PR{self._ax3_step:.3f}\r".encode())
        else:
            self.dev.write(f"3PR{-self._ax3_step:.3f}\r".encode())

    @command(dtype_in=bool)
    def move_relative_axis12(self, plus=True):
        if plus:
            self.dev.write(f"1PR{self._ax12_step:.3f}\r".encode())
            self.dev.write(f"2PR{self._ax12_step:.3f}\r".encode())
        else:
            self.dev.write(f"1PR{-self._ax12_step:.3f}\r".encode())
            self.dev.write(f"2PR{-self._ax12_step:.3f}\r".encode())


if __name__ == "__main__":
    ESP301.run_server()
