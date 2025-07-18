#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import logging
import pyvisa
import platform
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
if True:
    from Basler.server import Basler, LoggerAdapter
# -----------------------------
handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class DG645(Device):

    friendly_name = device_property(dtype=str, default_value='')
    ip = device_property(dtype=str, default_value='')
    socket = '5024'

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
        self.logger = LoggerAdapter(value, self.logger_base)

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    trigger = attribute(
        label="trigger",
        dtype="str",
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_trigger(self):
        self.device.write('TSRC?')
        response = self.device.read()
        self._trigger = [key for key, value in self.trigger_table.items(
        ) if value == int(response)][0]
        return self._trigger

    def write_trigger(self, value):
        self.device.write(f'TSRC{self.trigger_table[value]}')

    internal_rate = attribute(
        label="internal rate",
        dtype=float,
        memorized=True,
        min_value=0.001,
        max_value=1e6,
        access=AttrWriteType.READ_WRITE,
        doc='Only applicable to internal mode.')

    def read_internal_rate(self):
        self.device.write('TRAT?')
        self._internal_rate = float(self.device.read())
        return self._internal_rate

    def write_internal_rate(self, value):
        self.device.write(f'TRAT {value}')

    # TODO: Implement burst rate
    # burst_rate = attribute(
    #     label="burst rate",
    #     dtype=float,
    #     memorized=True,
    #     min_value=0.001,
    #     max_value=1e6,
    #     access=AttrWriteType.READ_WRITE,
    #     doc="Only applicable to burst mode",
    # )

    # def read_burst_rate(self):
    #     self._internal_rate = float(self.device.query('TR1'))
    #     return self._internal_rate

    # def write_burst_rate(self, value):
    #     self.device.write(f'TR1, {value}')

    send_write = attribute(
        label="send command",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc="Refer to DG645 manual for the command",
    )

    def read_send_write(self):
        if not hasattr(self, '_last_command'):
            self._response = ''
        return self._response

    def write_send_write(self, value):
        self.device.write(f'{value}')
        if "?" in value:
            self._response = self.device.read()

    channel_table = {'T0': 0, 'T1': 1, 'A': 2, 'B': 3,
                     'C': 4, 'D': 5, 'E': 6, 'F': 7, 'G': 8, 'H': 9}
    channel_attr_table = {'A': 2, 'B': 3, 'C': 4,
                          'D': 5, 'E': 6, 'F': 7, 'G': 8, 'H': 9}
    trigger_table = {'Internal': 0, 'External rising': 1, 'External falling': 2,
                     'Single shot external rising edges': 3, 'Single shot external falling edges': 4, 'Single shot': 5, "Line": 6}

    def read_delay(self, channel):
        relative_chanel, delay = self.device.query(
            f'DLAY?{self.channel_table[channel]}').replace('\r', '').replace('\n', '').split(',')
        delay = f'{float(delay):.12e}'
        relative_chanel = [key for key, value in self.channel_table.items(
        ) if value == int(relative_chanel)][0]
        return relative_chanel, delay

    def write_delay(self, channel, relative_channel, delay):
        if float(delay) < 0 or float(delay) > 999.99:
            return
        self.device.write(
            f'DLAY{self.channel_table[channel]},{self.channel_table[relative_channel]}, {delay}')

    def create_read_relative_channel_func(self, channel):
        def func(*args, **kwargs):
            setattr(self, f'_{channel}_relative_channel', self.read_delay(
                channel)[0])
            return getattr(self, f'_{channel}_relative_channel')
        return func

    def create_read_relative_delay_func(self, channel):
        def func(*args, **kwargs):
            setattr(self, f'_{channel}_relative_delay', self.read_delay(
                channel)[1])
            return getattr(self, f'_{channel}_relative_delay')
        return func

    def create_write_relative_channel_func(self, channel):
        # Explicitly adding self as the first position argument to exclude it from *args. The reason is self is by default passed to the read/write function when we call tango.DeviceProxy().attribute.
        def func(self, *args, **kwargs):
            # Use position argument until the position argument is in *args
            self.write_delay(channel, delay=getattr(self, f'_{channel}_relative_delay'), *
                             (a.get_write_value() for a in args), **kwargs)
        return func

    def create_write_relative_delay_func(self, channel):
        def func(self, *args, **kwargs):
            self.write_delay(
                channel, getattr(self, f'_{channel}_relative_channel'), *(a.get_write_value() for a in args), **kwargs)
        return func

    def initialize_dynamic_attributes(self):
        # add attributes
        for arg1 in self.channel_attr_table:
            self.add_attribute(attribute(name=f'{arg1}_relative_channel', label=f'{arg1} relative channel',
                                         dtype=str,
                                         memorized=True,
                                         access=AttrWriteType.READ_WRITE))
            self.add_attribute(attribute(name=f'{arg1}_relative_delay', label=f'{arg1} relative delay (s)',
                                         dtype=str,
                                         memorized=True,
                                         #  format='%.6E',
                                         access=AttrWriteType.READ_WRITE))

    def init_device(self):
        super().init_device()
        self._host_computer = platform.node()
        self._user_defined_name = ''
        self.logger_base = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self._user_defined_name, self.logger_base)
        try:
            rm = pyvisa.ResourceManager()
            self.device = rm.open_resource(f'TCPIP0::{self.ip}::INSTR')
            self.device.write_termination = '\r'
            self.device.read_termination = '\r\n'
            for channel in self.channel_attr_table:
                # add read function. run read function. add write function.
                setattr(self, f'read_{channel}_relative_channel', self.create_read_relative_channel_func(
                    channel))
                setattr(self, f'read_{channel}_relative_delay', self.create_read_relative_delay_func(
                    channel))
                getattr(self, f'read_{channel}_relative_channel')()
                getattr(self, f'read_{channel}_relative_delay')()
                setattr(self, f'write_{channel}_relative_channel', self.create_write_relative_channel_func(
                    channel))
                setattr(self, f'write_{channel}_relative_delay', self.create_write_relative_delay_func(
                    channel))
            self.set_state(DevState.ON)
            logging.info(
                f'DG645 is connected.')
            self.set_status("DG645 device is connected.")
            Device.init_device(self)
            a = 1
        except:
            logging.info("Could NOT connect to  DG645")
            self.set_state(DevState.OFF)

    @command()
    def send_single_shot(self):
        self.device.write('*TRG')
        logging.info("Send a single-shot trigger")


if __name__ == "__main__":
    DG645.run_server()
