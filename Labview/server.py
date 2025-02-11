#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import datetime
import logging
from threading import Thread

import socket
import time
import serial.tools.list_ports
import numpy as np
import platform
# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class LabviewPrograme(Device):

    port = device_property(dtype=str, default_value='61557')
    # timeout = device_property(dtype=float, default_value='1.0')

    def init_device(self):
        '''
        save_data is initialized before save_path during the initialization caused by hw_memorized. self.write_save_data(True) will not set self._save to True because self._save_path is an empty string at that moment. Introducing self._try_save_data will save the intended status and can be used later in write_save_path function.
        '''
        Device.init_device(self)
        self.set_state(DevState.INIT)
        try:
            self._host_computer = platform.node()
            addr_info = socket.getaddrinfo(self._host_computer, None)
            addr_info_value = [i[4][0] for i in addr_info]
            self.ip = [i for i in addr_info_value if '192.168.131' in i][0]
            self.server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.bind((self.ip, int(self.port)))
            # self.server_socket.settimeout(self.timeout)
            Thread(target=self.receive_data).start()
            self._host_computer = platform.node()
            self._user_defined_name = 'labview'
            self._shot_id = "0"
            self._read_time = 'N/A'
            self.set_status("Labview device is connected.")
            self.set_state(DevState.ON)
        except:
            print("Could NOT connect to  Labview")
            self.set_state(DevState.OFF)

    def receive_data(self):
        while True:
            try:
                message, client_address = self.server_socket.recvfrom(1024)
                # print(f"Received message: {message.decode()} from {client_address}")

                message_decoded = message.decode()
                print(f'{datetime.datetime.now()} {message_decoded}')

                if message_decoded != "SN done":
                    index = message_decoded.find('SN ')+3
                    message_decoded = message_decoded[index:]
                    self._shot_id = message_decoded
                    self._read_time = datetime.datetime.now().strftime("%H:%M:%S")
                    self.push_change_event("shot_id", self.read_shot_id())
                    self.push_change_event("read_time", self.read_read_time())
            except socket.timeout:
                tim = datetime.datetime.now()
                print("No data received, timeout occurred. Time at:" + str(tim))
            except Exception as e:
                # Handle the exception
                print("An error occurred:", e)

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

    read_time = attribute(
        label="read time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_read_time(self):
        return self._read_time

    shot_id = attribute(
        label="shot id",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_shot_id(self):
        return self._shot_id


if __name__ == "__main__":
    LabviewPrograme.run_server()
