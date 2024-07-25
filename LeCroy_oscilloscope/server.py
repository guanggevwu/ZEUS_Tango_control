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
    is_memorized = True

    IP_address = device_property(dtype=str, default_value='')
    friendly_name = device_property(dtype=str, default_value='')

    def create_func(self, channel_number, x_or_y):
        def func(*args, **kwargs):
            try:
                setattr(self, f'_waveform_c{channel_number}', self.scope.GetScaledWaveformWithTimes(
                    f"C{channel_number}", 1000000, 0))
                idx = 0 if x_or_y == "x" else 1
                setattr(self, f'_waveform_c{channel_number}_{x_or_y}', getattr(
                    self, f'_waveform_c{channel_number}')[idx])
                return getattr(self, f'_waveform_c{channel_number}_{x_or_y}')
            except:
                return []
        return func

    channel_info = [[channel_number, x_y]
                    for channel_number in [1, 2, 3, 4] for x_y in ['x', 'y']]

    def initialize_dynamic_attributes(self):
        attr_dict = dict()
        for arg1, args2 in self.channel_info:
            attr_dict[f"waveform_c{arg1}_{args2}"] = {
                'name': f'waveform_c{arg1}_{args2}', 'label': f"waveform c{arg1} {args2}"}
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
            setattr(
                self, f'read_waveform_c{arg1}_{arg2}', self.create_func(arg1, arg2))
        Device.init_device(self)
        self.set_state(DevState.INIT)
        try:
            # creates instance of the ActiveDSO control
            self.scope = win32com.client.Dispatch("LeCroy.ActiveDSOCtrl.1")
            self.scope.MakeConnection(f"IP:{self.IP_address}")
            # self.scope.WriteString("BUZZ BEEP", 1)
            self.set_state(DevState.ON)
            self.set_status(f"Scope {self.IP_address} is connected.")
        except:
            print(f"Could NOT connect to  Scope:{self.IP_address}")
            self.set_state(DevState.OFF)


if __name__ == "__main__":
    LeCroy.run_server()
