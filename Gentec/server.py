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


class GentecEO(Device):
    # memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    friendly_name = device_property(dtype=str, default_value='')

    def find_com_number(self):
        all_ports = serial.tools.list_ports.comports()
        filtered_ports = [
            p for p in all_ports if p.manufacturer == 'Gentec-EO']
        if len(filtered_ports) == 1:
            return filtered_ports[0]
        elif self.friendly_name == "QE12":
            filtered_ports = [
                p for p in filtered_ports if p.serial_number == '23869B4602001200']
        elif self.friendly_name == "QE195":
            filtered_ports = [
                p for p in filtered_ports if p.serial_number == '27869B461E002000']
        return filtered_ports[0]

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

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

    read_time = attribute(
        label="read time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_read_time(self):
        return self._read_time

    main_value = attribute(
        name="main_value",
        label="reading",
        dtype=str,
        access=AttrWriteType.READ,
        polling_period=200,
        doc='reading value (energy or power)'
    )

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
        self._auto_range = value

    measure_mode = attribute(
        label="measure mode",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
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
        hw_memorized=True,
        doc='save the data'
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
            self.get_existing_rows()
        else:
            self._save_data = value
        logging.info(f'save status is changed to {value}')

    def get_existing_rows(self):
        with open(self._save_path, 'a+') as csvfile:
            csvfile.seek(0)
            self.should_write_header = False
            reader = csv.reader(csvfile)
            idx = -1
            for idx, row in enumerate(reader):
                pass
            if idx > 0:
                self._shot = int(row[0]) + 1
            if idx == -1:
                self.should_write_header = True
                self._shot = 1

    def save_data_to_file(self):
        self.get_existing_rows()
        with open(self._save_path, 'a+', newline='') as csvfile:
            fieldnames = ['shot', 'read_time', 'main_value', 'base_unit', 'wavelength', 'display_range', 'auto_range',
                          'measure_mode', 'attenuator', 'multiplier', 'offset']
            if self._model != "PH100-Si-HA-OD1":
                fieldnames.append('trigger_level')
            else:
                fieldnames.append('set_zero')
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if self.should_write_header:
                writer.writeheader()
            # if not csvfile.tell():
            #     writer.writeheader()
            row_dict = {}
            self.read_display_range()
            for key in fieldnames:
                row_dict[key] = getattr(self, f'_{key}')
            writer.writerow(row_dict)
            # add 1 shot after saving
            self._shot += 1

    shot = attribute(
        label="shot # (saved)",
        dtype=int,
        access=AttrWriteType.READ,
        doc='shot number'
    )

    def read_shot(self):
        return self._shot-1

    statistics_shots = attribute(
        label="shot # (statistics)",
        dtype=int,
        access=AttrWriteType.READ,
        doc='shot number'
    )

    def read_statistics_shots(self):
        return self._statistics_shots

    average = attribute(
        label="average",
        dtype=str,
        access=AttrWriteType.READ,
        doc='average since starting statistics'
    )

    def read_average(self):
        value, unit = self.format_unit(self._average, self._base_unit)
        return f'{value:.4f} {unit}'

    rsd = attribute(
        label="rsd",
        dtype=str,
        access=AttrWriteType.READ,
        doc='relative standard deviation since starting statistics'
    )

    def read_rsd(self):
        return f'{self._rsd*100:.4f}%'

    max = attribute(
        label="max",
        dtype=str,
        access=AttrWriteType.READ,
        doc='standard deviation since starting statistics'
    )

    def read_max(self):
        value, unit = self.format_unit(self._max, self._base_unit)
        return f'{value:.4f} {unit}'

    min = attribute(
        label="min",
        dtype=str,
        access=AttrWriteType.READ,
        doc='standard deviation since starting statistics'
    )

    def read_min(self):
        value, unit = self.format_unit(self._min, self._base_unit)
        return f'{value:.4f} {unit}'

    save_path = attribute(
        label='save path (file)',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
    )

    def read_save_path(self):
        if self._use_date and datetime.datetime.today().strftime("%Y%m%d") not in self._save_path:
            self.write_save_path(self.path_raw)
        return self._save_path

    # I assume "write_save_data" is done before "write_save_path" when hw_memorized is True.
    def write_save_path(self, value):
        # if the entered path has %date in it, replace %date with today's date and mark a _use_date flag
        self.path_raw = value
        if '%date' in value:
            self._use_date = True
            value = value.replace(
                '%date', datetime.datetime.today().strftime("%Y%m%d"))
        else:
            self._use_date = False
        self._save_path = value
        self.write_save_data(self._try_save_data)
        self.push_change_event("save_path", self.read_save_path())

    start_statistics = attribute(
        label="start statistics",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='Start to collect statistics. It will reset the historical data and start to collect new data. If it is set to False, the historical data will be cleared.'
    )

    def read_start_statistics(self):
        return self._start_statistics

    def write_start_statistics(self, value):
        if self._start_statistics and not value:
            self._historical_data = [['pulse #', 'time', 'value']]
            self._historical_data_number = []
        self._start_statistics = value

    historical_data = attribute(
        label="Historical data",
        dtype=((str,),),
        max_dim_x=100,
        max_dim_y=10000,
        access=AttrWriteType.READ,
    )

    def read_historical_data(self):
        return self._historical_data

    historical_data_number = attribute(
        label="Historical data plot",
        dtype=(float,),
        max_dim_x=10000,
        access=AttrWriteType.READ,
    )

    def read_historical_data_number(self):
        return self._historical_data_number

    def initialize_dynamic_attributes(self):
        #     '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open'''
        if self._model == "PH100-Si-HA-OD1":
            self._base_unit = 'W'
        else:
            self._base_unit = 'J'

        self.range_dict = {}
        res_table = [1, 3, 10, 30, 100, 300]
        unit_table = ['p', 'n', 'u', 'm', '', 'k', 'M']
        unit_table = [u + self._base_unit for u in unit_table]
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

        main_value_float = attribute(
            name="main_value_float",
            label="reading float",
            dtype=float,
            format='.12e',
            unit=self._base_unit,
            access=AttrWriteType.READ,
            doc='reading in float format'
        )

        trigger_level = attribute(
            name='trigger_level',
            label='trigger level',
            dtype=str,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
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

        self.add_attribute(main_value_float)
        self.add_attribute(hide_display_range_dropdown_text_list)
        self.add_attribute(hide_display_range_dropdown_text_value)
        # self.add_attribute(display_range)
        if self._model != "PH100-Si-HA-OD1":
            self.add_attribute(trigger_level)
        else:
            self.add_attribute(set_zero)

    def do_things_if_new(self):
        self._new = True
        self._read_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")
        if self._debug:
            print(
                f'New data is acquired. {self._main_value_adjust} {self._main_value_adjust_unit} at {self._read_time}')
        if self._save_data:
            self.save_data_to_file()
            self.push_change_event("shot", self.read_shot())
        if self._start_statistics:
            self._statistics_shots = len(self._historical_data)-1
            self._historical_data.append(
                [str(self._statistics_shots), self._read_time, f'{self._main_value_adjust} {self._main_value_adjust_unit}'])
            self._historical_data_number.append(
                self._main_value)
            self._average = np.mean(self._historical_data_number)
            self._rsd = np.std(self._historical_data_number)/self._average
            self._max = np.max(self._historical_data_number)
            self._min = np.min(self._historical_data_number)
    # self.get_attribute_config('main_value')[
    #     0].unit = self._main_value_adjust_unit
            self.push_change_event(
                "statistics_shots", self.read_statistics_shots())
            self.push_change_event("average", self.read_average())
            self.push_change_event("rsd", self.read_rsd())
            self.push_change_event("max", self.read_max())
            self.push_change_event("min", self.read_min())
            self.push_change_event(
                "historical_data_number", self.read_historical_data_number())
            self.push_change_event(
                "historical_data", self.read_historical_data())

    def read_main_value(self):
        # check if it is new data. The sequence is important. Must check if this is new first then read. If read first, then it is always old.
        if self._model != "PH100-Si-HA-OD1":
            self.device.write(b'*NVU')
            reply = self.device.readline().strip().decode()
            # no new data message is "New Data Not Available"
            if 'not' not in reply.lower():
                self._new = True
            else:
                self._new = False
        else:
            self._new = True

        self.device.write(b'*CVU')
        self._main_value = self.device.readline().strip().decode()
        self._main_value = float(self._main_value)
        self._main_value_adjust, self._main_value_adjust_unit = self.format_unit(
            self._main_value, self._base_unit)
        self.push_change_event(
            "main_value_float", self.read_main_value_float('placeholder'))
        if self._new:
            self.do_things_if_new()
        return f'{self._main_value_adjust:.4f} {self._main_value_adjust_unit}'

    def read_main_value_float(self, attr):
        return self._main_value

    def format_unit(self, value, _base_unit):
        magnitude_ranges = [[float("-inf"), 0], [0, 1e-12], [1e-12, 1e-9],
                            [1e-9, 1e-6], [1e-6, 1e-3], [1e-3, 1], [1, float("inf")]]
        unit_prefix = ['', '', 'p', 'n', 'u', 'm', '']
        scale_list = [1, 1, 1e12, 1e9, 1e6, 1e3, 1]
        for idx, m in enumerate(magnitude_ranges):
            if value >= m[0] and value <= m[1]:
                unit = unit_prefix[idx] + _base_unit
                value = scale_list[idx] * value
                break
        # if float(value) < 1000 and float(value) >= 1:
        #     value = f'{float(value):#.7g} {_base_unit}'
        # elif float(value) < 1 and float(value) >= 1e-3:
        #     value = f'{float(value)*1e3:#.7g} m{_base_unit}'
        # elif float(value) < 1e-3 and float(value) >= 1e-6:
        #     value = f'{float(value)*1e6:#.7g} u{_base_unit}'
        # elif float(value) < 1e-6 and float(value) >= 1e-9:
        #     value = f'{float(value)*1e9:#.7g} n{_base_unit}'
        # elif float(value) < 1e-9 and float(value) >= 1e-12:
        #     value = f'{float(value)*1e12:#.7g} p{_base_unit}'
        # elif float(value) < 1e-12:
        #     value = f'{value}'
        # elif float(value) < 0:
        #     value = f'{value} (negative value, try setting scale down)'
        return value, unit

    def read_hide_display_range_dropdown_text_list(self, attr):
        return [e[1] for e in self.range_dict.values()]

    def read_hide_display_range_dropdown_text_value(self, attr):
        return [e[0] for e in self.range_dict.values()]

    display_range = attribute(
        label="range",
        dtype=str,
        polling_period=500,
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
        time.sleep(0.2)
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
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        self._host_computer = platform.node()
        self._debug = 0
        self._historical_data = [['pulse #', 'time', 'value']]
        self._historical_data_number = []
        self._start_statistics = False
        self._use_date = False
        self._save_data = False
        self._try_save_data = False
        self._save_path = ''
        # shot is next shot number which will be saved to text file. read_shot returns self._shot -1
        self._shot = 1
        self._statistics_shots = 0
        self._average = 0
        self._rsd = 0
        self._max = 0
        self._min = 0
        super().init_device()
        self.set_state(DevState.INIT)
        com_obj = self.find_com_number()
        if com_obj is not None:
            com_number = com_obj.device
        try:
            self.device = serial.Serial(
                port=com_number, baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
            self.set_state(DevState.ON)
            self._read_time = "N/A"
            self.device.write(b'*STS')
            res = self.device.readlines()
            res_decode = [e.strip().decode() for e in res]
            decoded = ''
            for i in res_decode:
                decoded = decoded+chr(int(i[-2:], 16))
                decoded = decoded+chr(int(i[-4:-2], 16))
            self._serial_number = decoded[42*2:45*2]
            self._model = decoded[26*2:42*2]
            self.display_range_steps = range(
                int(res_decode[10][-2:], 16), int(res_decode[8][-2:], 16))
            self._model = self._model.replace(
                '\x00', '').replace(chr(int('CC', 16)), '')
            if self._model == "PH100-Si-HA-OD1":
                self._new = True
                self.read_set_zero('any')
            else:
                self._new = False
                self.read_trigger_level('any')
            self.read_auto_range()
            self.read_offset()
            self.read_wavelength()
            self.read_measure_mode()
            self.read_attenuator()
            self.read_multiplier()
            print(
                f'Genotec-eo device is connected. Model: {self._model}. Serial number: {self._serial_number}')
            self.set_state(DevState.ON)
            self.set_status("Gentec device is connected.")
        except:
            print("Could NOT connect to  Genotec-eo")
            self.set_state(DevState.OFF)


if __name__ == "__main__":
    GentecEO.run_server()
