# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import logging
import platform
import py_thorlabs_tsp
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class TSP01B(Device):
    serial_number = device_property(dtype=str, default_value='')

    def init_device(self):
        super().init_device()  # this loads the device properties
        self.get_logger = logging.getLogger(self.__class__.__name__)
        if not hasattr(self, '_user_defined_name'):
            self._user_defined_name = self.__class__.__name__
        self.logger = LoggerAdapter(self._user_defined_name, self.get_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        try:
            self.dev = py_thorlabs_tsp.ThorlabsTsp01B(self.serial_number)
            self._host_computer = platform.node()
            self.set_status("TSP01B device is connected.")
            self.set_state(DevState.ON)
        except Exception as e:
            self.set_status(f"Failed to connect to TSP01B device: {e}")
            self.set_state(DevState.FAULT)

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

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    temperature = attribute(
        label="temperature",
        unit='°C',
        dtype=float,
        polling_period=1000,
        access=AttrWriteType.READ,
        format='6.3f',
        doc="Returns temperature in Celsius"
    )

    def read_temperature(self):
        self._temperature = self.dev.measure_temperature('th0')
        return self._temperature

    humidity = attribute(
        label="humidity",
        dtype=float,
        access=AttrWriteType.READ,
        polling_period=1000,
        format='6.3f',
        doc="Returns humidity in %RH"
    )

    def read_humidity(self):
        self._humidity = self.dev.measure_humidity()
        return self._humidity


if __name__ == "__main__":
    TSP01B.run_server()
