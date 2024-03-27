#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
from pypylon import pylon
from numpy import array
import numpy as np
import time
import datetime
import logging
from PIL import Image
import os

# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class Basler(Device):

    polling = 1000
    polling_infinite = -1
    # is_memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    image = attribute(
        label="image",
        max_dim_x=4096,
        max_dim_y=4096,
        dtype=((DevFloat,),),
        access=AttrWriteType.READ,
        polling_period=polling,
    )

    serial_number = device_property(dtype=str, default_value='40222934')

    # image_encoded = attribute(label='encnoded image',
    #            access=AttrWriteType.READ)

    # no need since it is a device property
    # serial_number = attribute(
    #     label="serial number",
    #     dtype="str",
    #     access=AttrWriteType.READ,
    #     polling_period=polling_infinite,
    # )

    model = attribute(
        label="model name",
        dtype=str,
        access=AttrWriteType.READ,
    )

    save_data = attribute(
        label="save data",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
        doc='save the images or not'
    )

    save_path = attribute(
        label='save path',
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
        doc='save data path, use ";" to seperate multiple paths'
    )

    trigger_source = attribute(
        label="trigger source",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
        doc='off or software or external'
    )

    trigger_selector = attribute(
        label="trigger selector",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # polling_period=polling,
        doc='usually use acquisition start'
    )

    frames_per_trigger = attribute(
        label="frames per trigger",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # polling_period=polling,
        doc='frames generated per trigger'
    )

    repetition = attribute(
        label="triggers per shot",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
        doc='triggers to be received before transferring the data'
    )

    fps = attribute(
        label="frame rate",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # polling_period=polling,
        doc='frame rate (only applicable when frames per trigger is large than 1)'
    )

    offsetX = attribute(
        label="offset x axis",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
    )

    offsetY = attribute(
        label="offset y axis",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
    )

    format_pixel = attribute(
        label="pixel format",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # polling_period=polling,
    )

    # framerate = attribute(
    #     label="max framerate",
    #     dtype=float,
    #     access=AttrWriteType.READ,
    #     polling_period=polling_infinite,
    # )

    binning_horizontal = attribute(
        label="binning_horizontal",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
    )

    binning_vertical = attribute(
        label="binning_vertical",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        hw_memorized=True,
        # polling_period=polling,
    )

    sensor_readout_mode = attribute(
        label="sensor readout mode",
        dtype=str,
        access=AttrWriteType.READ,
        # polling_period=polling_infinite,
    )

    timeoutt = 1000

    def initialize_dynamic_attributes(self):
        '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open'''
        exposure = attribute(
            name="exposure",
            label="exposure",
            dtype=float,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,

            # polling_period=self.polling,
            unit="us",
            min_value=self.camera.ExposureTimeAbs.Min,
            max_value=self.camera.ExposureTimeAbs.Max
        )
        gain = attribute(
            name="gain",
            label="gain",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,

            # polling_period=self.polling,
            min_value=self.camera.GainRaw.Min,
            max_value=self.camera.GainRaw.Max
        )
        width = attribute(
            name="width",
            label="width of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,

            # polling_period=self.polling,
            min_value=self.camera.Width.Min,
            max_value=self.camera.Width.Max,
        )

        height = attribute(
            name='height',
            label="height of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,

            # polling_period=self.polling,
            min_value=self.camera.Height.Min,
            max_value=self.camera.Height.Max,
        )
        self.add_attribute(exposure)
        self.add_attribute(gain)
        self.add_attribute(width)
        self.add_attribute(height)
        # if self.camera.DeviceModelName() in ['acA640-121gm']:
        self.remove_attribute('sensor_readout_mode')

    def read_exposure(self, attr):
        return self.camera.ExposureTimeAbs.Value

    def write_exposure(self, attr):
        self.camera.ExposureTimeAbs.Value = attr.get_write_value()

    def read_gain(self, attr):
        return self.camera.GainRaw()

    def write_gain(self, attr):
        self.camera.GainRaw.Value = attr.get_write_value()

    def read_width(self, attr):
        return self.camera.Width()

    def write_width(self, attr):
        self.camera.StopGrabbing()
        self.camera.Width.Value = attr.get_write_value()

    def read_height(self, attr):
        return self.camera.Height()

    def write_height(self, attr):
        self.camera.StopGrabbing()
        self.camera.Height.Value = attr.get_write_value()

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.INIT)

        try:
            self.device = self.get_camera_device()
            if self.device is not None:
                instance = pylon.TlFactory.GetInstance()

                self.camera = pylon.InstantCamera(
                    instance.CreateDevice(self.device))
                self.camera.Open()

                # always use continuous mode. Although it seems this is the default, still set it here in case.
                self.camera.AcquisitionMode.SetValue('Continuous')
                self.camera.TriggerSelector.SetValue('AcquisitionStart')
                # self.camera.TriggerMode.SetValue('On')
                # repetition is not a parameter in the camera ifself
                self._repetition = 1
            print(f'Camera is connected: {self.device.GetSerialNumber()}')
            self.set_state(DevState.ON)
            # self.set_change_event('image', True)
        except:
            print("Could not open camera with serial: {:s}".format(
                self.serial_number))
            self.set_state(DevState.OFF)

    def get_camera_device(self):
        print("we get camera device")
        for device in pylon.TlFactory.GetInstance().EnumerateDevices():
            if device.GetSerialNumber() == self.serial_number:
                return device
        # factory = pylon.TlFactory.GetInstance()
        # empty_camera_info = pylon.DeviceInfo()
        # empty_camera_info.SetPropertyValue('SerialNumber', self.serial_number)
        # camera_device = factory.CreateDevice(empty_camera_info)
        return None

    # def read_serial_number(self):
    #     return self.device.GetSerialNumber()

    def read_save_data(self):
        if not hasattr(self, '_save_data'):
            self._save_data = False
        return self._save_data

    def write_save_data(self, value):
        if not hasattr(self, '_save_data'):
            self._save_data = value
        if self._save_data != value:
            self._save_data = value
            logging.info(f'save status is changed to {value}')

    def read_save_path(self):
        if not hasattr(self, '_save_path'):
            self._save_path = os.path.join(
                os.path.dirname(__file__), 'basler_tmp_data')
            os.makedirs(self._save_path, exist_ok=True)
        if len(self._save_path) > 20:
            if ";" in self._save_path:
                return ";".join([f'{e[0:2]}...{e[-2:-1]}' for e in self._save_path.split(';')])
            return f'{self._save_path[0:5]}...{self._save_path[-5:-1]}'
        else:
            return self._save_path

    def write_save_path(self, value):
        self._save_path = value

    def read_model(self):
        return self.camera.GetDeviceInfo().GetModelName()

    def read_format_pixel(self):
        return self.camera.PixelFormat()

    def write_format_pixel(self, value):
        if type(value) == str:
            self.camera.PixelFormat = value
        else:
            self.camera.PixelFormat = self.camera.PixelFormat()

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

    def read_binning_horizontal(self):
        return self.camera.BinningHorizontal()

    def write_binning_horizontal(self, value):
        # To check limit. Use self.camera.BinningHorizontal.Min
        self.camera.BinningHorizontal.Value = value

    def read_binning_vertical(self):
        return self.camera.BinningVertical()

    def write_binning_vertical(self, value):

        self.camera.BinningVertical.Value = value

    def read_sensor_readout_mode(self):
        return self.camera.SensorReadoutMode.GetValue()

    def read_trigger_selector(self):
        return self.camera.TriggerSelector.Value

    def write_trigger_selector(self, value):
        if value.lower() == 'acquisitionstart':
            value = 'AcquisitionStart'
        elif value.lower() == 'framestart':
            value = 'FrameStart'
        self.camera.TriggerSelector.SetValue(value)

    def read_trigger_source(self):
        if self.camera.TriggerMode.Value == 'Off':
            return 'Off'
        else:
            return self.camera.TriggerSource.Value

    def write_trigger_source(self, value):
        self.camera.StopGrabbing()
        if value.lower() == 'off':
            self.camera.TriggerMode.SetValue('Off')
        else:
            self.camera.TriggerMode.SetValue('On')
            if value.lower() == 'external':
                self.camera.TriggerSource.SetValue('Line1')
            else:
                self.camera.TriggerSource.SetValue(value.capitalize())

    def read_frames_per_trigger(self):
        return self.camera.AcquisitionFrameCount.Value

    def write_frames_per_trigger(self, value):
        self.camera.StopGrabbing()
        self.camera.AcquisitionFrameCount.SetValue(value)

    def read_repetition(self):
        return self._repetition

    def write_repetition(self, value):
        self.camera.StopGrabbing()
        self._repetition = value

    def read_fps(self):
        return self.camera.AcquisitionFrameRateAbs.Value

    def write_fps(self, value):
        self.camera.AcquisitionFrameRateAbs.SetValue(value)

    def read_image(self):
        try:
            while self.camera.IsGrabbing():
                grabResult = self.camera.RetrieveResult(
                    100, pylon.TimeoutHandling_ThrowException)
                if self.read_trigger_source().lower() != "off":
                    self.i += 1
                    logging.info(
                        f'{self.i}/{self.camera.AcquisitionFrameCount.Value * self._repetition}')
                if grabResult.GrabSucceeded():
                    self._image = grabResult.Array
                    grabResult.Release()
                    logging.info(f"mean instensity: {np.mean(self._image)}")
                    # self.push_change_event('image', self._image)
                    if self._save_data:
                        data = Image.fromarray(self._image)
                        parse_save_path = self._save_path.split(';')
                        for path in parse_save_path:
                            os.makedirs(path, exist_ok=True)
                            now = datetime.datetime.strftime(
                                datetime.datetime.now(), '%Y-%m-%d-%H-%M-%S-%f')
                            image_name = f'{now}.tiff'
                            data.save(os.path.join(path, image_name))
                    return self._image
        except Exception as ex:
            if ex.__class__.__name__ == "TimeoutException":
                pass
                # logging.info("Started grabbing but no images retrieved yet!")
        if not hasattr(self, "_image"):
            self._image = np.zeros(
                (self.camera.Height.Value, self.camera.Width.Value))
        # logging.info(f"mean instensity: {np.mean(self._image)}")
        return self._image

    @command()
    def get_ready(self):
        if self.camera.TriggerMode.Value.lower() == 'off':
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logging.info(
                'Starting live mode')
            self.set_state(DevState.ON)
        else:
            self.i = 0
            self.camera.StartGrabbingMax(
                self.camera.AcquisitionFrameCount.Value * self._repetition, pylon.GrabStrategy_OneByOne)
            logging.info(
                f'Ready to receive triggers. Either "send_software_trigger" or send external triggers. Image retrieve will be stopped after receiving {self.camera.AcquisitionFrameCount.Value * self._repetition} images')
            self.set_state(DevState.STANDBY)

    @command()
    def send_software_trigger(self):
        if self.camera.TriggerSource.Value != "Software":
            self.write_trigger_source(self, "Software")
            logging.info(
                f'Trigger source is changed from {self.camera.TriggerSource.Value} to Software')
        time.sleep(0.5)
        logging.info("Sending software trigger....................")
        self.camera.TriggerSoftware.Execute()
        self.set_state(DevState.ON)

    @command()
    def relax(self):
        self.camera.StopGrabbing()
        self.set_state(DevState.ON)


if __name__ == "__main__":
    Basler.run_server()
