#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import datetime
import logging
import time
import platform
import ctypes
import os
import sys
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
        self.dev = ctypes.windll.LoadLibrary(os.path.join(
            os.path.dirname(__file__), "ps90.dll"))
        p90_connected = self.dev.PS90_SimpleConnect(1, b"")  # ANSI/Unicode !!
        if p90_connected != 0:
            print("Could NOT connect to PS90!")
            self.set_state(DevState.OFF)
            raise
        # load axis parameter file according to the part number
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

        self._user_defined_name = 'ps90_23070207'
        self._host_computer = platform.node()
        for axis in self.axis.split(','):
            setattr(self, f'_ax{axis}_position', -99999.0)
            setattr(self, f'_ax{axis}_step', 0.0)
        self._user_defined_locations = []
        self._saved_location_source = 'client'
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

    saved_location_source = attribute(
        label="saved location source",
        dtype="str",
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Require restart client GUI to take effect in the GUI. If set to "server", use the "...server_locations.txt" on the server computer. If set to "client", use "...client_locations.txt" on the client computer. Only works when the txt files are not empty. For example, if the attribute is set to "client" but the "...client_locations.txt" is empty, the server side saved locations will still be used.'
    )

    def read_saved_location_source(self):
        return self._saved_location_source

    def write_saved_location_source(self, value):
        if value == "server":
            self.load_server_side_list()
        self._saved_location_source = value

    user_defined_locations = attribute(
        label="user defined locations",
        dtype=(str,),
        max_dim_x=1000,
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
        doc='Use dev.current_location = "location_name" to move to the predefined location. Do NOT include the coordinates part.'
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
            setattr(self, f'read_set_ax{axis}_as',
                    self.create_read_set_as_function(axis))
            setattr(self, f'write_set_ax{axis}_as',
                    self.create_write_set_as_function(axis))
            self.add_attribute(self.create_position_attribute(axis))
            self.add_attribute(self.create_ax_step_attribute(axis))
            self.add_attribute(self.create_set_as_attribute(axis))

            # self.add_command(self.create_command_member(axis))
            # self.add_command(self.create_init_axis_function(axis))

    def create_position_attribute(self, axis):
        self.logger.info(f'created axis{axis} position.')
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
            self.dev.PS90_GetPositionEx.restype = ctypes.c_double
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
            self.dev.PS90_MoveEx(1, axis, ctypes.c_double(value), 1)
        self.logger.info(f'created write function for axis {axis}')
        return write_position

    def create_ax_step_attribute(self, axis):
        self.logger.info(f'created axis{axis} step.')
        attr = attribute(
            name=f"ax{axis}_step",
            label=f"axis {axis} step",
            dtype=float,
            unit='mm',
            format='6.3f',
            memorized=True,
            hw_memorized=True,
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

    def create_set_as_attribute(self, axis):
        attr = attribute(
            name=f"set_ax{axis}_as",
            label=f"set axis {axis} as",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_read_set_as_function(self, axis):
        def read_set_as(self, attr):
            if hasattr(self, f'_ax{axis}_old'):
                setattr(self, f'_set_ax{axis}_as',
                        f"set {getattr(self, f'_ax{axis}_old'):.3f} to {getattr(self, f'_ax{axis}_position'):.3f}")
            else:
                setattr(self, f'_set_ax{axis}_as',
                        "------------N/A-----------")
            return getattr(self, f'_set_ax{axis}_as')
        return read_set_as

    def create_write_set_as_function(self, axis):
        def write_set_as(self, attr):
            if hasattr(attr, 'get_write_value'):
                attr = attr.get_write_value()
            self.logger.info(f"{attr}")
            setattr(self, f'_ax{axis}_old', getattr(
                self, f'_ax{axis}_position'))
            error = self.dev.PS90_SetPositionEx(
                1, axis, ctypes.c_double(float(attr)))
            setattr(self, f'_ax{axis}_position', float(attr))
        return write_set_as

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
        self.init_ax(axis)
        result = self.dev.PS90_FreeSwitch(1, axis)
        self.logger.info(f"free switch axis {axis}. Result: {result}")

    @command(dtype_in=int)
    def go_ref_ax(self, axis):
        result = self.dev.PS90_GoRef(1, axis, 4)
        self.logger.info(f"go ref axis {axis}. Result: {result}")

    @command()
    def move_relative_axis(self, input: list[int]):
        self.dev.PS90_SetTargetMode(1, int(input[0]), 0)
        if input[1]:
            self.dev.PS90_MoveEx(1, int(input[0]), ctypes.c_double(
                getattr(self, f'_ax{input[0]}_step')), 1)
        else:
            self.dev.PS90_MoveEx(
                1, int(input[0]), ctypes.c_double(-getattr(self, f'_ax{input[0]}_step')), 1)
        self.logger.info(f'relative moving, [direction, axis], {input}')

    @command
    def load_server_side_list(self):
        '''
        Load the server side saved list of user defined locations.
        '''
        try:
            server_list_path = os.path.join(os.path.dirname(
                __file__), f'{sys.argv[1]}_server_locations.txt')
            if not os.path.isfile(server_list_path):
                with open(server_list_path, 'w', newline='') as f:
                    f.write(
                        "name positions\n")
            with open(server_list_path, 'r',) as f:
                tmp = []
                next(f)
                for line in f:
                    if line.strip():
                        name, positions = [e for e in line.replace(
                            '\t', ' ').strip().replace('"', '').split(' ') if e]
                        tmp.append(f"{name}: ({positions})")
                if tmp:
                    self._user_defined_locations = tmp
                    self.logger.info(
                        f'Loaded server side saved user defined locations: {tmp}')
                else:
                    self.logger.info(
                        "No server side saved user defined locations found.")
        except Exception as e:
            self.logger.info(
                "Server side saved user defined locations file is not loaded successfully. Reason: {e}")


if __name__ == "__main__":
    OwisPS.run_server()
