from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
import datetime
import logging
import os
import csv
import platform
import nidaqmx
import datetime
from common.logger_adapter import LoggerAdapter
# -----------------------------


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
        label="pressure (psi)",
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
            task.ao_channels.add_ao_voltage_chan(
                self.high_voltage_channel, min_val=self.high_voltage_channel_min, max_val=self.high_voltage_channel_max)
            task.ao_channels.add_ao_voltage_chan(
                self.low_voltage_channel, min_val=self.low_voltage_channel_min, max_val=self.low_voltage_channel_max)
            # 10 V, 1000 psi.
            if self.differential_mode == 'standard':
                if self.revert_channel:
                    out_put_array = [0, self._pressure_psi /
                                     self.voltage_to_device_output]
                else:
                    out_put_array = [self._pressure_psi /
                                     self.voltage_to_device_output, 0]
            elif self.differential_mode == 'half_half':
                if self.revert_channel:
                    out_put_array = [[-self._pressure_psi/(
                        2*self.voltage_to_device_output)], [self._pressure_psi/(2*self.voltage_to_device_output)]]
                else:
                    out_put_array = [[
                        self._pressure_psi/(2*self.voltage_to_device_output)], [-self._pressure_psi/(2*self.voltage_to_device_output)]]
            else:
                raise ValueError(
                    f"Invalid differential_mode: {self.differential_mode}. Must be 'standard' or 'half_half'.")
            task.write(out_put_array)
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

    high_voltage_channel = device_property(dtype=str, default_value='')
    high_voltage_channel_min = device_property(dtype=float, default_value=0)
    high_voltage_channel_max = device_property(dtype=float, default_value=10)
    low_voltage_channel = device_property(dtype=str, default_value='')
    low_voltage_channel_min = device_property(dtype=float, default_value=0)
    low_voltage_channel_max = device_property(dtype=float, default_value=10)
    differential_mode = device_property(dtype=str, default_value='standard')
    # 1 v will generate 100 psi.
    voltage_to_device_output = device_property(dtype=float, default_value=100)
    # high voltage channel will be set to 0V or negative when revert_voltage is true.
    revert_channel = device_property(dtype=bool, default_value=False)

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
            self.poll_attribute('pressure_psi', value)

    def init_device(self):
        self._host_computer = platform.node()
        self._user_defined_name = 'GXRegulator_init_name'
        self._pressure_psi = 0
        self._read_time = 'N/A'
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
