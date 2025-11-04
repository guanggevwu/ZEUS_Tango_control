#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import datetime
import logging
import os
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class Clock(Device):
    def init_device(self):
        super().init_device()  # this loads the device properties
        self.get_logger = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self.__class__.__name__, self.get_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        self.set_status("Clock device is connected.")
        self.set_state(DevState.ON)

    time = attribute(
        label="time",
        dtype=str,
        access=AttrWriteType.READ,
        polling_period=100,
    )

    def read_time(self):
        self._time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')
        return self._time

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer


if __name__ == "__main__":
    Clock.run_server()
