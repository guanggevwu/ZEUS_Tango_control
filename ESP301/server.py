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
import socket

# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class ESP301(Device):

    com = device_property(dtype=str, default_value='COM1')
    ip = device_property(dtype=str, default_value='')
    extra_script = device_property(dtype=str, default_value='')

    @staticmethod
    def clear_error_wrap(func):
        '''
        A decorator to clear error message and restart auto polling reading error message.
        This decorator is applied to all write functions, except for "stop" and change relative move steps.
        '''
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self._error_message = None
            self.should_stop = False
            func(self, *args, **kwargs)
        return wrapper

    def dev_write(self, *args, **kwargs):
        if self.ip:
            return self.controller_socket.sendall(*args, **kwargs)
        else:
            return self.dev_write(*args, **kwargs)

    def dev_read(self, *args, **kwargs):
        if self.ip:
            return self.controller_socket.recv(1024).decode().strip()
        else:
            return self.dev.readline().decode().strip()

    def init_device(self):
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        self.get_logger = logging.getLogger(self.__class__.__name__)
        if not hasattr(self, 'friendly_name'):
            self.friendly_name = self.__class__.__name__
        self.logger = LoggerAdapter(self.friendly_name, self.get_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        super().init_device()
        self.set_state(DevState.INIT)
        try:
            if self.ip:
                self.controller_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                # Set a timeout for the connection
                self.controller_socket.settimeout(5)
                self.controller_socket.connect((self.ip, 5001))
                self.logger.info(
                    f"Successfully connected to ESP302 at {self.ip}")
            else:
                self.dev = serial.Serial(
                    port=self.com, baudrate=19200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self.should_stop = False
            self._read_time = "N/A"
            self._user_defined_name = 'esp301'
            self._host_computer = platform.node()
            self._ax1_step, self._ax2_step, self._ax3_step, self._ax12_step, self._ax1_status, self._ax2_status, self._ax3_status = 0, 0, 0, 0, False, False, False
            self._raw_command_return = ''
            self.unit_code = {0: "unknown",
                              1: "unknown", 2: "mm", 3: "um", 7: "deg"}
            self.axis = []
            for axis in range(1, 4):
                self.dev_write(f"{axis}ID?\r".encode())
                reply = self.dev_read()
                if "NO STAGE" not in reply:
                    self.axis.append(axis)
                    self.dev_write(f"{axis}SN?\r".encode())
                    setattr(self, f"_axis{axis}_unit", self.unit_code[
                        int(self.dev_read())])
                    self.dev_write(f"{axis}ZS00H\r".encode())
            self._error_message = None
            # print(
            #     f'ESP301 is connected. Model: {self._model}. Serial number: {self._serial_number}')
            self.set_status("ESP301 device is connected.")
        except:
            print("Could NOT connect to  ESP device.")
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

    @clear_error_wrap
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

    def create_position_attribute(self, axis):
        self.logger.info(f'created axis{axis} position.')
        attr = attribute(
            name=f"ax{axis}_position",
            label=f"axis {axis} position",
            dtype=float,
            unit=getattr(self, f"_axis{axis}_unit"),
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_read_position_function(self, axis):
        def read_position(self, attr):
            self.dev_write(f"{axis}TP\r".encode())
            setattr(self, f'_ax{axis}_position', float(self.dev_read()))
            return getattr(self, f'_ax{axis}_position')
        self.logger.info(f'created read function for axis {axis} position')
        return read_position

    def create_write_position_function(self, axis):
        @ESP301.clear_error_wrap
        def write_position(self, attr):
            value = attr.get_write_value()
            setattr(self, f'_ax{axis}_position', value)
            self.dev_write(f"{axis}PA{value:.3f}\r".encode())
        self.logger.info(f'created write function for axis {axis} position')
        return write_position

    def create_ax_step_attribute(self, axis):
        self.logger.info(f'created axis{axis} step.')
        attr = attribute(
            name=f"ax{axis}_step",
            label=f"axis {axis} step",
            dtype=float,
            unit=getattr(self, f"_axis{axis}_unit"),
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_ax_status(self, axis):
        self.logger.info(f'created axis{axis} status.')
        attr = attribute(
            name=f"ax{axis}_status",
            label=f"axis {axis} status",
            dtype=bool,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        return attr

    def create_read_status_function(self, axis):
        def read_status(self, attr):
            self.dev_write(f"{axis}MO?\r".encode())
            reply = self.dev_read()
            if reply == '1':
                setattr(self, f'_ax{axis}_status', True)
            elif reply == '0':
                setattr(self, f'_ax{axis}_status', False)
            return getattr(self, f'_ax{axis}_status')
        self.logger.info(f'created read function for axis {axis} status')
        return read_status

    def create_write_status_function(self, axis):
        def write_status(self, attr):
            value = attr.get_write_value()
            setattr(self, f'_ax{axis}_status', value)
            if value:
                self.dev_write(f"{axis}MO\r".encode())
            else:
                self.dev_write(f"{axis}MF\r".encode())
        self.logger.info(f'created write function for axis {axis} status')
        return write_status

    def initialize_dynamic_attributes(self):
        customized_location = attribute(
            name="customized_location",
            label="customized location",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

        cmd_move_relative_axis12 = command(
            f=self.move_relative_axis12,
            dtype_in=bool,)

        cmd_move_to_negative_limit = command(
            f=self.move_to_negative_limit, dtype_in=int,)
        cmd_move_to_positive_limit = command(
            f=self.move_to_positive_limit, dtype_in=int,)

        cmd_set_as_zero = command(
            f=self.set_as_zero, dtype_in=int,)

        @command()
        @ESP301.clear_error_wrap
        def ax2_positive_limit(self):
            self.dev_write(f"2MT+\r".encode())

        @command()
        @ESP301.clear_error_wrap
        def reset_to_TA1(self):
            Thread(target=self.threaded_reset_to_TA1).start()

        for axis in range(1, 4):
            if axis in self.axis:
                setattr(self, f'read_ax{axis}_position',
                        self.create_read_position_function(axis))
                setattr(self, f'write_ax{axis}_position',
                        self.create_write_position_function(axis))
                self.add_attribute(self.create_position_attribute(axis))
                self.add_attribute(self.create_ax_step_attribute(axis))
                setattr(self, f'read_ax{axis}_status',
                        self.create_read_status_function(axis))
                setattr(self, f'write_ax{axis}_status',
                        self.create_write_status_function(axis))
                self.add_attribute(self.create_ax_status(axis))
                self.add_command(cmd_move_to_negative_limit)
                self.add_command(cmd_move_to_positive_limit)
                self.add_command(cmd_set_as_zero)
                # self.add_command(cmd_move_relative_axis12)
        # only for a special case
        # if 1 in self.axis and 2 in self.axis and self._axis1_unit == self._axis2_unit:
            # ax12_distance = attribute(
            #     name="ax12_distance",
            #     label="ax12 distance",
            #     dtype=float,
            #     unit=self._axis1_unit,
            #     format='6.3f',
            #     access=AttrWriteType.READ,
            # )

            # ax12_step = attribute(
            #     name="ax12_step",
            #     label="ax12 step",
            #     dtype=float,
            #     unit=self._axis1_unit,
            #     format='6.3f',
            #     memorized=True,
            #     hw_memorized=True,
            #     access=AttrWriteType.READ_WRITE,
            #     doc='steps for axis 1 and axis 2 are the same, so this attribute is used for both axes.',
            # )
        #     self.add_attribute(ax12_distance)
        #     self.add_attribute(ax12_step)
            # self.add_command(cmd)
        if hasattr(self, "extra_script"):
            if self.extra_script == "turning_box_3":
                # axis 1: -88 to 14 mm. axis 2: 0 to 135 deg. When axis 1 is in -88 to -46 (limit might be close to -30), axis 2 is free to rotate.
                self.TA1 = [0, 135]
                self.TA2 = [89, 0]
                self.TA3 = [101, 90]
                # ta_test position is not fixed, it is set when the user clicks the button.
                self.TA_test = [0, 2.5]
                self.add_attribute(customized_location)
                self.add_command(reset_to_TA1)

    def read_ax12_distance(self, attr):
        return float(f'{(self._ax1_position-self._ax2_position):.3f}')

    def read_ax1_step(self, attr):
        return self._ax1_step

    def write_ax1_step(self, attr):
        self._ax1_step = attr.get_write_value()

    def read_ax2_step(self, attr):
        return self._ax2_step

    def write_ax2_step(self, attr):
        self._ax2_step = float(attr.get_write_value())

    def read_ax3_step(self, attr):
        return self._ax3_step

    def write_ax3_step(self, attr):
        self._ax3_step = float(attr.get_write_value())

    def read_ax12_step(self, attr):
        return self._ax12_step

    def write_ax12_step(self, attr):
        self._ax12_step = float(attr.get_write_value())

    def read_customized_location(self, attr):
        if hasattr(self, '_ax1_position'):
            if abs(self._ax1_position - self.TA1[0]) < 0.1 and abs(self._ax2_position - self.TA1[1]) < 0.1:
                self._customized_location = 'TA1'
            elif abs(self._ax1_position - self.TA2[0]) < 0.1 and abs(self._ax2_position - self.TA2[1]) < 0.1:
                self._customized_location = 'TA2'
            elif abs(self._ax1_position - self.TA3[0]) < 0.1 and abs(self._ax2_position - self.TA3[1]) < 0.1:
                self._customized_location = 'TA3'
            elif abs(self._ax1_position - self.TA_test[0]) < 0.1 and abs(self._ax2_position - self.TA_test[1]) < 0.1:
                self._customized_location = 'TA_test'
            else:
                self._customized_location = 'Undefined'
        else:
            self._customized_location = 'Not initialized'
        return self._customized_location

    @clear_error_wrap
    def write_customized_location(self, attr):
        Thread(target=self.threaded_write_customized_location,
               args=(attr,)).start()

    def wait_until_arrive(self, axis, dest, interval=1):
        while abs(dest-getattr(self, f'_ax{axis}_position')) > 0.1:
            time.sleep(interval)
            print(f"waiting for axis {axis}")
            if self.should_stop:
                break

    def threaded_write_customized_location(self, attr):
        value = attr.get_write_value()
        ax1_previous_step = self._ax1_step
        ax2_previous_step = self._ax2_step
        ax1_previous_position = self._ax1_position
        ax2_previous_position = self._ax2_position
        # value is the requested position, i.e., from self._customized_location to value.
        if value.lower() == 'ta2' and self._customized_location == 'TA1':
            # rotate and then move forward
            self._ax1_step = self.TA2[0] - self.TA1[0]
            self._ax2_step = self.TA2[1] - self.TA1[1]
            self.move_relative_axis([2, True])
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self.move_relative_axis([1, True])
        elif value.lower() == 'ta3' and self._customized_location == 'TA1':
            # rotate and then move forward
            self._ax1_step = self.TA3[0] - self.TA1[0]
            self._ax2_step = self.TA3[1] - self.TA1[1]
            self.move_relative_axis([2, True])
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self.move_relative_axis([1, True])
        elif value.lower() == 'ta1' and self._customized_location == 'TA2':
            # move backward and then rotate
            self._ax1_step = self.TA1[0] - self.TA2[0]
            self._ax2_step = self.TA1[1] - self.TA2[1]
            self.move_relative_axis([1, True])
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis([2, True])
        elif value.lower() == 'ta1' and self._customized_location == 'TA3':
            # move backward and then rotate
            self._ax1_step = self.TA1[0] - self.TA3[0]
            self._ax2_step = self.TA1[1] - self.TA3[1]
            self.move_relative_axis([1, True])
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis([2, True])
        elif value.lower() == 'ta2' and self._customized_location == 'TA3':
            # move backward, rotate and then move forward. Note the procedure is different.
            self._ax1_step = -60
            self._ax2_step = self.TA2[1] - self.TA3[1]
            self.move_relative_axis([1, True])
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis([2, True])
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self._ax1_step = 48
            self.move_relative_axis([1, True])
        elif value.lower() == 'ta3' and self._customized_location == 'TA2':
            # move backward, rotate and then move forward.
            self._ax1_step = -48
            self._ax2_step = self.TA3[1] - self.TA2[1]
            self.move_relative_axis([1, True])
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis([2, True])
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self._ax1_step = 60
            self.move_relative_axis([1, True])
        elif value == 'TA_test':
            self.TA_test[0] = self._ax1_position
            self.TA_test[1] = self._ax2_position + 5
            self._ax1_step = 5
            self._ax2_step = 5
            self.move_relative_axis([1, True])
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis([2, True])
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self.move_relative_axis1(plus=False)
        self._ax1_step = ax1_previous_step
        self._ax2_step = ax2_previous_step

    error_message = attribute(
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
        doc="refer to error appendix: https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    )

    def read_error_message(self):
        if not self._error_message:
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._error_message = f"{current_datetime} NO ERROR"
        if "NO ERROR" in self._error_message:
            return f'{self._error_message}'
        return f'{self._error_message}'

    message = attribute(
        label="message",
        dtype="str",
        access=AttrWriteType.READ,
        polling_period=1000,
    )

    def read_message(self):
        self.dev_write(b"TB?\r")
        reply = self.dev_read()
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._message = f"{current_datetime} {reply.split(', ')[-1]}"
        if reply.split(', ')[0] != '0':
            self._error_message = self._message
            self.should_stop = True
            self.logger.info(self._message)
        return self._message

    raw_command = attribute(
        label="raw command",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc="No carriage-return required. https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf"
    )

    def read_raw_command(self):
        return self._raw_command_return

    @clear_error_wrap
    def write_raw_command(self, value):
        if value != '':
            self.dev_write(f"{value}\r".encode())
            self._raw_command_return = self.dev_read()

    # @command(dtype_in=int)
    # def home(self, axis=1):
    #     self.dev_write(f"{axis}OR\r".encode())

    # @command
    # def home(self,):
    #     axis = self.axis.split(',')
    #     for a in axis:
    #         self.dev_write(f"{a}ST\r".encode())
    #     self.dev_write(f"{1}OR\r".encode())

    # @command(dtype_in=int)
    # def emergency_stop(self):
    #     axis = self.axis.split(',')
    #     for a in axis:
    #         self.dev_write(f"{a}AB\r".encode())

    @command()
    def stop(self):
        for a in self.axis:
            self.dev_write(f"{a}ST\r".encode())
        self.should_stop = True

    @command()
    def move_relative_axis(self, input: list[int]):
        if input[1]:
            self.dev_write(
                f"{input[0]}PR{getattr(self, f'_ax{input[0]}_step'):.3f}\r".encode())
        else:
            self.dev_write(
                f"{input[0]}PR{-getattr(self, f'_ax{input[0]}_step'):.3f}\r".encode())
        self.logger.info(f'relative moving, [direction, axis], {input}')

    @clear_error_wrap
    def move_relative_axis12(self, plus: bool = True):
        self.logger.info(f'relative moving of axis 1 and 2')
        # if plus:
        #     self.dev_write(f"1PR{self._ax12_step:.3f}\r".encode())
        #     self.dev_write(f"2PR{self._ax12_step:.3f}\r".encode())
        # else:
        #     self.dev_write(f"1PR{-self._ax12_step:.3f}\r".encode())
        #     self.dev_write(f"2PR{-self._ax12_step:.3f}\r".encode())

    @clear_error_wrap
    def move_to_negative_limit(self, axis):
        self.logger.info(f'negative limit of axis {axis}')
        self.dev_write(f"{axis}MT-\r".encode())

    @clear_error_wrap
    def move_to_positive_limit(self, axis):
        self.logger.info(f'positive limit of axis {axis}')
        self.dev_write(f"{axis}MT+\r".encode())

    @clear_error_wrap
    def set_as_zero(self, axis):
        self.logger.info(f'setting axis {axis} as zero')
        self.dev_write(f"{axis}DH0\r".encode())

    def wait_until_stop(self, axis=1):
        while True:
            self.dev_write(f"{axis}MD?\r".encode())
            reply = self.dev_read()
            # if reply is one, this means the motion has stopped. There can be two cases. One is the stage is at the desired location and the other is the stage stopped by an error. It is noted that a manual stop command will also cause an error during move to limit process.
            if reply == "1":
                self.read_message()
                if not self._error_message or "NO ERROR" not in self._error_message:
                    self.stop_whole_function_due_to_error = True
                break
            time.sleep(1)

    def threaded_reset_to_TA1(self):
        self.stop_whole_function_due_to_error = False
        self.move_to_negative_limit(axis=1)
        self.wait_until_stop(axis=1)
        if self.stop_whole_function_due_to_error:
            return
        self.move_to_positive_limit(axis=2)
        self.wait_until_stop(axis=2)
        if self.stop_whole_function_due_to_error:
            return
        self.dev_write(f"1DH-1\r".encode())
        self.dev_write(f"2DH211.05\r".encode())
        self.dev_write(f"1PA{self.TA1[0]:.3f}\r".encode())
        self.dev_write(f"2PA{self.TA1[1]:.3f}\r".encode())


if __name__ == "__main__":
    ESP301.run_server()
