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
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class ESP301(Device):

    com = device_property(dtype=str, default_value='COM1')
    axis = device_property(dtype=str, default_value='1,2,3')
    extra_script = device_property(dtype=str, default_value='')

    @staticmethod
    def clear_error_wrap(func):
        '''
        A decorator to clear error message and restart auto polling reading error message.
        This decorator is applied to all write functions, except for "stop" and change relative move steps.
        '''
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args[0]._error_message = None
            args[0].should_stop = False
            func(*args, **kwargs)
        return wrapper

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
            self.dev.write(b"1SN?\r")
            self._axis1_unit = self.unit_code[
                int(self.dev.readline().decode().replace('\r\n', ''))]
            self.dev.write(b"2SN?\r")
            self._axis2_unit = self.unit_code[
                int(self.dev.readline().decode().replace('\r\n', ''))]
            self.dev.write(b"3SN?\r")
            self._axis3_unit = self.unit_code[
                int(self.dev.readline().decode().replace('\r\n', ''))]
            self._error_message = None
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

    def initialize_dynamic_attributes(self):
        ax1_position = attribute(
            name="ax1_position",
            label="axis 1 position",
            dtype=float,
            unit=self._axis1_unit,
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_position = attribute(
            name="ax2_position",
            label="axis 2 position",
            dtype=float,
            unit=self._axis2_unit,
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_position = attribute(
            name="ax3_position",
            label="axis 3 position",
            dtype=float,
            unit=self._axis3_unit,
            format='6.3f',
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

        ax12_distance = attribute(
            name="ax12_distance",
            label="ax12 distance",
            dtype=float,
            unit=self._axis1_unit,
            format='6.3f',
            access=AttrWriteType.READ,
        )
        ax1_step = attribute(
            name="ax1_step",
            label="axis 1 step",
            dtype=float,
            unit=self._axis1_unit,
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_step = attribute(
            name="ax2_step",
            label="axis 2 step",
            dtype=float,
            unit=self._axis2_unit,
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_step = attribute(
            name="ax3_step",
            label="axis 3 step",
            dtype=float,
            unit=self._axis3_unit,
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax12_step = attribute(
            name="ax12_step",
            label="ax12 step",
            dtype=float,
            unit=self._axis1_unit,
            format='6.3f',
            memorized=True,
            hw_memorized=True,
            access=AttrWriteType.READ_WRITE,
            doc='steps for axis 1 and axis 2 are the same, so this attribute is used for both axes.',
        )
        ax1_status = attribute(
            name="ax1_status",
            label="axis 1 status",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax2_status = attribute(
            name="ax2_status",
            label="axis 2 status",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        ax3_status = attribute(
            name="ax3_status",
            label="axis 3 status",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )
        customized_location = attribute(
            name="customized_location",
            label="customized location",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

        @command()
        @ESP301.clear_error_wrap
        def ax1_negative_limit(self):
            self.dev.write(f"1MT-\r".encode())

        @command()
        @ESP301.clear_error_wrap
        def ax2_positive_limit(self):
            self.dev.write(f"2MT+\r".encode())

        @command()
        @ESP301.clear_error_wrap
        def reset_to_TA1(self):
            Thread(target=self.threaded_reset_to_TA1).start()

        if '1' in self.axis:
            self.add_attribute(ax1_position)
            self.add_attribute(ax1_step)
            self.add_attribute(ax1_status)
        if '2' in self.axis:
            self.add_attribute(ax2_position)
            self.add_attribute(ax2_step)
            self.add_attribute(ax2_status)
        if '3' in self.axis:
            self.add_attribute(ax3_position)
            self.add_attribute(ax3_step)
            self.add_attribute(ax3_status)
        if '1' in self.axis and '2' in self.axis and self._axis1_unit == self._axis2_unit:
            self.add_attribute(ax12_distance)
            self.add_attribute(ax12_step)
        if hasattr(self, "extra_script"):
            if self.extra_script == "turning_box_3":
                # axis 1: -88 to 14 mm. axis 2: 0 to 135 deg. When axis 1 is in -88 to -46 (limit might be close to -30), axis 2 is free to rotate.
                self.TA1 = [0, 135]
                self.TA2 = [89, 0]
                self.TA3 = [101, 90]
                # ta_test position is not fixed, it is set when the user clicks the button.
                self.TA_test = [0, 2.5]
                self.add_attribute(customized_location)
                self.add_command(ax1_negative_limit)
                self.add_command(ax2_positive_limit)
                self.add_command(reset_to_TA1)

    def read_ax1_position(self, attr):
        self.dev.write(b"1TP\r")
        self._ax1_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax1_position

    @clear_error_wrap
    def write_ax1_position(self, attr):
        self._ax1_position = attr.get_write_value()
        self.dev.write(f"1PA{self._ax1_position:.3f}\r".encode())

    def read_ax2_position(self, attr):
        self.dev.write(b"2TP\r")
        self._ax2_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax2_position

    @clear_error_wrap
    def write_ax2_position(self, attr):
        self._ax2_position = attr.get_write_value()
        self.dev.write(f"2PA{self._ax2_position:.3f}\r".encode())

    def read_ax3_position(self, attr):
        self.dev.write(b"3TP\r")
        self._ax3_position = float(
            self.dev.readline().decode().replace('\r\n', ''))
        return self._ax3_position

    @clear_error_wrap
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
        self._ax2_step = float(attr.get_write_value())

    def read_ax3_step(self, attr):
        return self._ax3_step

    def write_ax3_step(self, attr):
        self._ax3_step = float(attr.get_write_value())

    def read_ax12_step(self, attr):
        return self._ax12_step

    def write_ax12_step(self, attr):
        self._ax12_step = float(attr.get_write_value())

    def read_ax1_status(self, attr):
        self.dev.write(b"1MO?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        if reply == '1':
            self._ax1_status = "On"
        elif reply == '0':
            self._ax1_status = "Off"
        return self._ax1_status

    @clear_error_wrap
    def write_ax1_status(self, attr):
        self._ax1_status = attr.get_write_value()
        if attr.get_write_value().lower() == "on":
            self.dev.write(b"1MO\r")
        elif attr.get_write_value().lower() == "off":
            self.dev.write(b"1MF\r")

    def read_ax2_status(self, attr):
        self.dev.write(b"2MO?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        if reply == '1':
            self._ax2_status = "On"
        elif reply == '0':
            self._ax2_status = "Off"
        return self._ax2_status

    @clear_error_wrap
    def write_ax2_status(self, attr):
        self._ax2_status = attr.get_write_value()
        if attr.get_write_value().lower() == "on":
            self.dev.write(b"2MO\r")
        elif attr.get_write_value().lower() == "off":
            self.dev.write(b"2MF\r")

    def read_ax3_status(self, attr):
        self.dev.write(b"3MO?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
        if reply == '1':
            self._ax3_status = "On"
        elif reply == '0':
            self._ax3_status = "Off"
        return self._ax3_status

    @clear_error_wrap
    def write_ax3_status(self, attr):
        self._ax3_status = attr.get_write_value()
        if attr.get_write_value().lower() == "on":
            self.dev.write(b"3MO\r")
        elif attr.get_write_value().lower() == "off":
            self.dev.write(b"3MF\r")

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
            self.move_relative_axis2()
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self.move_relative_axis1()
        elif value.lower() == 'ta3' and self._customized_location == 'TA1':
            # rotate and then move forward
            self._ax1_step = self.TA3[0] - self.TA1[0]
            self._ax2_step = self.TA3[1] - self.TA1[1]
            self.move_relative_axis2()
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self.move_relative_axis1()
        elif value.lower() == 'ta1' and self._customized_location == 'TA2':
            # move backward and then rotate
            self._ax1_step = self.TA1[0] - self.TA2[0]
            self._ax2_step = self.TA1[1] - self.TA2[1]
            self.move_relative_axis1()
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis2()
        elif value.lower() == 'ta1' and self._customized_location == 'TA3':
            # move backward and then rotate
            self._ax1_step = self.TA1[0] - self.TA3[0]
            self._ax2_step = self.TA1[1] - self.TA3[1]
            self.move_relative_axis1()
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis2()
        elif value.lower() == 'ta2' and self._customized_location == 'TA3':
            # move backward, rotate and then move forward. Note the procedure is different.
            self._ax1_step = -60
            self._ax2_step = self.TA2[1] - self.TA3[1]
            self.move_relative_axis1()
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis2()
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self._ax1_step = 48
            self.move_relative_axis1()
        elif value.lower() == 'ta3' and self._customized_location == 'TA2':
            # move backward, rotate and then move forward.
            self._ax1_step = -48
            self._ax2_step = self.TA3[1] - self.TA2[1]
            self.move_relative_axis1()
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis2()
            self.wait_until_arrive(2, ax2_previous_position+self._ax2_step)
            if self.should_stop:
                return
            self._ax1_step = 60
            self.move_relative_axis1()
        elif value == 'TA_test':
            self.TA_test[0] = self._ax1_position
            self.TA_test[1] = self._ax2_position + 5
            self._ax1_step = 5
            self._ax2_step = 5
            self.move_relative_axis1()
            self.wait_until_arrive(1, ax1_previous_position+self._ax1_step)
            if self.should_stop:
                return
            self.move_relative_axis2()
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
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
        polling_period=1000,
    )

    def read_message(self):
        self.dev.write(b"TB?\r")
        reply = self.dev.readline().decode().replace('\r\n', '')
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
            self.dev.write(f"{value}\r".encode())
            self._raw_command_return = self.dev.readline().decode().replace('\r\n', '')

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

    @command()
    def stop(self):
        axis = self.axis.split(',')
        for a in axis:
            self.dev.write(f"{a}ST\r".encode())
        self.should_stop = True

    @command(dtype_in=bool)
    @clear_error_wrap
    def move_relative_axis1(self, plus=True):
        if plus:
            self.dev.write(f"1PR{self._ax1_step:.3f}\r".encode())
        else:
            self.dev.write(f"1PR{-self._ax1_step:.3f}\r".encode())
        print(f'{self._ax1_step}, {plus}')
        # self.dev.write(f"1PR{rel:.3f}\r".encode())

    @command(dtype_in=bool)
    @clear_error_wrap
    def move_relative_axis2(self, plus=True):
        if plus:
            self.dev.write(f"2PR{self._ax2_step:.3f}\r".encode())
        else:
            self.dev.write(f"2PR{-self._ax2_step:.3f}\r".encode())

    @command(dtype_in=bool)
    @clear_error_wrap
    def move_relative_axis3(self, plus=True):
        if plus:
            self.dev.write(f"3PR{self._ax3_step:.3f}\r".encode())
        else:
            self.dev.write(f"3PR{-self._ax3_step:.3f}\r".encode())

    @command(dtype_in=bool)
    @clear_error_wrap
    def move_relative_axis12(self, plus=True):
        if plus:
            self.dev.write(f"1PR{self._ax12_step:.3f}\r".encode())
            self.dev.write(f"2PR{self._ax12_step:.3f}\r".encode())
        else:
            self.dev.write(f"1PR{-self._ax12_step:.3f}\r".encode())
            self.dev.write(f"2PR{-self._ax12_step:.3f}\r".encode())

    def wait_until_stop(self, axis=1):
        while True:
            self.dev.write(f"{axis}MD?\r".encode())
            reply = self.dev.readline().decode().replace('\r\n', '')
            # if reply is one, this means the motion has stopped. There can be two cases. One is the stage is at the desired location and the other is the stage stopped by an error. It is noted that a manual stop command will also cause an error during move to limit process.
            if reply == "1":
                self.read_message()
                if not self._error_message or "NO ERROR" not in self._error_message:
                    self.stop_whole_function_due_to_error = True
                break
            time.sleep(1)

    def threaded_reset_to_TA1(self):
        self.stop_whole_function_due_to_error = False
        self.ax1_negative_limit()
        self.wait_until_stop(axis=1)
        if self.stop_whole_function_due_to_error:
            return
        self.ax2_positive_limit()
        self.wait_until_stop(axis=2)
        if self.stop_whole_function_due_to_error:
            return
        self.dev.write(f"1DH-1\r".encode())
        self.dev.write(f"2DH211.05\r".encode())
        self.dev.write(f"1PA{self.TA1[0]:.3f}\r".encode())
        self.dev.write(f"2PA{self.TA1[1]:.3f}\r".encode())


if __name__ == "__main__":
    ESP301.run_server()
