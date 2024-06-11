import win32com.client
import matplotlib.pyplot as plt
import numpy as np
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import time
import datetime
import logging
import os
import csv
import time

# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class LeCroy(Device):

    polling = 1000
    waiting = 0.1
    # is_memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    IP_address = device_property(dtype=str, default_value='')
    friendly_name = device_property(dtype=str, default_value='')
    # model = attribute(
    #     label="model",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    # )

    # def read_model(self):
    #     return self._model

    # serial_number = attribute(
    #     label="serial number",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    # )

    # def read_serial_number(self):
    #     return self._serial_number

   
    # save_data = attribute(
    #     label="save data",
    #     dtype=bool,
    #     access=AttrWriteType.READ_WRITE,
    #     memorized=is_memorized,
    #     doc='save the data'
    # )

    # def read_save_data(self):
    #     if self._save_data:
    #         if not self._save_path:
    #             self.read_save_path()
    #         if not os.path.isdir(os.path.dirname(self._save_path)):
    #             print("Not a correct file path")
    #             self._save_data = False
    #             return self._save_data
    #     return self._save_data

    # def write_save_data(self, value):
    #     if self._save_data != value:
    #         self._save_data = value

    # def save_data_to_file(self):
    #     file_exists = os.path.isfile(self._save_path)
    #     with open(self._save_path, 'a+', newline='') as csvfile:
    #         fieldnames = ['read_time', 'main_value', 'wavelength', 'display_range', 'auto_range',
    #                       'measure_mode', 'attenuator', 'multiplier', 'offset']
    #         if self._model != "PH100-Si-HA-OD1":
    #             fieldnames.append('trigger_level')
    #         else:
    #             fieldnames.append('set_zero')
    #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #         if not file_exists:
    #             writer.writeheader()
    #         row_dict = {}
    #         for key in fieldnames:
    #             row_dict[key] = getattr(self, f'_{key}')
    #         writer.writerow(row_dict)

    # save_path = attribute(
    #     label='save path (file)',
    #     dtype=str,
    #     access=AttrWriteType.READ_WRITE,
    #     memorized=is_memorized,
    #     hw_memorized=True,
    #     doc='save data path, use ";" to separate multiple paths'
    # )

    # def read_save_path(self):
    #     if len(self._save_path) > 20:
    #         return f'{self._save_path[0:10]}...{self._save_path[-10:-1]}'
    #     else:
    #         return self._save_path

    # def write_save_path(self, value):
    #     if self.create_save_folder(value):
    #         self._save_path = value

    # def create_save_folder(self, path):
    #     try:
    #         os.makedirs(os.path.dirname(path), exist_ok=True)
    #         print(f'{path} created!')
    #         return True
    #     except:
    #         print('create failed')
    #         return False

    # def create_save_file(self):
    #     date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    #     with open(os.path.join(self._save_path, date, ), "w") as my_empty_csv:
    #         print(f'{path} created!')
    #         return True

    def create_func(self, channel_number, x_or_y):
        def func(*args, **kwargs):
            try:
                setattr(self, f'_waveform_c{channel_number}', self.scope.GetScaledWaveformWithTimes(f"C{channel_number}", 1000000, 0))
                idx = 0 if x_or_y == "x" else 1
                setattr(self, f'_waveform_c{channel_number}_{x_or_y}', getattr(self, f'_waveform_c{channel_number}')[idx])
                return getattr(self, f'_waveform_c{channel_number}_{x_or_y}')    
            except:
                return []
        return func
    
    # test_attr = attribute(
    #         label="test_attr",
    #         dtype=(float,),
    #         unit='ns',
    #         max_dim_x=1000000,
    #         polling_period=polling,
    #         access=AttrWriteType.READ,
    #     )

    # def read_test_attr(self):
    #     return [1,1,1]
    
    channel_info = [[channel_number, x_y] for channel_number in [1, 2, 3, 4] for x_y in ['x', 'y']]

    def initialize_dynamic_attributes(self):
        attr_dict = dict()
        for arg1, args2 in self.channel_info:
            attr_dict[f"waveform_c{arg1}_{args2}"] = {'name':f'waveform_c{arg1}_{args2}', 'label':f"waveform c{arg1} {args2}"}
        for name, details in attr_dict.items():
            self.add_attribute(attribute(name=details['name'], label=details['label'],
            dtype=(float,),
            unit='ns',
            max_dim_x=1000000,
            polling_period=self.polling,
            access=AttrWriteType.READ))

    def init_device(self):
        # def the read attribute method here at the beginning
        for arg1, arg2 in self.channel_info:
            setattr(self, f'read_waveform_c{arg1}_{arg2}',self.create_func(arg1, arg2))
        Device.init_device(self)
        self.set_state(DevState.INIT)
        try:
            self.scope=win32com.client.Dispatch("LeCroy.ActiveDSOCtrl.1") #creates instance of the ActiveDSO control
            self.scope.MakeConnection(f"IP:{self.IP_address}") 
            # self.scope.WriteString("BUZZ BEEP", 1)
            self.set_state(DevState.ON)
            self.set_status(f"Scope {self.IP_address} is connected.")
        except:
            print(f"Could NOT connect to  Scope:{self.IP_address}")
            self.set_state(DevState.OFF)


if __name__ == "__main__":
    LeCroy.run_server()
