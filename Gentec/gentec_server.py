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

    friendly_name = device_property(dtype=str, default_value='')

    def find_com_number(self):
        all_ports = serial.tools.list_ports.comports()
        for p in all_ports:
            if p.manufacturer == 'Gentec-EO':
                return p

    model = attribute(
        label="model",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_model(self):
        return self._model

    serial_number = attribute(
        label="serial number",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_serial_number(self):
        return self._serial_number

    name_attr = attribute(
        label="name",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_name_attr(self):
        return self.friendly_name

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
        self._wavelength = value

    auto_range = attribute(
        label="auto range",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
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
        self._auto_range = value

    measure_mode = attribute(
        label="measure mode",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        polling_period=polling,
        memorized=is_memorized,
        doc='power, energy or single shot energy'
    )

    def read_measure_mode(self):
        self.device.write(b'*GMD')
        self._measure_mode = self.device.readline().strip().decode().split(' ')[
            1]
        return self._measure_mode

    def write_measure_mode(self, value):
        if not hasattr(self, '_measure_mode'):
            self.read_measure_mode()
            if self._measure_mode != value:
                if value == "2":
                    self.device.write(b'*SSE1')
                else:
                    self.device.write(b'*SSE0')
                time.sleep(2)
        self._measure_mode = value

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
        self._attenuator = value

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
        self._multiplier = value

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
        self._offset = value

    save_data = attribute(
        label="save data",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='save the data'
    )

    def read_save_data(self):
        if self._save_data:
            if not self._save_path:
                self.read_save_path()
            if not os.path.isdir(os.path.dirname(self._save_path)):
                self._save_data = False
                return self._save_data
            file_exists = os.path.isfile(self._save_path)
            with open(self._save_path, 'a', newline='') as csvfile:
                fieldnames = ['time', 'main_value', 'wavelength', 'display_range', 'auto_range',
                              'measure_mode', 'attenuator', 'multiplier', 'offset']
                if self._model != "PH100-Si-HA-OD1":
                    fieldnames.append('trigger_level')
                else:
                    fieldnames.append('set_zero')
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                if self._model == "PH100-Si-HA-OD1" or self._new:
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
            try:
                os.makedirs(self._save_path, exist_ok=True)
            except:
                pass
        if len(self._save_path) > 20:
            return f'{self._save_path[0:10]}...{self._save_path[-10:-1]}'
        else:
            return self._save_path

    def write_save_path(self, value):
        self._save_path = value
        self._save_folder = os.path.dirname(self._save_path)
        os.makedirs(self._save_folder, exist_ok=True)

    def initialize_dynamic_attributes(self):
        #     '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open'''
        if self._model == "PH100-Si-HA-OD1":
            self.main_value_unit = 'w'
            # 3nw to 1 w
            self.display_range_steps = range(8, 25)
        else:
            self.main_value_unit = 'J'
            # 30mj to 300j
            self.display_range_steps = range(21, 30)

        self.range_dict = {}
        res_table = [1, 3, 10, 30, 100, 300]
        unit_table = ['p', 'n', 'u', 'm', '', 'k', 'M']
        unit_table = [u + self.main_value_unit for u in unit_table]
        for idx in self.display_range_steps:
            u, res = divmod(idx, 6)
            self.range_dict[f'{idx:02}'] = [res_table[res]*1000**u/1e12,
                                            f'{res_table[res]} {unit_table[u]}']

        hide_display_range_dropdown_text_list = attribute(
            name="hide_display_range_dropdown_text_list",
            label="hide_display_range_dropdown_text_list",
            dtype=(str,),
            max_dim_x=100,
            access=AttrWriteType.READ,
            doc='display_range_dropdown'
        )

        hide_display_range_dropdown_text_value = attribute(
            name="hide_display_range_dropdown_text_value",
            label="hide_display_range_dropdown_text_value",
            dtype=(float,),
            max_dim_x=100,
            access=AttrWriteType.READ,
            doc='display_range_dropdown'
        )

        main_value = attribute(
            name="main_value",
            label="reading",
            dtype=str,
            access=AttrWriteType.READ,
            polling_period=self.polling,
            doc='reading value (energy or power)'
        )

        trigger_level = attribute(
            name='trigger_level',
            label='trigger level',
            dtype=str,
            access=AttrWriteType.READ_WRITE,
            doc='Set trigger level. Is the base value equal'
        )

        set_zero = attribute(
            name="set_zero",
            label="set to 0",
            dtype=bool,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,
            doc='Set currrent value as 0. Better not to use this since it takes 10 secs to do the subtraction and may cause error. Why not use offset?'
        )

        self.add_attribute(main_value)
        self.add_attribute(hide_display_range_dropdown_text_list)
        self.add_attribute(hide_display_range_dropdown_text_value)
        # self.add_attribute(display_range)
        if self._model != "PH100-Si-HA-OD1":
            self.add_attribute(trigger_level)
        else:
            self.add_attribute(set_zero)

    def read_main_value(self, attr):
        if self._model != "PH100-Si-HA-OD1":
            self.device.write(b'*NVU')
            reply = self.device.readline().strip().decode()
            if 'not' not in reply:
                self._new = True
            else:
                self._new = False
        # New data available or New data not available
        self.device.write(b'*CVU')
        self._main_value = self.device.readline().strip().decode()
        if float(self._main_value) < 1 and float(self._main_value) >= 1e-3:
            self._main_value = f'{float(self._main_value)*1e3:#.7g} m{self.main_value_unit}'
        elif float(self._main_value) < 1e-3 and float(self._main_value) >= 1e-6:
            self._main_value = f'{float(self._main_value)*1e6:#.7g} u{self.main_value_unit}'
        elif float(self._main_value) < 1e-6 and float(self._main_value) >= 1e-9:
            self._main_value = f'{float(self._main_value)*1e9:#.7g} n{self.main_value_unit}'
        elif float(self._main_value) < 1e-9 and float(self._main_value) >= 1e-12:
            self._main_value = f'{float(self._main_value)*1e12:#.7g} p{self.main_value_unit}'
        elif float(self._main_value) < 0:
            self._main_value = f'{self._main_value} (negative value, try set scale down)'
        return self._main_value

    def read_hide_display_range_dropdown_text_list(self, attr):
        return [e[1] for e in self.range_dict.values()]

    def read_hide_display_range_dropdown_text_value(self, attr):
        return [e[0] for e in self.range_dict.values()]

    display_range = attribute(
        label="range",
        dtype=str,
        polling_period=polling,
        memorized=is_memorized,
        access=AttrWriteType.READ_WRITE,
        doc='range'
    )

    def read_display_range(self):
        self.device.write(b'*GCR')
        response = self.device.readline(
        ).strip().decode().split(' ')[-1]
        self._display_range = self.range_dict[f'{int(response):02}'][1]
        return self._display_range

    def write_display_range(self, attr):
        for k, v in self.range_dict.items():
            if float(attr) == v[0]:
                self.device.write(f'*SCS{k}'.encode())
        time.sleep(0.5)
        self._display_range = attr

    def read_trigger_level(self, attr):
        self.device.write(b'*GTL')
        response = self.device.readline(
        ).strip().decode().split(' ')[-1]
        self._trigger_level = response
        return response

    def write_trigger_level(self, attr):
        value = float(attr.get_write_value())
        self.device.write(f'*STL{value:04.1f}'.encode())
        time.sleep(0.5)
        self._trigger_level = value

    def read_set_zero(self, attr):
        self.device.write(b'*GZO')
        reply = self.device.readline().strip().decode()[-1]
        if reply == '1':
            self._set_zero = True
        elif reply == '0':
            self._set_zero = False
        return self._set_zero

    def write_set_zero(self, attr):
        value = attr.get_write_value()
        if not hasattr(self, '_set_zero'):
            self.read_set_zero()
        if not self._set_zero and value:
            # self.device.write(b'*SOU')
            # SDZ for photdiodo
            self.device.write(b'*SDZ')
            # comment out because it takes too long to get a valid readback and will cause a timeout problem.
            # readback = self.device.readlines().strip().decode()
            # print(readback)
        elif self._set_zero and not value:
            # self.device.write(b'*COU')
            self.device.write(b'*COU')
        self._set_zero = value

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.INIT)
        com_obj = self.find_com_number()
        if com_obj is not None:
            com_number = com_obj.device
        try:
            self.device = serial.Serial(
                port=com_number, baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self._save_data = False
            self.device.write(b'*STS')
            res = self.device.readlines()
            res_decode = [e.strip().decode() for e in res]
            decoded = ''
            for i in res_decode:
                decoded = decoded+chr(int(i[-2:], 16))
                decoded = decoded+chr(int(i[-4:-2], 16))
            self._serial_number = decoded[42*2:45*2]
            self._model = decoded[26*2:35*2]
            self._model = self._model.replace('\x00', '')
            print(
                f'Genotec-eo device is connected. Model: {self._model}. Serial number: {self._serial_number}')
        except:
            print("Could NOT connect to  Genotec-eo")
            self.set_state(DevState.OFF)


if __name__ == "__main__":
    GentecEO.run_server()
