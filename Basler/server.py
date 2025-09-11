#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
from pypylon import pylon
import numpy as np
import time
import datetime
import logging
import os
import sys
from scipy.ndimage import convolve
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from queue import Queue
import csv
import platform

if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.other import generate_basename
# -----------------------------


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs


class Basler(Device):
    '''
    is_polling_periodically attribute. If is_polling_periodically is False, the polling is manually controlled by the acquisition script, else the polling is made by the polling period "polling".
    '''
    polling_infinite = -1
    # memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    # The image attribute should not be polled periodically since images are large. They will be pushed when is_new_image attribute is True.
    def grabbing_wrap(func):
        '''
        A decorator to stop grabbing before executing the function and start grabbing after the function is executed.'''
        def wrapper(*args, **kwargs):
            is_grabbing = args[0].camera.IsGrabbing()
            if is_grabbing:
                args[0].camera.StopGrabbing()
                args[0].logger.info(
                    f"stop grabbing temporarily in {func.__name__}")
            func(*args, **kwargs)
            if is_grabbing:
                args[0].get_ready()
        return wrapper

    image = attribute(
        label="image",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((np.uint16,),),
        access=AttrWriteType.READ,
    )

    image_r = attribute(
        label="image_r",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((np.uint8,),),
        access=AttrWriteType.READ,
    )

    image_g = attribute(
        label="image_g",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((np.uint8,),),
        access=AttrWriteType.READ,
    )

    image_b = attribute(
        label="image_b",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((np.uint8,),),
        access=AttrWriteType.READ,
    )

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

    flux = attribute(
        label="flux",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((float,),),
        unit='J*cm**-2',
        access=AttrWriteType.READ,
    )

    hot_spot = attribute(
        label="hot spot",
        dtype=float,
        unit='J*cm**-2',
        format='8.4f',
        access=AttrWriteType.READ,
        doc="Flat kernel is used. The kernel size is 7*7 for 3PW_Grating-4_NF camera and 5*5 for 3PW_Screen camera. The real size is about 0.22*0.22 cm2. The energy per area is to show the read location data, thus the leak coefficient and clip coefficient (only for 3PW_Grating-4_NF) are considered."
    )

    serial_number = device_property(dtype=str, default_value='')
    friendly_name = device_property(dtype=str, default_value='')

    # image_encoded = attribute(label='encoded image',
    #            access=AttrWriteType.READ)

    # no need since it is a device property
    # serial_number = attribute(
    #     label="serial number",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    # )

    model = attribute(
        label="model",
        dtype=str,
        access=AttrWriteType.READ,
    )

    user_defined_name = attribute(
        label="name",
        dtype=str,
        access=AttrWriteType.READ,
    )

    def read_user_defined_name(self):
        return self.camera.GetDeviceInfo().GetUserDefinedName()

    energy = attribute(
        label="energy",
        dtype=float,
        unit='J',
        access=AttrWriteType.READ,
        doc='Calibrated by QE195 E = sum(I)_from_current_image*Energy_reading_from_QE195_during_calibration/sum(I)_during_calibration. The energy value here is to mimic the reading from QE195, thus no clip coefficient and leak coefficient are considered.'
    )

    def read_energy(self):
        return self._energy

    is_polling_periodically = attribute(
        label="polling periodically",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='polling the image periodically or by external acquisition code'
    )

    save_data = attribute(
        label="save data",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='save the images on the server'
    )

    save_path = attribute(
        label='save path (folder)',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='Save data path on the server. Use %date to indicate today; Use ";" to separate multiple paths'
    )

    save_interval = attribute(
        label='save interval',
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit='s',
        memorized=is_memorized,
        hw_memorized=True,
        doc='If the trigger interval is longer than the save_interval threshold, images will be saved. Otherwise, no saving.'
    )

    def read_save_interval(self):
        return self._save_interval

    def write_save_interval(self, value):
        self._save_interval = value

    resulting_fps = attribute(
        label="resulting frame rate",
        dtype=float,
        access=AttrWriteType.READ,
        doc='Several factors may limit the frame rate on any Basler camera, e.g., bandwidth.'
    )

    bandwidth = attribute(
        label="bandwidth",
        dtype=float,
        unit="MB/s",
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='Bandwidth assigned to this device. For some simple cameras, this parameter is not availabe, shown as -1.'
    )
    naming_format = attribute(
        label='naming format',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='Naming format for the image file. For example, "%s_%t_%e_%h.%f", where %s is for shot number, %t is for timestamp, %e is for energy, %h is for hot spot, %f is tiff'
    )

    def read_naming_format(self):
        return self._naming_format

    def write_naming_format(self, value):
        self._naming_format = value

    lr_flip = attribute(
        label='lr flip',
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc="flip the image left-right"
    )

    def read_lr_flip(self):
        return self._lr_flip

    def write_lr_flip(self, value):
        self._lr_flip = value

    ud_flip = attribute(
        label='ud flip',
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc="flip the image up-down"
    )

    def read_ud_flip(self):
        return self._ud_flip

    def write_ud_flip(self, value):
        self._ud_flip = value

    rotate = attribute(
        label='rotate',
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc="Rotate the image counterclockwise. Accepted value is 90, 180, 270."
    )

    def read_rotate(self):
        return self._rotate

    def write_rotate(self, value):
        if value in [0, 90, 180, 270]:
            self._rotate = value
        else:
            raise ('Must be 0, 90, 180 or 270.')

    exposure = attribute(
        name="exposure",
        label="exposure",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        unit="us",
    )
    gain = attribute(
        name="gain",
        label="gain",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
    )
    frames_per_trigger = attribute(
        label="frames per trigger",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='frames generated per trigger'
    )

    repetition = attribute(
        label="triggers per shot",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        doc='triggers to be received before transferring the data'
    )

    fps = attribute(
        label="frame rate",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='frame rate (only applicable when frames per trigger is large than 1)'
    )

    offsetX = attribute(
        label="offset x axis",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # hw_memorized=True,
    )

    offsetY = attribute(
        label="offset y axis",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # hw_memorized=True,
    )

    format_pixel = attribute(
        label="pixel format",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
    )

    trigger_selector = attribute(
        label="trigger selector",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # hw_memorized=True,
        doc='FrameStart for one image per trigger and AcquisitionStart for multiple images per trigger.'
    )

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    is_debug_mode = attribute(
        label='debug',
        dtype=bool,
        memorized=is_memorized,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_is_debug_mode(self):
        return self._debug

    def write_is_debug_mode(self, value):
        self._debug = value

    polling_period = attribute(
        label='image polling',
        dtype=int,
        unit='ms',
        hw_memorized=True,
        memorized=is_memorized,
        access=AttrWriteType.READ_WRITE,
    )

    def read_polling_period(self):
        # self._polling = self.get_attribute_poll_period('is_new_image')
        return self._polling

    def write_polling_period(self, value):
        # if self._exposure/1000 > 0.9 * value * self._timeout_polling_ratio:
        #     self.logger.info(
        #         f'{value} ms is too short compared to the exposure time {self._exposure/1000} ms. Minimum value is {self._exposure/1000/0.9/self._timeout_polling_ratio}. Discard!')
        # else:
        self._polling = value
        if self._is_polling_periodically:
            self.poll_attribute('is_new_image', value)

    image_number = attribute(
        label='image #',
        dtype=int,
        access=AttrWriteType.READ,
        doc="image number since reset"
    )

    def read_image_number(self):
        if self._debug:
            self.logger.info(f'Reading image number: {self._image_number}')
        return self._image_number

    def initialize_dynamic_attributes(self):
        '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open.
        The max width of the image is determined by the camera model and the binning value. So better remove the min max value constrain.
        '''

        width = attribute(
            name="width",
            label="width of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
        )

        height = attribute(
            name='height',
            label="height of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
        )

        binning_horizontal = attribute(
            name='binning_horizontal',
            label="binning_horizontal",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
        )

        binning_vertical = attribute(
            name='binning_vertical',
            label="binning_vertical",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
        )

        trigger_source = attribute(
            name="trigger_source",
            label="trigger source",
            dtype=str,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
            doc='off or software or external'
        )

        filter_option = attribute(
            name="filter_option",
            label="filter option",
            dtype=str,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
            doc='Filters used before PW_Comp_In camera. 0 is for customized parameters. Others uses previously calibrated parameters.'
        )

        image_with_MeV_mark = attribute(
            name="image_with_MeV_mark",
            label="image_with_MeV_mark",
            max_dim_x=10000,
            max_dim_y=10000,
            dtype=((np.uint16,),),
            access=AttrWriteType.READ,
        )

        if self._model != 'a2A1920-51gcBAS':
            self.add_attribute(binning_horizontal)
            self.add_attribute(binning_vertical)
        if self.friendly_name == "3PW_Grating-4_NF" or self.friendly_name == "3PW_Screen" or self.friendly_name == "test":
            self.add_attribute(filter_option)
            self._filter_option = "1"
        if self._has_MeV_mark:
            self.add_attribute(image_with_MeV_mark)
            self._image_with_MeV_mark = np.zeros(
                (self.camera.Height.Value, self.camera.Width.Value))
        self.add_attribute(width)
        self.add_attribute(height)
        self.add_attribute(trigger_source)
        # self.add_attribute("trigger_source")
        # if self.camera.DeviceModelName() in ['acA640-121gm']:

    def read_image_with_MeV_mark(self, attr):
        return self._image_with_MeV_mark

    def draw_dash_line(self, draw, start, end, period_length=40, ratio=0.5):
        number = int(((end[0] - start[0])**2 +
                     (end[1] - start[1])**2)**0.5/period_length)
        arc = np.arctan2(end[1] - start[1], end[0] - start[0])
        dx, dy = period_length*np.cos(arc), period_length*np.sin(arc)
        for i in range(number):
            line_start = (np.array(start)+[i*dx, i*dy]).astype(int)
            line_end = (np.array(start) +
                        [i*dx+dx*ratio, i*dy+dy*ratio]).astype(int)
            draw.line([tuple(line_start), tuple(line_end)],
                      fill=int(np.max(self._image)), width=5)

    def read_exposure(self):
        if self._model_category == 1:
            self._exposure = self.camera.ExposureTime.Value
        else:
            self._exposure = self.camera.ExposureTimeAbs.Value
        return self._exposure

    def write_exposure(self, value):
        # if self._is_polling_periodically and attr.get_write_value()/1000 > 0.9 * self._polling * self._timeout_polling_ratio:
        #     self._polling = attr.get_write_value()/1000/0.9/self._timeout_polling_ratio
        #     self.poll_attribute('is_new_image', int(self._polling))
        #     self.logger.info(
        #         f'Changed the image retrieve timeout to {self._polling} to match the long exposure time')
        if self._model_category == 1:
            self.camera.ExposureTime.Value = value
        else:
            self.camera.ExposureTimeAbs.Value = value
        self._exposure = value

    def read_gain(self):
        if self._model_category == 1:
            self._gain = self.camera.Gain.Value
        else:
            self._gain = self.camera.GainRaw()
        return float(self._gain)

    def write_gain(self, value):
        if self._model_category == 1:
            self.camera.Gain.Value = float(value)
        else:
            self.camera.GainRaw.Value = int(value)
        self._gain = value

    def read_width(self, attr):
        self._width = self.camera.Width()
        return self._width

    @grabbing_wrap
    def write_width(self, attr):
        self.camera.Width.Value = attr.get_write_value()

    def read_height(self, attr):
        self._height = self.camera.Height()
        return self._height

    @grabbing_wrap
    def write_height(self, attr):
        self.camera.Height.Value = attr.get_write_value()

    def read_binning_horizontal(self, attr):
        self._binning_horizontal = self.camera.BinningHorizontal()
        return self._binning_horizontal

    @grabbing_wrap
    def write_binning_horizontal(self, attr):
        # To check limit. Use self.camera.BinningHorizontal.Min
        self._binning_horizontal = attr.get_write_value()
        self.camera.BinningHorizontal.Value = attr.get_write_value()

    def read_binning_vertical(self, attr):
        self._binning_vertical = self.camera.BinningVertical()
        return self.camera.BinningVertical()

    @grabbing_wrap
    def write_binning_vertical(self, attr):
        self._binning_vertical = attr.get_write_value()
        self.camera.BinningVertical.Value = attr.get_write_value()

    def read_filter_option(self, attr):
        if self._filter_option == "0":
            return "accepting user defined calibration parameters"
        elif self._filter_option in self.filter_option_details:
            return f"using OD 2+4, {self.filter_option_details[self._filter_option]}"
        else:
            return "wrong input"

    def write_filter_option(self, attr):
        self._filter_option = attr.get_write_value()
        # key: self._filter_option. Values: [0]Energy reading from QE195 [1] mean intensity [2]calculated clip coefficient for "3PW_Grating-4_NF" [3] Energy reading from QE195 [4] mean intensity for camera 3PW_Screen.
        if attr.get_write_value() in self.filter_option_details:
            self._filter_option = attr.get_write_value()
            if self.friendly_name == "3PW_Grating-4_NF" or self.friendly_name == 'test':
                self.QE195_reading = self.filter_option_details[self._filter_option][0]
                self.mean_intensity_of_calibration_images = self.filter_option_details[
                    self._filter_option][1]
                self.clip_coe = self.filter_option_details[self._filter_option][2]
                self.energy_intensity_coefficient = self.QE195_reading / \
                    (self.mean_intensity_of_calibration_images*640*512)
            elif self.friendly_name == "3PW_Screen":
                self.QE195_reading = self.filter_option_details[self._filter_option][3]
                self.mean_intensity_of_calibration_images = self.filter_option_details[
                    self._filter_option][4]
                self.energy_intensity_coefficient = self.QE195_reading / \
                    (self.mean_intensity_of_calibration_images*640*512)
        elif attr.get_write_value() == "0":
            self._filter_option = attr.get_write_value()
        else:
            raise Exception(
                f"Can't accept the filter option [{attr.get_write_value()}]")

    def init_device(self):
        self._host_computer = platform.node()
        self.model_type = ['a2A1920-51gmBAS',
                           'a2A2590-22gmBAS', 'a2A5320-7gmPRO']
        self.filter_option_details = {
            "1": [27.53, 26.988, 0.8455, 27.53, 24.540], "2": [23.24, 21.370, 0.827, 23.24, 20.641]}
        self.path_raw = ''
        self._is_polling_periodically = False
        self._debug = False
        self._save_data = False
        self._save_path = ''
        self._naming_format = '%t.%f'
        self._save_interval = 0
        self._image_number = 0
        self._energy = 0
        self._hot_spot = 0
        self._read_time = 'N/A'
        self._use_date = False
        self._lr_flip = False
        self._ud_flip = False
        self._rotate = 0
        self._frames_per_trigger = 1
        self._repetition = 50
        super().init_device()
        self.set_state(DevState.INIT)
        logger = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self.friendly_name, logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        # force disable polling for "image" in DB
        self.disable_polling('image')
        try:
            self.device = self.get_camera_device()
            if self.device is not None:
                instance = pylon.TlFactory.GetInstance()
                self.camera = pylon.InstantCamera(
                    instance.CreateDevice(self.device))
                self.camera.Open()
                self.read_model()
                if self._model in self.model_type or self._model.startswith('a2'):
                    self._model_category = 1
                else:
                    self._model_category = 0
                self.read_exposure()
                self.read_frames_per_trigger()
                self._polling = self.get_attribute_poll_period('is_new_image')
                if self._polling == 0:
                    self._polling = 200
                self._timeout_polling_ratio = 0.75
                self._image = np.zeros(
                    (self.camera.Height.Value, self.camera.Width.Value))
                # if the pixel format can be read as rbg8, definitely should use slicing for images. Sometimes the pixel format at device start up is not 'rgb8', but I know for this type of camera (a2A1920-51gcBAS) we probably will change the format to 'rgb8' later, so we include rgb slice at startup.
                if self.read_format_pixel().lower() == "rgb8" or self._model == 'a2A1920-51gcBAS':
                    self._image_r = np.zeros(
                        (self.camera.Height.Value, self.camera.Width.Value))
                    self._image_g = np.zeros(
                        (self.camera.Height.Value, self.camera.Width.Value))
                    self._image_b = np.zeros(
                        (self.camera.Height.Value, self.camera.Width.Value))
                self._flux = np.zeros(
                    (self.camera.Height.Value, self.camera.Width.Value))
                # always use continuous mode. Although it seems this is the default, still set it here in case.
                self.camera.AcquisitionMode.SetValue('Continuous')
                self.camera.AcquisitionFrameRateEnable.SetValue(True)
                self.set_change_event("image", True, False)
                self.camera.MaxNumBuffer.SetValue(1000)
                self.leak_coe = 0.815
                self._calibration = 1
                self.clip_coe = 1
                self.mean_intensity_of_calibration_images = 1
                self.QE195_reading = 1
                if self.friendly_name == "3PW_Grating-4_NF":
                    self.energy_intensity_coefficient = self.QE195_reading / \
                        (self.mean_intensity_of_calibration_images*640*512)
                    self.pixel_size = 4.97/107
                    self.kernel = np.ones([7, 7])/49
                elif self.friendly_name == "3PW_Screen" or self.friendly_name == 'test':
                    self.energy_intensity_coefficient = self.QE195_reading / \
                        (self.mean_intensity_of_calibration_images*640*512)
                    self.pixel_size = 20/316
                    self.kernel = np.ones([5, 5])/25
                else:
                    self._calibration = 0
                    self._flux = np.zeros((2, 2))
                self._has_MeV_mark = 0
                if self.friendly_name == "TA1-EspecH" or self.friendly_name == 'test':
                    self._has_MeV_mark = 1
                self.q = Queue()
                print(
                    f'Camera is connected. {self.device.GetUserDefinedName()}: {self.device.GetSerialNumber()}')
                self.set_state(DevState.ON)
        except:
            print("Could not open camera with serial: {:s}".format(
                self.serial_number))
            self.set_state(DevState.OFF)

    def delete_device(self):
        self.camera.Close()
        print("Camera is disconnected.")
        super().delete_device()

    def get_camera_device(self):
        for device in pylon.TlFactory.GetInstance().EnumerateDevices():
            if device.GetSerialNumber() == self.serial_number or device.GetUserDefinedName() == self.friendly_name:
                return device
        # factory = pylon.TlFactory.GetInstance()
        # empty_camera_info = pylon.DeviceInfo()
        # empty_camera_info.SetPropertyValue('SerialNumber', self.serial_number)
        # camera_device = factory.CreateDevice(empty_camera_info)
        return None

    # def read_serial_number(self):
    #     return self.device.GetSerialNumber()

    def read_save_data(self):
        return self._save_data

    def write_save_data(self, value):
        if self._save_data != value:
            self.logger.info(f'save status is changed to {value}')
        self._save_data = value
        if value:
            try:
                os.makedirs(self._save_path, exist_ok=True)
            except FileNotFoundError:
                return

    def read_is_polling_periodically(self):
        return self._is_polling_periodically

    def write_is_polling_periodically(self, value):
        self._is_polling_periodically = value
        if not self._is_polling_periodically:
            self.disable_polling('is_new_image')
        else:
            self.enable_polling('is_new_image')

    def read_save_path(self):
        if self._use_date and datetime.datetime.today().strftime("%Y%m%d") not in self._save_path:
            self.write_save_path(self.path_raw)
        return self._save_path

    def write_save_path(self, value):
        # if the entered path has %date in it, replace %date with today's date and mark a _use_date flag
        self.path_raw = value
        if '%date' in value:
            self._use_date = True
            value = value.replace(
                '%date', datetime.datetime.today().strftime("%Y%m%d"))
        else:
            self._use_date = False
        value_split = value.split(';')
        if self._save_data:
            for idx, v in enumerate(value_split):
                try:
                    os.makedirs(v, exist_ok=True)
                except OSError as inst:
                    logging.error(inst)
                    raise Exception(f'error on save_path part {idx}')
        self._save_path = value
        self.push_change_event("save_path", self.read_save_path())

    def get_settings(self):
        if self._calibration:
            self.csv_fieldnames = ['_read_time', '_image_number', '_energy', '_hot_spot', '_exposure', '_gain', '_binning_horizontal', '_binning_vertical', '_width',
                                   '_height', 'QE195_reading', 'mean_intensity_of_calibration_images', 'leak_coe', 'clip_coe', 'pixel_size']
        else:
            self.csv_fieldnames = ['_read_time', '_image_number',  '_exposure', '_gain',
                                   '_binning_horizontal', '_binning_vertical', '_width', '_height']
        self.data_to_log = {}
        for name in self.csv_fieldnames:
            if hasattr(self, name):
                self.data_to_log[name] = str(getattr(self, name))

    def save_settings(self, save_path, data_to_log):
        '''write the important camera parameters and calibration data.'''
        logging_file_path = os.path.join(save_path, 'logging.csv')
        to_do = 'w'
        # if the file exists and the existing data is same as the current data, then skip. If the file exists but the data is different, append with 'a' mode. Else, overwrite with 'w' mode.
        if os.path.isfile(logging_file_path):
            to_do = 'a'
        try:
            with open(logging_file_path, to_do, newline='') as csvfile:
                writer = csv.DictWriter(
                    csvfile, fieldnames=data_to_log.keys())
                if to_do == 'w':
                    writer.writeheader()
                writer.writerow(data_to_log)
        except ValueError:
            self.logger.info(
                f"Check the logging file at {logging_file_path}")

    def read_model(self):
        self._model = self.camera.GetDeviceInfo().GetModelName()
        return self._model

    def read_format_pixel(self):
        return self.camera.PixelFormat.Value

    @grabbing_wrap
    def write_format_pixel(self, value):
        if type(value) == str:
            self.camera.PixelFormat.Value = value
        else:
            self.camera.PixelFormat.Value = self.camera.PixelFormat()

    def read_offsetX(self):
        return self.camera.OffsetX()

    def write_offsetX(self, value):
        self.camera.OffsetX.Value = value

    def read_offsetY(self):
        return self.camera.OffsetY()

    def write_offsetY(self, value):
        self.camera.OffsetY.Value = value

    # def read_framerate(self):
    #     return self.camera.ResultingFrameRateAbs()

    def read_trigger_selector(self):
        return self.camera.TriggerSelector.Value

    def write_trigger_selector(self, value):
        # somehow has to set trigger mode as off before changing trigger selector
        current_trigger_source = self.read_trigger_source('')
        if value.lower() == 'acquisitionstart':
            self.camera.TriggerMode.SetValue('Off')
            value = 'AcquisitionStart'
        elif value.lower() == 'framestart':
            self.camera.TriggerMode.SetValue('Off')
            value = 'FrameStart'
        self.camera.TriggerSelector.SetValue(value)
        self.logger.info(f'trigger selector is changed to {value}')
        if current_trigger_source != 'Off':
            self.write_trigger_source(current_trigger_source)

    def read_trigger_source(self, attr):
        # replace 'on' with 'Software' and 'Line1'
        if self.camera.TriggerMode.Value == 'Off':
            return 'Off'
        elif self.camera.TriggerSource.Value == "Line1":
            return "External"
        else:
            return self.camera.TriggerSource.Value

    def write_trigger_source(self, attr):
        self.camera.StopGrabbing()
        if hasattr(attr, 'get_write_value'):
            value = attr.get_write_value()
        else:
            value = attr
        if value.lower() == 'off':
            self.camera.TriggerMode.SetValue('Off')
            self.write_is_polling_periodically(True)
        else:
            self.camera.TriggerMode.SetValue('On')
            if value.lower() == 'external':
                self.camera.TriggerSource.SetValue('Line1')
            else:
                self.camera.TriggerSource.SetValue(
                    value.capitalize())
        self.get_ready()

    def read_frames_per_trigger(self):
        if self._model_category == 1:
            self._frames_per_trigger = self.camera.AcquisitionBurstFrameCount.Value
        else:
            self._frames_per_trigger = self.camera.AcquisitionFrameCount.Value
        return self._frames_per_trigger

    @grabbing_wrap
    def write_frames_per_trigger(self, value):
        if self._model_category == 1:
            self.camera.AcquisitionBurstFrameCount.SetValue(value)
        else:
            self.camera.AcquisitionFrameCount.SetValue(value)
        self._frames_per_trigger = value

    def read_repetition(self):
        return self._repetition

    def write_repetition(self, value):
        self._repetition = value

    def read_fps(self):
        if self.camera.AcquisitionFrameRateEnable.Value:
            if self._model_category == 1:
                self._fps = self.camera.AcquisitionFrameRate.Value
            else:
                self._fps = self.camera.AcquisitionFrameRateAbs.Value
            return self._fps
        else:
            return 0

    def write_fps(self, value):
        if value:
            self.camera.AcquisitionFrameRateEnable.SetValue(True)
            if self._model_category == 1:
                self.camera.AcquisitionFrameRate.SetValue(value)
            else:
                self.camera.AcquisitionFrameRateAbs.SetValue(value)
            self._fps = value
        else:
            self.camera.AcquisitionFrameRateEnable.SetValue(False)
            self._fps = 0

    def read_resulting_fps(self):
        if self._model_category == 1:
            self._resulting_fps = self.camera.BslResultingAcquisitionFrameRate.Value
        else:
            self._resulting_fps = self.camera.ResultingFrameRateAbs.Value
        self._resulting_fps = round(self._resulting_fps, 2)
        return self._resulting_fps

    def read_bandwidth(self):
        try:
            self._bandwidth = float(self.camera.GetNodeMap().GetNode(
                'DeviceLinkThroughputLimit').Value)/1e6
        except:
            self._bandwidth = -1
        return self._bandwidth

    def write_bandwidth(self, value):
        try:
            self._bandwidth = self.camera.GetNodeMap().GetNode(
                'DeviceLinkThroughputLimit').SetValue(int(value*1e6))
        except:
            self._bandwidth = -1

    def read_is_new_image(self):
        # self.i, grabbing successfully grabbed image. self._image_number, image counting and can be reset at any time.
        self._is_new_image = False
        while self.camera.IsGrabbing():
            # the retrieve time out may need to be reconsidered.
            time0 = time.perf_counter()
            grabResult = self.camera.RetrieveResult(
                100, pylon.TimeoutHandling_Return)
            if self._debug:
                self.logger.info(f'grab takes {time.perf_counter() - time0}')
            if grabResult and grabResult.GrabSucceeded():
                if self.read_trigger_source("").lower() != "off":
                    self.i += 1
                    self._image_number += 1
                    self.logger.info(
                        f'{self.i}')
                self._image = grabResult.Array
                if len(self._image.shape) == 3:
                    self._image_r = self._image[:, :, 0]
                    self._image_g = self._image[:, :, 1]
                    self._image_b = self._image[:, :, 2]
                    # Convert to grayscale using the luminance formula (common weights)
                    # Y = 0.299 * R + 0.587 * G + 0.114 * B
                    self._image = 0.299*self._image_r + 0.587 * \
                        self._image_g + 0.114 * self._image_b
                if self._lr_flip:
                    self._image = np.fliplr(self._image)
                if self._ud_flip:
                    self._image = np.flipud(self._image)
                if self._rotate:
                    self._image = np.rot90(self._image, int(self._rotate/90))
                if self._calibration:
                    self._energy = (np.sum(self._image)) * \
                        self.energy_intensity_coefficient
                    self._flux = (self._image) * self.energy_intensity_coefficient * self.clip_coe *\
                        self.leak_coe/self.pixel_size**2
                    convolved_image = convolve(
                        self._flux, self.kernel, mode='constant')
                    self._hot_spot = np.max(
                        convolved_image)
                    cy, cx = np.unravel_index(
                        np.argmax(convolved_image), convolved_image.shape)
                    dy, dx = self.kernel.shape
                    min_value = np.min(self._flux)
                    im_pil = Image.fromarray(self._flux)
                    draw = ImageDraw.Draw(im_pil)
                    enlarged_length = 4
                    draw.rectangle([(max(0, int(cx-(dx+1+enlarged_length)/2)), max(int(cy-(dy+1+enlarged_length)/2), 0)), (min(int(cx+(dx+1+enlarged_length)/2),
                                    convolved_image.shape[1]),  min(int(cy+(dy+1+enlarged_length)/2), convolved_image.shape[0]))], outline=min_value, width=3)
                    self._flux = np.array(im_pil)
                    self.flux_path_string = "flux_image_with_hot_spot"
                if self._has_MeV_mark:
                    ek = np.array([400,   600,  800,  1000, 1200, 1400, 1600,
                                  1800, 2000, 2500, 3000, 3300, 3500, 3800, 4000, 4300])/1000
                    ek_pixels = (72 - np.array([11.6, 23.5, 29.3, 34.1, 37.9, 42.9, 47.6,
                                 51.4, 54.5, 60.3, 64.4, 66.3, 67.4, 68.8, 69.6, 70.8])) * 70 + 324
                    ek_pixels = np.array([int(ek_pixels[i])
                                         for i in range(len(ek_pixels))])
                    im_pil = Image.fromarray(self._image)
                    draw = ImageDraw.Draw(im_pil)
                    font = ImageFont.truetype("arial.ttf", 80)
                    for idx, (i, j) in enumerate(zip(ek, ek_pixels)):
                        self.draw_dash_line(draw, [j, 0], [j, im_pil.size[0]])
                        draw.text(
                            (j-70, im_pil.size[1]-idx*50), str(i)+'G', font=font, fill=int(np.max(self._image)))
                    self._image_with_MeV_mark = np.array(
                        im_pil).astype(self._image.dtype)
                    self.push_change_event(
                        "image_with_MeV_mark", self.read_image_with_MeV_mark("placeholder"))
                grabResult.Release()
                if self._debug:
                    self.logger.info(
                        f"{self._image_number} new. mean intensity: {np.mean(self._image)}")

                self._is_new_image = True
                self._read_time = datetime.datetime.now().strftime("%H-%M-%S.%f")
                # self.push_change_event("image", self._image)
                self.push_change_event("image", self.read_image())
                self.push_change_event("flux", self.read_flux())
                self.push_change_event(
                    "image_number", self.read_image_number())
                self.push_change_event(
                    "energy", self.read_energy())
                self.push_change_event(
                    "hot_spot", self.read_hot_spot())
                # show image count while not in live mode
                if self._save_data and self._save_path:
                    parse_save_path = self._save_path.split(';')
                    self.time1 = time.perf_counter()
                    should_save = True
                    if hasattr(self, 'time0'):
                        self.time_interval = self.time1 - self.time0
                        # ----create the interval threshold, read time attr
                        if self.time_interval < self._save_interval:
                            for path in parse_save_path:
                                if os.path.exists(os.path.join(
                                        path, self.image_basename)):
                                    os.remove(os.path.join(
                                        path, self.image_basename))
                                    try:
                                        with open(os.path.join(path, 'logging.csv'), "r+") as f:
                                            current_position = previous_position = f.tell()
                                            while f.readline():
                                                previous_position = current_position
                                                current_position = f.tell()
                                            f.truncate(previous_position)
                                    except ValueError:
                                        self.logger.info(
                                            f"Check the logging file at {os.path.join(path, 'logging.csv')}")
                                    self.logger.info(
                                        f"Removed previous saved image {self.image_basename}")
                                if self._calibration:
                                    if os.path.exists(os.path.join(
                                            path, self.flux_path_string, self.image_basename)):
                                        os.remove(os.path.join(
                                            path, self.flux_path_string, self.image_basename))
                                should_save = False
                    self.time0 = self.time1
                    # generate file name after delete the old file name
                    self.image_basename = generate_basename(
                        self._naming_format, {'%s': f'ImageNum{self._image_number}', '%t': f'Time{self._read_time}', '%e': f'Energy{self._energy:.3f}J', '%h': f'HotSpot{self._hot_spot:.4f}Jcm-2', '%f': 'tiff'})
                    if should_save:
                        data = Image.fromarray(self._image)
                        self.q.put(data)
                        self.get_settings()
                        self.q.put(self.data_to_log)
                        if self._calibration:
                            self.q.put(im_pil)
                            # self.q.put(Image.fromarray(convolved_image))
                        Thread(target=self.save_image_to_file,
                               args=[self.q]).start()
            return self._is_new_image
        # return False if there is no new image
        return self._is_new_image

    def save_image_to_file(self, q):
        parse_save_path = self._save_path.split(';')
        image_to_save = q.get()
        data_to_log = q.get()
        if self._calibration:
            flux_to_save = q.get()
        for path in parse_save_path:
            os.makedirs(path, exist_ok=True)
            path_to_name = os.path.join(
                path, self.image_basename)
            image_to_save.save(path_to_name)
            self.logger.info(
                f"Image is save to {path_to_name}")
            self.save_settings(path, data_to_log)
            if self._calibration:
                os.makedirs(os.path.join(
                    path, self.flux_path_string), exist_ok=True)
                parts = path_to_name.split(os.sep)
                parts.insert(-1, self.flux_path_string)
                flux_to_save.save(os.path.join(*parts))
                self.logger.info(
                    f"{self.flux_path_string} is save to {path_to_name}")

                # flux_path_string = "smoothed_flux_image"
                # os.makedirs(os.path.join(
                #     path, flux_path_string), exist_ok=True)
                # parts = path_to_name.split(os.sep)
                # parts.insert(-1, flux_path_string)
                # q.get().save(os.path.join(*parts))
                # self.logger.info(
                #     f"f{flux_path_string} is save to {path_to_name}")

    def read_image(self):
        # now read_image() is only triggered when it is a new image. Polling period setting in attribute will Not overwrite the polling settings in the db.
        # If image is polling automatically (periodically), push event from server side still work. But the client request from client side will use the data stored in the period polled buffer.
        # If image is not polling automatically, the client request will call the read_attr function and thus use the latest data.
        # Therefore, image should not be polled.
        self.logger.info(f'in server read: {np.mean(self._image)}')
        return self._image

    def read_image_r(self):
        return self._image_r

    def read_image_g(self):
        return self._image_g

    def read_image_b(self):
        return self._image_b

    def read_flux(self):
        return self._flux

    def read_hot_spot(self):
        return self._hot_spot

    def disable_polling(self, attr):
        if self.is_attribute_polled(attr):
            self.stop_poll_attribute(attr)
            self.logger.info(f'polling for {attr} is disabled')

    def enable_polling(self, attr):
        if not self.is_attribute_polled(attr):
            if not self._polling:
                self._polling = 200
            self.poll_attribute(attr, self._polling)
            self.logger.info(
                f'polling period of {attr} is set to {self._polling}')

    @command()
    def get_ready(self):
        """
        If trigger mode is Off, then the trigger selector has no effect.
        """
        if self.camera.TriggerMode.Value.lower() == 'off':
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.logger.info(
                'Starting live mode')
        else:
            self.i = 0
            # Previous we use a very large number for _grab_number, but it caused some memory problem when we have many camera.
            self._grab_number = max(
                [self._repetition*self._frames_per_trigger, 200])
            self.camera.StartGrabbingMax(
                self._grab_number, pylon.GrabStrategy_OneByOne)
            self.logger.info(
                f'Ready to receive triggers from {self.read_trigger_source("")}. Image retrieve will be stopped after receiving {self._grab_number} images')

    @command()
    def send_software_trigger(self):
        if self.camera.TriggerSource.Value != "Software":
            self.logger.info(
                f'Please set the "trigger source" to "software" to send software trigger. Abort!')
            return
        self.logger.info("Sending software trigger....................")
        self.camera.TriggerSoftware.Execute()

    @command()
    def relax(self):
        self.camera.StopGrabbing()
        self.logger.info("Grabbing stops")

    @command(dtype_in=int)
    def reset_number(self, number=0):
        self._image_number = number
        self.logger.info("Reset image number")


if __name__ == "__main__":
    Basler.run_server()
