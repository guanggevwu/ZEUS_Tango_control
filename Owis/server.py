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

    # @staticmethod
    # def clear_error_wrap(func):
    #     '''
    #     A decorator to clear error message and restart auto polling reading error message.
    #     This decorator is applied to all write functions, except for "stop" and change relative move steps.
    #     '''
    #     @functools.wraps(func)
    #     def wrapper(*args, **kwargs):
    #         args[0]._error_message = None
    #         args[0].should_stop = False
    #         func(*args, **kwargs)
    #     return wrapper

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

        # use absolute position mode
        self.dev.PS90_SetTargetMode(1, 1, 1)
        # self._read_time = "N/A"
        self._user_defined_name = 'ps90_23070207'
        self._host_computer = platform.node()
        self._ax1_step, self._ax2_step = 0, 0
        for axis in self.axis.split(','):
            setattr(self, f'_ax{axis}_position', 0)
        self._user_defined_locations = []
        # self._ax1_step, self._ax2_step, self._ax3_step, self._ax12_step, self._ax1_status, self._ax2_status, self._ax3_status = 0, 0, 0, 0, False, False, False
        # self._raw_command_return = ''
        # self.unit_code = {0: "unknown",
        #                   1: "unknown", 2: "mm", 3: "um", 7: "deg"}
        # self.dev.write(b"1SN?\r")
        # self._axis1_unit = self.unit_code[
        #     int(self.dev.readline().decode().replace('\r\n', ''))]
        # self.dev.write(b"2SN?\r")
        # self._axis2_unit = self.unit_code[
        #     int(self.dev.readline().decode().replace('\r\n', ''))]
        # self.dev.write(b"3SN?\r")
        # self._axis3_unit = self.unit_code[
        #     int(self.dev.readline().decode().replace('\r\n', ''))]
        # self._error_message = None
        # # print(
        # #     f'ESP301 is connected. Model: {self._model}. Serial number: {self._serial_number}')
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
        access=AttrWriteType.READ,
    )

    def read_user_defined_locations(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'user_defined_locations.csv'), 'r',) as f:
                self._user_defined_locations_dict = {}
                reader = csv.DictReader(f,  delimiter=' ')
                for row in reader:
                    self._user_defined_locations_dict[row['name']] = [
                        float(i) for i in row['positions'].split(',') if i]

                self._user_defined_locations = [
                    f'{k}: ({",".join([str(i) for i in v])})' for k, v in self._user_defined_locations_dict.items()]
        except Exception as e:
            self.logger.info(f"Error reading user_defined_locations.csv: {e}")
        return self._user_defined_locations

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
        for k, v in self._user_defined_locations_dict.items():
            if self.is_position_close(current_positions, v):
                self._current_location = f'{k}: ({",".join([str(i) for i in v])})'
                break
        return self._current_location

    def write_current_location(self, value):
        target_positions = self._user_defined_locations_dict[value]
        for axis, target in zip(self.axis.split(','), target_positions):
            getattr(self, f'write_ax{axis}_position')(self, target)

    def initialize_dynamic_attributes(self):
        ax1_step = attribute(
            name="ax1_step",
            label="axis 1 step",
            dtype=float,
            unit='mm',
            format='6.3f',
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

        # ax1_status = attribute(
        #     name="ax1_status",
        #     label="axis 1 status",
        #     dtype=str,
        #     memorized=True,
        #     access=AttrWriteType.READ_WRITE,
        # )
        # ax2_status = attribute(
        #     name="ax2_status",
        #     label="axis 2 status",
        #     dtype=str,
        #     memorized=True,
        #     access=AttrWriteType.READ_WRITE,
        # )
        # ax3_status = attribute(
        #     name="ax3_status",
        #     label="axis 3 status",
        #     dtype=str,
        #     memorized=True,
        #     access=AttrWriteType.READ_WRITE,
        # )
        # customized_location = attribute(
        #     name="customized_location",
        #     label="customized location",
        #     dtype=str,
        #     memorized=True,
        #     access=AttrWriteType.READ_WRITE,
        # )

        # @command()
        # @ESP301.clear_error_wrap
        # def ax1_negative_limit(self):
        #     self.dev.write(f"1MT-\r".encode())

        # @command()
        # @ESP301.clear_error_wrap
        # def ax2_positive_limit(self):
        #     self.dev.write(f"2MT+\r".encode())

        # @command()
        # @ESP301.clear_error_wrap
        # def reset_to_TA1(self):
        #     Thread(target=self.threaded_reset_to_TA1).start()
        # @command()
        # def test_command(self):
        #     self.fa = '1'
        #     print("test command")

        for axis in [int(i) for i in self.axis.split(',')]:
            setattr(self, f'read_ax{axis}_position',
                    self.create_read_position_function(axis))
            setattr(self, f'write_ax{axis}_position',
                    self.create_write_position_function(axis))
            # setattr(self, f'ax{axis}_position',
            #         self.create_position_attribute(axis))
            self.add_attribute(self.create_position_attribute(axis))
            # self.add_command(self.create_init_axis_function(axis))
            # not sure why add_command does not work.
            # self.add_command(test_command)

        if '1' in self.axis:
            self.add_attribute(ax1_step)
        if '2' in self.axis:
            self.add_attribute(ax2_step)
        if '3' in self.axis:
            self.add_attribute(ax3_step)

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

    # def create_init_axis_function(self, axis):
    #     @command
    #     def init_axis(self):
    #         print("init axis")
    #         # self.dev.PS90_InitAxis(1, axis)
    #     # init_axis.__name__ = f'init_axis{axis}'
    #     return init_axis

    @command
    def stop_all_axis(self):
        self.logger.info(f"stop all axis")
        for axis in range(1, 10):
            result = self.dev.PS90_Stop(1, axis)
            if result != 0:
                self.logger.error(
                    f"Error stopping axis {axis}: error code {result}")

    @command
    def init_ax1(self):
        self.logger.info(f"init axis 1")
        self.dev.PS90_MotorInit(1, 1)

    @command
    def init_ax2(self):
        self.logger.info(f"init axis 2")
        self.dev.PS90_MotorInit(1, 2)

    @command
    def init_ax3(self):
        self.logger.info(f"init axis 3")
        self.dev.PS90_MotorInit(1, 3)

    @command
    def init_ax4(self):
        self.logger.info(f"init axis 4")
        self.dev.PS90_MotorInit(1, 4)

    @command
    def free_switch_ax1(self):
        self.logger.info(f"free switch axis 1")
        self.dev.PS90_FreeSwitch(1, 1)

    @command
    def free_switch_ax2(self):
        self.logger.info(f"free switch axis 2")
        self.dev.PS90_FreeSwitch(1, 2)

    @command
    def free_switch_ax3(self):
        self.logger.info(f"free switch axis 3")
        self.dev.PS90_FreeSwitch(1, 3)

    @command
    def free_switch_ax4(self):
        self.logger.info(f"free switch axis 4")
        self.dev.PS90_FreeSwitch(1, 4)

    @command
    def go_ref_ax1(self):
        self.logger.info(f"go ref axis 1")
        self.dev.PS90_GoRef(1, 1, 4)

    @command
    def go_ref_ax2(self):
        self.logger.info(f"go ref axis 2")
        self.dev.PS90_GoRef(1, 2, 4)

    @command
    def go_ref_ax3(self):
        self.logger.info(f"go ref axis 3")
        self.dev.PS90_GoRef(1, 3, 4)

    @command
    def go_ref_ax4(self):
        self.logger.info(f"go ref axis 4")
        self.dev.PS90_GoRef(1, 4, 4)

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
        self._ax3_step = float(attr.get_write_value())

    def read_ax1_status(self, attr):
        self.dev.write(b"1MO?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        if reply == '1':
            self._ax1_status = "On"
        elif reply == '0':
            self._ax1_status = "Off"
        return self._ax1_status

    # @clear_error_wrap
    # def write_ax1_status(self, attr):
    #     self._ax1_status = attr.get_write_value()
    #     if attr.get_write_value().lower() == "on":
    #         self.dev.write(b"1MO\r")
    #     elif attr.get_write_value().lower() == "off":
    #         self.dev.write(b"1MF\r")

    # def read_ax2_status(self, attr):
    #     self.dev.write(b"2MO?\r")
    #     reply = self.dev.readline().decode().replace('\r\n', '')
    #     if reply == '1':
    #         self._ax2_status = "On"
    #     elif reply == '0':
    #         self._ax2_status = "Off"
    #     return self._ax2_status

    # @clear_error_wrap
    # def write_ax2_status(self, attr):
    #     self._ax2_status = attr.get_write_value()
    #     if attr.get_write_value().lower() == "on":
    #         self.dev.write(b"2MO\r")
    #     elif attr.get_write_value().lower() == "off":
    #         self.dev.write(b"2MF\r")

    # def read_ax3_status(self, attr):
    #     self.dev.write(b"3MO?\r")
    #     reply = self.dev.readline().decode().replace('\r\n', '')
    #     if reply == '1':
    #         self._ax3_status = "On"
    #     elif reply == '0':
    #         self._ax3_status = "Off"
    #     return self._ax3_status

    # @clear_error_wrap
    # def write_ax3_status(self, attr):
    #     self._ax3_status = attr.get_write_value()
    #     if attr.get_write_value().lower() == "on":
    #         self.dev.write(b"3MO\r")
    #     elif attr.get_write_value().lower() == "off":
    #         self.dev.write(b"3MF\r")

    # def read_customized_location(self, attr):
    #     if hasattr(self, '_ax1_position'):
    #         if abs(self._ax1_position - self.TA1[0]) < 0.1 and abs(self._ax2_position - self.TA1[1]) < 0.1:
    #             self._customized_location = 'TA1'
    #         elif abs(self._ax1_position - self.TA2[0]) < 0.1 and abs(self._ax2_position - self.TA2[1]) < 0.1:
    #             self._customized_location = 'TA2'
    #         elif abs(self._ax1_position - self.TA3[0]) < 0.1 and abs(self._ax2_position - self.TA3[1]) < 0.1:
    #             self._customized_location = 'TA3'
    #         elif abs(self._ax1_position - self.TA_test[0]) < 0.1 and abs(self._ax2_position - self.TA_test[1]) < 0.1:
    #             self._customized_location = 'TA_test'
    #         else:
    #             self._customized_location = 'Undefined'
    #     else:
    #         self._customized_location = 'Not initialized'
    #     return self._customized_location

    # @clear_error_wrap
    # def write_customized_location(self, attr):
    #     Thread(target=self.threaded_write_customized_location,
    #            args=(attr,)).start()

    # def wait_until_arrive(self, axis, dest, interval=1):
    #     while abs(dest-getattr(self, f'_ax{axis}_position')) > 0.1:
    #         time.sleep(interval)
    #         print(f"waiting for axis {axis}")
    #         if self.should_stop:
    #             break

    # error_message = attribute(
    #     label="error message",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    #     doc="refer to error appendix: https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    # )

    # def read_error_message(self):
    #     if not self._error_message:
    #         current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #         self._error_message = f"{current_datetime} NO ERROR"
    #     if "NO ERROR" in self._error_message:
    #         return f'{self._error_message}'
    #     return f'{self._error_message}'

    # message = attribute(
    #     label="error message",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    #     polling_period=1000,
    # )

    # def read_message(self):
    #     self.dev.write(b"TB?\r")
    #     reply = self.dev.readline().decode().replace('\r\n', '')
    #     current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     self._message = f"{current_datetime} {reply.split(', ')[-1]}"
    #     if reply.split(', ')[0] != '0':
    #         self._error_message = self._message
    #         self.should_stop = True
    #         self.logger.info(self._message)
    #     return self._message

    # raw_command = attribute(
    #     label="raw command",
    #     dtype=str,
    #     memorized=True,
    #     access=AttrWriteType.READ_WRITE,
    #     doc="No carriage-return required. https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    # )

    # def read_raw_command(self):
    #     return self._raw_command_return

    # @clear_error_wrap
    # def write_raw_command(self, value):
    #     if value != '':
    #         self.dev.write(f"{value}\r".encode())
    #         self._raw_command_return = self.dev.readline().decode().replace('\r\n', '')

    # @command(dtype_in=int)
    # def home(self, axis=1):
    #     self.dev.write(f"{axis}OR\r".encode())

    # @command
    # def home(self,):
    #     axis = self.axis.split(',')
    #     for a in axis:
    #         self.dev.write(f"{a}ST\r".encode())
    #     self.dev.write(f"{1}OR\r".encode())

    # @command(dtype_in=int)
    # def emergency_stop(self):
    #     axis = self.axis.split(',')
    #     for a in axis:
    #         self.dev.write(f"{a}AB\r".encode())

    # @command()
    # def stop(self):
    #     axis = self.axis.split(',')
    #     for a in axis:
    #         self.dev.write(f"{a}ST\r".encode())
    #     self.should_stop = True

    @command(dtype_in=bool)
    def move_relative_axis1(self, plus=True):
        self.dev.PS90_SetTargetMode(1, 1, 0)
        if plus:
            self.dev.PS90_MoveEx(1, 1, c_double(self._ax1_step), 1)
        else:
            self.dev.PS90_MoveEx(1, 1, c_double(-self._ax1_step), 1)
        self.logger.info(f'{self._ax1_step}, {plus}')

    @command(dtype_in=bool)
    def move_relative_axis2(self, plus=True):
        self.dev.PS90_SetTargetMode(1, 2, 0)
        if plus:
            self.dev.PS90_MoveEx(1, 2, c_double(self._ax1_step), 1)
        else:
            self.dev.PS90_MoveEx(1, 2, c_double(-self._ax1_step), 1)
        self.logger.info(f'{self._ax2_step}, {plus}')

    # @command(dtype_in=bool)
    # @clear_error_wrap
    # def move_relative_axis2(self, plus=True):
    #     if plus:
    #         self.dev.write(f"2PR{self._ax2_step:.3f}\r".encode())
    #     else:
    #         self.dev.write(f"2PR{-self._ax2_step:.3f}\r".encode())

    # @command(dtype_in=bool)
    # @clear_error_wrap
    # def move_relative_axis3(self, plus=True):
    #     if plus:
    #         self.dev.write(f"3PR{self._ax3_step:.3f}\r".encode())
    #     else:
    #         self.dev.write(f"3PR{-self._ax3_step:.3f}\r".encode())

    # @command(dtype_in=bool)
    # @clear_error_wrap
    # def move_relative_axis12(self, plus=True):
    #     if plus:
    #         self.dev.write(f"1PR{self._ax12_step:.3f}\r".encode())
    #         self.dev.write(f"2PR{self._ax12_step:.3f}\r".encode())
    #     else:
    #         self.dev.write(f"1PR{-self._ax12_step:.3f}\r".encode())
    #         self.dev.write(f"2PR{-self._ax12_step:.3f}\r".encode())

    # def wait_until_stop(self, axis=1):
    #     while True:
    #         self.dev.write(f"{axis}MD?\r".encode())
    #         reply = self.dev.readline().decode().replace('\r\n', '')
    #         # if reply is one, this means the motion has stopped. There can be two cases. One is the stage is at the desired location and the other is the stage stopped by an error. It is noted that a manual stop command will also cause an error during move to limit process.
    #         if reply == "1":
    #             self.read_message()
    #             if not self._error_message or "NO ERROR" not in self._error_message:
    #                 self.stop_whole_function_due_to_error = True
    #             break
    #         time.sleep(1)

    # def threaded_reset_to_TA1(self):
    #     self.stop_whole_function_due_to_error = False
    #     self.ax1_negative_limit()
    #     self.wait_until_stop(axis=1)
    #     if self.stop_whole_function_due_to_error:
    #         return
    #     self.ax2_positive_limit()
    #     self.wait_until_stop(axis=2)
    #     if self.stop_whole_function_due_to_error:
    #         return
    #     self.dev.write(f"1DH-1\r".encode())
    #     self.dev.write(f"2DH211.05\r".encode())
    #     self.dev.write(f"1PA{self.TA1[0]:.3f}\r".encode())
    #     self.dev.write(f"2PA{self.TA1[1]:.3f}\r".encode())


if __name__ == "__main__":
    OwisPS.run_server()
