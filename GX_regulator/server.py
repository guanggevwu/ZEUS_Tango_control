#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
import numpy as np
import datetime
import logging
import os
import sys
from scipy.ndimage import convolve
import csv
import platform
import nidaqmx
import datetime
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.other import generate_basename
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class GXRegulator(Device):

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

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

    read_time = attribute(
        label="read time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_read_time(self):
        return self._read_time


    pressure_psi = attribute(
        label="pressure",
        dtype=float,
        unit='psi',
        format='8.2f',
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_pressure_psi(self):
        return self._pressure_psi

    def write_pressure_psi(self, value):
        self._pressure_psi = value
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(f"Dev1/ao{self.high_voltage_channel}", min_val=0, max_val=10)
            task.ao_channels.add_ao_voltage_chan(f"Dev1/ao{self.low_voltage_channel}", min_val=0, max_val=10)
            # 10 V, 1000 psi.
            task.write([self._pressure_psi/1000*10,0])
            self._read_time = datetime.datetime.now().strftime("%Y%m%d.%H:%M:%S.%f")
        if self._save_data:
            if os.path.isfile(self._save_path):
                with open(self._save_path, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([self._read_time, self._pressure_psi])
            else:
                with open(self._save_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['write_time', 'pressure(psi)'])
                    writer.writerow([self._read_time, self._pressure_psi])

    pressure_bar = attribute(
        label="pressure",
        dtype=float,
        unit='bar',
        format='8.4f',
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_pressure_bar(self):
        return self._pressure_psi*self.psi2bar

    def write_pressure_bar(self, value):
        self.write_pressure_psi(self, value/self.psi2bar)

    high_voltage_channel = device_property(dtype=str, default_value='')
    low_voltage_channel = device_property(dtype=str, default_value='')


    save_data = attribute(
        label="save data",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc='save the images on the server'
    )

    def read_save_data(self):
        return self._save_data

    def write_save_data(self, value):
        self._try_save_data = value
        if value:
            try:
                os.makedirs(os.path.dirname(self._save_path), exist_ok=True)
                self._save_data = value
            except FileNotFoundError:
                logging.info(
                    f"Folder creation failed! If you see this at server start-up. It is usually fine since {self._save_path=} is not initialized yet!")
                return
        else:
            self._save_data = value
        logging.info(f'save status is changed to {value}')


    save_path = attribute(
        label='save path (folder)',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc='Save data path on the server. Use %date to indicate today; Use ";" to separate multiple paths'
    )

    def read_save_path(self):
        if self._use_date and datetime.datetime.today().strftime("%Y%m%d") not in self._save_path:
            self.write_save_path(self.path_raw)
        return self._save_path

    def write_save_path(self, value):
        # if the entered path has %date in it, replace %date with today's date and mark a _use_date flag
        self.path_raw = value
        if '%date' in value:
            self._use_date = True
            value = value.replace(
                '%date', datetime.datetime.today().strftime("%Y%m%d"))
        else:
            self._use_date = False
        value_split = value.split(';')
        if self._save_data:
            for idx, v in enumerate(value_split):
                try:
                    os.makedirs(v, exist_ok=True)
                except OSError as inst:
                    logging.error(inst)
                    raise (f'error on save_path part {idx}')
        self._save_path = value
        self.push_change_event("save_path", self.read_save_path())


    is_debug_mode = attribute(
        label='debug',
        dtype=bool,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_is_debug_mode(self):
        return self._debug

    def write_is_debug_mode(self, value):
        self._debug = value

    polling_period = attribute(
        label='polling interval',
        dtype=int,
        unit='ms',
        hw_memorized=True,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_polling_period(self):
        return self._polling

    def write_polling_period(self, value):
        self._polling = value
        if self._is_polling_periodically:
            self.poll_attribute('pressure_bar', value)
            self.poll_attribute('pressure_psi', value)


    def init_device(self):
        self._host_computer = platform.node()
        self._user_defined_name = 'GXRegulator_init_name'
        self._pressure_psi = 0
        self.psi2bar = 0.0689476
        self.path_raw = ''
        self._debug = False
        self._save_data = False
        self._save_path = ''
        self._read_time = 'N/A'
        self._use_date = False
        self._polling = 1000
        super().init_device()
        self.get_logger = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self._user_defined_name, self.get_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        self.set_state(DevState.ON)


if __name__ == "__main__":
    GXRegulator.run_server()
