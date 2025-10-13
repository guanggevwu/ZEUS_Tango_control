#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import time
import datetime
import logging
import serial
import time
import platform
from threading import Thread
import functools
from ctypes import windll, c_double
import sys
import os
import csv
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class OwisPS(Device):
    serial_number = device_property(dtype=int, default_value=1)
    part_number = device_property(dtype=str, default_value='')
    axis = device_property(dtype=str, default_value='1')

    def init_device(self):
        super().init_device()  # this loads the device properties
        self.get_logger = logging.getLogger(self.__class__.__name__)
        if not hasattr(self, 'friendly_name'):
            self.friendly_name = self.__class__.__name__
        self.logger = LoggerAdapter(self.friendly_name, self.get_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        self.dev = windll.LoadLibrary(os.path.join(
            os.path.dirname(__file__), "ps90.dll"))
        p90_connected = self.dev.PS90_SimpleConnect(1, b"")  # ANSI/Unicode !!
        if p90_connected != 0:
            print("Could NOT connect to PS90!")
            self.set_state(DevState.OFF)
            return
        if self.part_number:
            self.part_number_list = self.part_number.split(',')
            # iterate through all axes and find the part number from the part_number property.
            for idx, axis in enumerate(self.axis.split(',')):
                if idx < len(self.part_number_list):
                    pn = self.part_number_list[idx]
                if os.path.isfile(os.path.join(os.path.dirname(__file__), 'axis_parameter_file', f'{pn}.owd')):
                    result = self.dev.PS90_LoadTextFile(1, int(axis), os.path.join(
                        os.path.dirname(__file__), 'axis_parameter_file', f'{pn}.owd').encode('utf-8'))
                    if result == 0:
                        self.logger.info(
                            f"{pn}.owd is loaded for axis {axis}.")
                        continue
                self.logger.info(
                    f"Could NOT load axis parameter file: {pn}.owd for axis {axis}! Error code: {result}")

        # self._read_time = "N/A"
        self._user_defined_name = 'ps90_23070207'
        self._host_computer = platform.node()
        for axis in self.axis.split(','):
            setattr(self, f'_ax{axis}_position', 0)
            setattr(self, f'_ax{axis}_step', 0.0)
        self._user_defined_locations = []
        self.set_status("PS90 device is connected.")
        self.set_state(DevState.ON)

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

    user_defined_locations = attribute(
        label="user defined locations",
        dtype=(str,),
        max_dim_x=100,
        access=AttrWriteType.READ_WRITE,
    )

    def read_user_defined_locations(self):
        return self._user_defined_locations

    def write_user_defined_locations(self, value):
        self.logger.info(f"Write user_defined_locations: {value}")
        self._user_defined_locations = value

    current_location = attribute(
        label="current location",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Use dev.current_location = "location_name" to move to the predefined location'
    )

    def is_position_close(self, a: list[float], b: list[float], tol=1e-3):
        return all(abs(x - y) < tol for x, y in zip(a, b))

    def read_current_location(self):
        self._current_location = 'Undefined'
        current_positions = [
            getattr(self, f'_ax{axis}_position') for axis in self.axis.split(',')]
        for loc in self._user_defined_locations:
            name, positions = loc.split(': ')
            p = [float(i) for i in positions.strip('()').split(',')]
            if self.is_position_close(current_positions, p):
                self._current_location = loc
                break
        return self._current_location

    def write_current_location(self, value):
        for loc in self._user_defined_locations:
            name, positions = loc.split(': ')
            if name == value:
                target_positions = [float(i)
                                    for i in positions.strip('()').split(',')]
        for axis, target in zip(self.axis.split(','), target_positions):
            getattr(self, f'write_ax{axis}_position')(self, target)

    def initialize_dynamic_attributes(self):
        # way to add command dynamically
        # cmd = command(f=self.test_stop)
        # self.add_command(cmd)
        for axis in [int(i) for i in self.axis.split(',')]:
            setattr(self, f'read_ax{axis}_position',
                    self.create_read_position_function(axis))
            setattr(self, f'write_ax{axis}_position',
                    self.create_write_position_function(axis))
            setattr(self, f'read_ax{axis}_step',
                    self.create_read_ax_step_function(axis))
            setattr(self, f'write_ax{axis}_step',
                    self.create_write_ax_step_function(axis))
            self.add_attribute(self.create_position_attribute(axis))
            self.add_attribute(self.create_ax_step_attribute(axis))

            # self.add_command(self.create_command_member(axis))
            # self.add_command(self.create_init_axis_function(axis))

    def create_position_attribute(self, axis):
        self.logger.info(f'created axis{axis}.')
        attr = attribute(
            name=f"ax{axis}_position",
            label=f"axis {axis} position",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_read_position_function(self, axis):
        def read_position(self, attr):
            self.dev.PS90_GetPositionEx.restype = c_double
            setattr(self, f'_ax{axis}_position',
                    self.dev.PS90_GetPositionEx(1, axis))
            return getattr(self, f'_ax{axis}_position')
        self.logger.info(f'created read function for axis {axis}')
        return read_position

    def create_write_position_function(self, axis):
        def write_position(self, attr):
            if hasattr(attr, 'get_write_value'):
                value = attr.get_write_value()
            else:
                value = attr
            self.dev.PS90_SetTargetMode(1, axis, 1)
            self.dev.PS90_MoveEx(1, axis, c_double(value), 1)
        self.logger.info(f'created write function for axis {axis}')
        return write_position

    def create_ax_step_attribute(self, axis):
        self.logger.info(f'created axis{axis}.')
        attr = attribute(
            name=f"ax{axis}_step",
            label=f"axis {axis} step",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_read_ax_step_function(self, axis):
        def read_ax_step(self, attr):
            return getattr(self, f'_ax{axis}_step')
        return read_ax_step

    def create_write_ax_step_function(self, axis):
        def write_ax_step(self, attr):
            setattr(self, f'_ax{axis}_step', attr.get_write_value())
        return write_ax_step

    @command
    def stop_all_axis(self):
        self.logger.info(f"stop all axis")
        for axis in range(1, 10):
            result = self.dev.PS90_Stop(1, axis)
            if result != 0:
                self.logger.error(
                    f"Error stopping axis {axis}: error code {result}")

    @command(dtype_in=int)
    def init_ax(self, axis):
        result = self.dev.PS90_MotorInit(1, axis)
        self.logger.info(f"init axis {axis}. Result: {result}")

    @command(dtype_in=int)
    def free_switch_ax(self, axis):
        result = self.dev.PS90_FreeSwitch(1, axis)
        self.logger.info(f"free switch axis {axis}. Result: {result}")

    @command(dtype_in=int)
    def go_ref_ax(self, axis):
        result = self.dev.PS90_GoRef(1, axis, 4)
        self.logger.info(f"go ref axis {axis}. Result: {result}")

    @command()
    def move_relative_axis1(self, input: list[int]):
        self.dev.PS90_SetTargetMode(1, int(input[0]), 0)
        if input[1]:
            self.dev.PS90_MoveEx(1, int(input[0]), c_double(self._ax1_step), 1)
        else:
            self.dev.PS90_MoveEx(
                1, int(input[0]), c_double(-self._ax1_step), 1)
        self.logger.info(f'relateive moving, {input}')

    # @command(dtype_in=bool)
    # def move_relative_axis2(self, plus=True):
    #     self.dev.PS90_SetTargetMode(1, 2, 0)
    #     if plus:
    #         self.dev.PS90_MoveEx(1, 2, c_double(self._ax1_step), 1)
    #     else:
    #         self.dev.PS90_MoveEx(1, 2, c_double(-self._ax1_step), 1)
    #     self.logger.info(f'{self._ax2_step}, {plus}')

    # @command(dtype_in=bool)
    # def move_relative_axis3(self, plus=True):
    #     self.dev.PS90_SetTargetMode(1, 3, 0)
    #     if plus:
    #         self.dev.PS90_MoveEx(1, 3, c_double(self._ax3_step), 1)
    #     else:
    #         self.dev.PS90_MoveEx(1, 3, c_double(-self._ax3_step), 1)
    #     self.logger.info(f'{self._ax3_step}, {plus}')


if __name__ == "__main__":
    OwisPS.run_server()
