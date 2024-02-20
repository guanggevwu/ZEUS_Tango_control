#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
from pypylon import pylon
from numpy import array
import numpy as np
import time
import datetime
import logging
from PIL import Image
import os
import csv

import serial
import time
import logging
import serial.tools.list_ports

# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class GentecEO(Device):

    polling = 500
    waiting = 0.1
    # is_memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    def find_com_number(self):
        all_ports = serial.tools.list_ports.comports()
        for p in all_ports:
            if p.manufacturer == 'Gentec-EO':
                return p

    # make dynamic
    energy = attribute(
        label="energy",
        dtype=str,
        access=AttrWriteType.READ,
        polling_period=polling,
        doc='energy or power'
    )

    def read_energy(self):
        self.device.write(b'*CVU')
        self._energy = self.device.readline().strip().decode()
        return self._energy

    wavelength = attribute(
        label="wavelength",
        dtype=int,
        unit='nm',
        access=AttrWriteType.READ_WRITE,
        min_value=400,
        max_value=1080,
        memorized=is_memorized,
        hw_memorized=True,
        doc='personal wavelength correction'
    )

    def read_wavelength(self):
        self.device.write(b'*GWL')
        readback = self.device.readline().strip().decode()
        if readback:
            self._wavelength = int(readback.split(' ')[-1])
        else:
            self._wavelength = 0
        return self._wavelength

    def write_wavelength(self, value):
        self.device.write(f'*PWC{value:05}'.encode())
        time.sleep(0.2)

    range_dict = {}
    res_table = [1, 3, 10, 30, 100, 300]
    # unit_table = ['p', 'n', 'u', 'm', '', 'k', 'M']
    unit_table = ['p', 'n', 'u', 'm', '', 'k', 'M']
    # 3nw to 1 w
    for idx in range(7, 25):
        u, res = divmod(idx, 6)
        range_dict[f'{idx:02}'] = [res_table[res]*1000**u/1e12,
                                   f'{res_table[res]}{unit_table[u]}']

    hide_display_range_dropdown_text_list = attribute(
        label="range",
        dtype=(str,),
        max_dim_x=100,
        max_dim_y=100,
        access=AttrWriteType.READ,
        polling_period=polling,
        doc='display_range_dropdown'
    )

    def read_hide_display_range_dropdown_text_list(self):
        return [e[1] for e in self.range_dict.values()]

    hide_display_range_dropdown_text_value = attribute(
        label="range",
        dtype=(float,),
        max_dim_x=100,
        max_dim_y=100,
        access=AttrWriteType.READ,
        polling_period=polling,
        doc='display_range_dropdown'
    )

    def read_hide_display_range_dropdown_text_value(self):
        return [e[0] for e in self.range_dict.values()]

    display_range = attribute(
        label="range",
        dtype=str,
        memorized=is_memorized,
        access=AttrWriteType.READ_WRITE,
        doc='range'
    )

    def read_display_range(self):
        self.device.write(b'*GCR')
        self._display_range = self.range_dict[self.device.readline(
        ).strip().decode().split(' ')[-1]][1]
        return self._display_range

    def write_display_range(self, value):
        for k, v in self.range_dict.items():
            if float(value) == v[0]:
                self.device.write(f'*SCS{k}'.encode())
        time.sleep(0.5)

    auto_range = attribute(
        label="auto range",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='enable or disable auto range'
    )

    def read_auto_range(self):
        self.device.write(b'*GAS')
        response = self.device.readline().strip().decode()[-1]
        if response == '1':
            self._auto_range = True
        else:
            self._auto_range = False
        return self._auto_range

    def write_auto_range(self, value):
        if value:
            self.device.write(b'*SAS1')
        else:
            self.device.write(b'*SAS0')
        time.sleep(0.5)

    measure_mode = attribute(
        label="measure mode",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        polling_period=polling,
        memorized=is_memorized,
        hw_memorized=True,
        doc='power, energy or single shot energy'
    )

    def read_measure_mode(self):
        self.device.write(b'*GMD')
        mode = self.device.readline().strip().decode().split(' ')[1]
        if mode == "0":
            self._measure_mode = 'power'
        elif mode == "1":
            self._measure_mode = 'energy'
        elif mode == "2":
            self._measure_mode = 'SSE'
        return self._measure_mode

    def write_measure_mode(self, value):
        if not hasattr(self, '_measure_mode'):
            self.read_measure_mode()
        if (self._measure_mode == '0' and value == "power") or (self._measure_mode == '2' and value == "SSE"):
            return
        else:
            self.device.write(b'*SSE')
            time.sleep(2)

    set_zero = attribute(
        label="set to 0",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='set currrent value as 0'
    )

    def read_set_zero(self):
        self.device.write(b'*GZO')
        reply = self.device.readline().strip().decode()[-1]
        self.info_stream(reply)
        if reply == '1':
            self._set_zero = True
        elif reply == '0':
            self._set_zero = False
        return self._set_zero

    def write_set_zero(self, value):
        if value:
            self.device.write(b'*SDZ')
            # while True:
            #     res = self.device.readline()
            #     if 'Done' in res.decode():
            #         break
            #     else:
            #         time.sleep(1)
        else:
            self.device.write(b'*COU')
            time.sleep(1)

    attenuator = attribute(
        label="attenuator",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='enable or disable attenuator'
    )

    def read_attenuator(self):
        self.device.write(b'*GAT')
        reply = self.device.readline().strip().decode()
        reply = reply.split(' ')[-1]
        if reply == '1':
            self._attenuator = True
        elif reply == '0':
            self._attenuator = False
        return self._attenuator

    def write_attenuator(self, value):
        if value:
            self.device.write(b'*ATT1')
        elif not value:
            self.device.write(b'*ATT0')
        time.sleep(0.5)

    multiplier = attribute(
        label="multiplier",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='apply multiplier'
    )

    def read_multiplier(self):
        self.device.write(b'*GUM')
        reply = self.device.readline().strip().decode()
        self._multiplier = int(float(reply.split(' ')[-1]))
        return self._multiplier

    def write_multiplier(self, value):
        self.device.write(f'*MUL{value:08}'.encode())
        time.sleep(0.5)

    offset = attribute(
        label="offset",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='apply offset'
    )

    def read_offset(self):
        self.device.write(b'*GUO')
        reply = self.device.readline().strip().decode()
        self._offset = float(reply.split(' ')[-1])
        return float(reply.split(' ')[-1])

    def write_offset(self, value):
        self.device.write(f'*OFF{value:08}'.encode())
        time.sleep(0.5)

    save_data = attribute(
        label="save data",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        polling_period=polling,
        doc='save the data'
    )

    def read_save_data(self):
        if self._save_data:
            if not self._save_path:
                self.read_save_path()
            file_exists = os.path.isfile(self._save_path)
            with open(self._save_path, 'a', newline='') as csvfile:
                fieldnames = ['time', 'energy', 'wavelength', 'display_range', 'auto_range',
                              'measure_mode', 'set_zero', 'attenuator', 'multiplier', 'offset']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                row_dict = {}
                for key in fieldnames:
                    if key == "time":
                        row_dict[key] = str(datetime.datetime.now())
                    else:
                        row_dict[key] = getattr(self, f'_{key}')
                writer.writerow(row_dict)
        return self._save_data

    def write_save_data(self, value):
        if self._save_data != value:
            self._save_data = value
            logging.info(f'save status is changed to {value}')

    save_path = attribute(
        label='save path',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='save data path, use ";" to seperate multiple paths'
    )

    def read_save_path(self):
        if not hasattr(self, '_save_path'):
            self._save_path = os.path.join(
                os.path.dirname(__file__), 'gentec_tmp_data')
            os.makedirs(self._save_path, exist_ok=True)
        # if len(self._save_path) > 20:
        #     return f'{self._save_path[0:10]}...{self._save_path[-10:-1]}'
        # else:
        return self._save_path

    def write_save_path(self, value):
        self._save_path = value
        self._save_folder = os.path.dirname(self._save_path)
        os.makedirs(self._save_folder, exist_ok=True)

    serial_number = attribute(
        label="serial number",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_serial_number(self):
        return self.find_com_number().serial_number

    # def initialize_dynamic_attributes(self):
    #     '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open'''
    #     exposure = attribute(
    #         name="exposure",
    #         label="exposure",
    #         dtype=float,
    #         access=AttrWriteType.READ_WRITE,
    #         memorized=self.is_memorized,

    #         polling_period=self.polling,
    #         unit="us",
    #         min_value=self.camera.ExposureTimeAbs.Min,
    #         max_value=self.camera.ExposureTimeAbs.Max
    #     )
    #     self.add_attribute(exposure)
    #     # if self.camera.DeviceModelName() in ['acA640-121gm']:
    #     self.remove_attribute('sensor_readout_mode')

    # def read_exposure(self, attr):
    #     return self.camera.ExposureTimeAbs.Value

    # def write_exposure(self, attr):
    #     self.camera.ExposureTimeAbs.Value = attr.get_write_value()

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.INIT)
        com_obj = self.find_com_number()
        if com_obj is not None:
            com_number = com_obj.device
        try:
            self.device = serial.Serial(
                port=com_number, baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            print(
                f'Genotec-eo device is connected: {com_obj.serial_number}')
            self.set_state(DevState.ON)
            self._save_data = False
        except:
            print("Could NOT connect to  Genotec-eo")
            self.set_state(DevState.OFF)


if __name__ == "__main__":
    GentecEO.run_server()
