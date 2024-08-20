#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
from pypylon import pylon
import numpy as np
import time
import datetime
import logging
from PIL import Image
import os
import sys
# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class FileReader(Device):
    polling = 200

    is_polling_periodically = attribute(
        label="polling periodically",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc='polling the image periodically or by external acquisition code'
    )

    def read_is_polling_periodically(self):
        return self._is_polling_periodically

    def write_is_polling_periodically(self, value):
        if value:
            self.enable_polling('is_new_image')
        else:
            self.disable_polling('is_new_image')
        self._is_polling_periodically = value

    polling_period = attribute(
        label='image polling',
        dtype=int,
        unit='ms',
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_polling_period(self):
        self._polling_period = self.get_attribute_poll_period('is_new_image')
        return self._polling_period

    def write_polling_period(self, value):
        if value > 5:
            self.poll_attribute('is_new_image', value)
            self._polling_period = value

    folder_path = attribute(
        label="folder",
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )

    def read_folder_path(self):
        return self._folder_path

    def write_folder_path(self, value):
        if os.path.isdir(value):
            self._folder_path = value
            self.read_file_list()
            self.previous_list = list(self._file_list)
            logging.info(
                f"{len(self._file_list)} {self._file_extension} files are found in the {self._folder_path}")

    file_extension = attribute(
        label="file extension",
        dtype="str",
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_file_extension(self):
        return self._file_extension

    def write_file_extension(self, value):
        self._file_extension = value

    file_list = attribute(
        label="file list",
        dtype=(str,),
        access=AttrWriteType.READ,
    )

    def read_file_list(self):
        file_folder = os.listdir(self._folder_path)
        self._file_list = [i for i in file_folder if i.split(".")[-1] == self._file_extension and os.path.isfile(
            os.path.join(self._folder_path, i))]
        self.debug_stream("debugging")
        return self._file_list

    current_file = attribute(
        label="current file",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_current_file(self):
        return self._current_file

    modification_time = attribute(
        label="created time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_modification_time(self):
        return self._modification_time

    image = attribute(
        label="image",
        max_dim_x=4096,
        max_dim_y=4096,
        dtype=((int,),),
        access=AttrWriteType.READ,
    )

    def read_image(self):
        return self._image

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    def read_is_new_image(self):
        new_files = [i for i in self.read_file_list()
                     if i not in self.previous_list]
        if new_files != []:
            new_files = sorted(new_files, key=lambda x: os.path.getmtime(
                os.path.join(self._folder_path, x)))
            self.previous_list = self.previous_list + [new_files[0]]
            logging.info(f"Detected a new file {new_files[0]}.")
            self._current_file = new_files[0]
            self._image = np.array(Image.open(
                os.path.join(self._folder_path, self._current_file)))
            self._modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(
                os.path.join(self._folder_path, self._current_file))).strftime("%m/%d %H:%M:%S:%f")
            self.push_change_event("image", self.read_image())
            self.push_change_event("current_file", self.read_current_file())
            self.push_change_event("modification_time",
                                   self.read_modification_time())
            return True
        else:
            return False

    is_debug = attribute(
        label='debug',
        dtype=bool,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_is_debug(self):
        return self._debug

    def write_is_debug(self, value):
        self._debug = value
    # serial_number = device_property(dtype=str, default_value='')
    # friendly_name = device_property(dtype=str, default_value='')

    def init_device(self):
        self._debug = False
        self._is_polling_periodically = False
        self._folder_path = ''
        self._file_extension = 'tiff'
        self._current_file = ''
        self._modification_time = 'N/A'
        self._image = np.zeros([1000, 1000])
        # self._polling_period = self.get_attribute_poll_period('is_new_image')
        # if self._polling_period == 0:
        #     self._polling_period = 200
        print(
            f'FileReader is started.')
        self.set_state(DevState.ON)

    def disable_polling(self, attr):
        if self.is_attribute_polled(attr):
            self.stop_poll_attribute(attr)
            logging.info(f'polling for {attr} is disabled')

    def enable_polling(self, attr):
        if not self.is_attribute_polled(attr):
            self.poll_attribute(attr, self._polling_period)
            logging.info(
                f'polling period of {attr} is set to {self._polling_period}')


if __name__ == "__main__":
    FileReader.run_server()
