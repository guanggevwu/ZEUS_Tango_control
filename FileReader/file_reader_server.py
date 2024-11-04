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
import csv
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from Basler.server import Basler, LoggerAdapter
# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class FileReader(Device):

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
        self.logger = LoggerAdapter(value, self.logger_base)

    data_dimension = attribute(
        label='data dimension',
        dtype=int,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_data_dimension(self):
        return self._data_dimension

    def write_data_dimension(self, value):
        self._data_dimension = value
        return self._data_dimension

    data_structure = attribute(
        label='data structure',
        dtype=int,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='0 for VISSpec csv file.'
    )

    def read_data_structure(self):
        return self._data_structure

    def write_data_structure(self, value):
        self._data_structure = value

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
            self.previous_list = self._file_list
            self._file_number = len(self._file_list)
            logging.info(
                f"{self._file_number} {self._file_extension} files are found in the {self._folder_path}")

    file_list = attribute(
        label="file list",
        dtype=(str,),
        max_dim_x=10000,
        access=AttrWriteType.READ,
    )

    def read_file_list(self):
        file_folder = os.listdir(self._folder_path)
        self._file_list = [i for i in file_folder if i.split(".")[-1] == self._file_extension and os.path.isfile(
            os.path.join(self._folder_path, i))]
        return self._file_list

    current_file = attribute(
        label="current file",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_current_file(self):
        return self._current_file

    file_number = attribute(
        label='file #',
        dtype=int,
        access=AttrWriteType.READ,
        doc="file number"
    )

    def read_file_number(self):
        return self._file_number

    read_time = attribute(
        label="modification time",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_read_time(self):
        return self._read_time

    image = attribute(
        label="image",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((int,),),
        access=AttrWriteType.READ,
    )

    def read_image(self):
        return self._image

    x = attribute(
        label="data list",
        max_dim_x=1000000,
        dtype=(float,),
        access=AttrWriteType.READ,
    )

    def read_x(self):
        return self._x

    y = attribute(
        label="data list",
        max_dim_x=1000000,
        dtype=(float,),
        access=AttrWriteType.READ,
    )

    def read_y(self):
        return self._y

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    def read_is_new_image(self):
        # logging.info(f'{len(self.previous_list)=}')
        # logging.info(f'{len(self.read_file_list())=}')
        new_files = [i for i in self.read_file_list()
                     if i not in self.previous_list]
        if new_files != []:
            new_files = sorted(new_files, key=lambda x: os.path.getmtime(
                os.path.join(self._folder_path, x)))
            self.previous_list = self.previous_list + [new_files[0]]
            logging.info(f"Detected a new file {new_files[0]}.")
            self._current_file = new_files[0]
            if self._data_dimension == 2:
                image_PIL = Image.open(
                    os.path.join(self._folder_path, self._current_file))
                self._image = np.array(image_PIL)
                self._format_pixel = str(self.mode_to_bpp[image_PIL.mode])
                self.push_change_event("image", self.read_image())
            elif self._data_structure == 0:
                with open(os.path.join(self._folder_path, self._current_file), newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    self._x, self._y = [], []
                    start = False
                    stop = False
                    for row in reader:
                        if row[0] == '[EndOfFile]':
                            stop = True
                        if start and not stop:
                            self._x.append(float(row[0].split(';')[0]))
                            self._y.append(float(row[0].split(';')[-1]))
                        if row[0] == '[Data]':
                            start = True
            self._read_time = datetime.datetime.fromtimestamp(os.path.getmtime(
                os.path.join(self._folder_path, self._current_file))).strftime("%H-%M-%S.%f")
            self._file_number += 1
            self.push_change_event("current_file", self.read_current_file())
            self.push_change_event("read_time",
                                   self.read_read_time())
            self.push_change_event("file_number",
                                   self.read_file_number())

            return True
        else:
            return False

    format_pixel = attribute(
        label="pixel format",
        dtype=str,
        access=AttrWriteType.READ,
    )

    def read_format_pixel(self):
        return self._format_pixel

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

    def init_device(self):
        self._user_defined_name = ''
        self.logger_base = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self._user_defined_name, self.logger_base)
        self._data_dimension = 2
        self._data_structure = 0
        self._debug = False
        self._is_polling_periodically = False
        self._polling_period = 199
        self._folder_path = ''
        self._file_extension = 'tiff'
        self._current_file = ''
        self._read_time = 'N/A'
        self._image = np.zeros([1000, 1000])
        self._x, self._y = [], []
        self._file_number = 0
        self._format_pixel = 'unknown'
        self.mode_to_bpp = {"1": 1, "L": 8, "P": 8, "RGB": 24, "RGBA": 32, "CMYK": 32, "YCbCr": 24, "LAB": 24, "HSV": 24, "I": 32, "F": 32, "I;16": 16,
                            "I;16B": 16, "I;16L": 16, "I;16S": 16, "I;16BS": 16, "I;16LS": 16, "I;32": 32, "I;32B": 32, "I;32L": 32, "I;32S": 32, "I;32BS": 32, "I;32LS": 32}
        # self._polling_period = self.get_attribute_poll_period('is_new_image')
        # if self._polling_period == 0:
        #     self._polling_period = 200
        logging.info(
            f'FileReader is started.')
        self.set_state(DevState.ON)

    def disable_polling(self, attr):
        if self.is_attribute_polled(attr):
            self.stop_poll_attribute(attr)
            logging.info(f'polling for {attr} is disabled')

    def enable_polling(self, attr):
        if not self.is_attribute_polled(attr):
            if not self._polling_period:
                self._polling_period = 200
            self.poll_attribute(attr, self._polling_period)
            logging.info(
                f'polling period of {attr} is set to {self._polling_period}')

    reset_number = Basler.reset_number

    @command()
    def read_files(self):
        self.write_folder_path(self._folder_path)


if __name__ == "__main__":
    FileReader.run_server()
