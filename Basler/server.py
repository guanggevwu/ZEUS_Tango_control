#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import tango
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
    polling = 200
    polling_infinite = -1
    # is_memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    # The image attribute should not be polled periodically since images are large. They will be pushed when is_new_image attribute is True.
    image = attribute(
        label="image",
        max_dim_x=4096,
        max_dim_y=4096,
        dtype=((DevFloat,),),
        access=AttrWriteType.READ,
    )

    serial_number = device_property(dtype=str, default_value='')
    friendly_name = device_property(dtype=str, default_value='')

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
        # hw_memorized=True,
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

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    is_debug_mode = attribute(
        label='debug',
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
    )

    def read_is_debug_mode(self):
        return self._debug

    def write_is_debug_mode(self, value):
        self._debug = value

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
        super().init_device()
        self._debug = False
        self.set_state(DevState.INIT)
        self.idx = 0
        try:
            self.device = self.get_camera_device()
            if self.device is not None:
                instance = pylon.TlFactory.GetInstance()

                self.camera = pylon.InstantCamera(
                    instance.CreateDevice(self.device))
                self.camera.Open()
                self._polling = 200
                self._is_new_image = False
                self._image = np.zeros(
                    (self.camera.Height.Value, self.camera.Width.Value))
                # always use continuous mode. Although it seems this is the default, still set it here in case.
                self.camera.AcquisitionMode.SetValue('Continuous')
                self.camera.AcquisitionFrameRateEnable.SetValue(True)
                # repetition is not a parameter in the camera itself
                self._repetition = 1
                self.set_change_event("image", True, False)
                self.camera.MaxNumBuffer.SetValue(1000)
            print(
                f'Camera is connected. {self.device.GetUserDefinedName()}: {self.device.GetSerialNumber()}')
            self.set_state(DevState.ON)
            # self.set_change_event('image', True)
        except:
            print("Could not open camera with serial: {:s}".format(
                self.serial_number))
            self.set_state(DevState.OFF)

    def get_camera_device(self):
        print("we get camera device")
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
        if not hasattr(self, '_save_data'):
            self._save_data = False
        return self._save_data

    def write_save_data(self, value):
        if not hasattr(self, '_save_data'):
            self._save_data = value
        if self._save_data != value:
            self._save_data = value
            logging.info(f'save status is changed to {value}')
        if self._save_data:
            self.disable_polling('is_new_image')
        else:
            self.enable_polling('is_new_image')

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
        # somehow has to set trigger mode as off before changing trigger selector
        current_trigger_source = self.read_trigger_source()
        if value.lower() == 'acquisitionstart':
            self.camera.TriggerMode.SetValue('Off')
            value = 'AcquisitionStart'
        elif value.lower() == 'framestart':
            self.camera.TriggerMode.SetValue('Off')
            value = 'FrameStart'
        self.camera.TriggerSelector.SetValue(value)
        logging.info(f'trigger source is changed to {value}')
        if current_trigger_source != 'Off':
            self.write_trigger_source(current_trigger_source)

    def read_trigger_source(self):
        # replace 'on' with 'Software' and 'Line1'
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
        self.get_ready()

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
        if self.camera.AcquisitionFrameRateEnable.Value:
            return self.camera.AcquisitionFrameRateAbs.Value
        else:
            return 0

    def write_fps(self, value):
        if value:
            self.camera.AcquisitionFrameRateEnable.SetValue(True)
            self.camera.AcquisitionFrameRateAbs.SetValue(value)
        else:
            self.camera.AcquisitionFrameRateEnable.SetValue(False)

    def read_is_new_image(self):
        self.idx += 1
        self._is_new_image = False
        while self.camera.IsGrabbing():
            grabResult = self.camera.RetrieveResult(
                int(self._polling/2), pylon.TimeoutHandling_Return)
            if grabResult.GrabSucceeded():
                self._image = grabResult.Array
                grabResult.Release()
                if self._debug:
                    logging.info(
                        f"{self.idx} new. mean intensity: {np.mean(self._image)}")
                # self.push_change_event('image', self._image)
                if self._save_data and self._save_path:
                    data = Image.fromarray(self._image)
                    parse_save_path = self._save_path.split(';')
                    for path in parse_save_path:
                        os.makedirs(path, exist_ok=True)
                        now = datetime.datetime.strftime(
                            datetime.datetime.now(), '%Y-%m-%d-%H-%M-%S-%f')
                        image_name = f'{now}.tiff'
                        data.save(os.path.join(path, image_name))
                self._is_new_image = True
                self.push_change_event("image", self._image)
                # show image count while not in live mode
                if self.read_trigger_source().lower() != "off":
                    self.i += 1
                    logging.info(
                        f'{self.i}/{self._grab_number}')
                    # get ready after successfully acquiring a set of images
                    if self.i == self._grab_number:
                        self.get_ready()
                return self._is_new_image
            # the else statement may never be triggered. may delete later.
            else:
                logging.info("Started grabbing but no images retrieved yet!")
                return self._is_new_image
        if self._debug:
            logging.info(
                f"{self.idx} old images. mean intensity: {np.mean(self._image)}")
        # return False if there is no new image
        return self._is_new_image

    def read_image(self):
        if self._debug:
            if self._is_new_image:
                logging.info("getting new images.")
            else:
                logging.info("getting old images.")
        return self._image

    def disable_polling(self, attr):
        if self.is_attribute_polled(attr):
            self.stop_poll_attribute(attr)
            logging.info(f'polling for {attr} is disabled')

    def enable_polling(self, attr):
        if not self.is_attribute_polled(attr):
            self.poll_attribute(attr, self._polling)
            logging.info(f'polling period of {attr} is set to {self._polling}')

    # @command()
    # def image_reader(self):
    #     # <- with this line we force change event generation, and transmitting new image
    #     if self._is_new_image:
    #         logging.info("sending push event")
    #         self.push_change_event("image", self._image)
    #     else:
    #         logging.info("No sending since it is an old image")

    # @command()
    # def ext_sent(self):
    #     # I don't find a way to know if an external trigger is received. Using camera.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException) is bad because the timeout is too long.
    #     if not self._save_data:
    #         self.enable_polling('is_new_image')

    @command()
    def get_ready(self):
        """
        If trigger mode is Off, then the trigger selector has no effect.
        """
        if self.camera.TriggerMode.Value.lower() == 'off':
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logging.info(
                'Starting live mode')
            self.set_state(DevState.ON)
        else:
            self.i = 0
            if self.camera.TriggerSelector.Value == 'FrameStart':
                self._grab_number = 1
            else:
                self._grab_number = self.camera.AcquisitionFrameCount.Value * self._repetition
            # self.disable_polling('is_new_image')
            self.camera.StartGrabbingMax(
                self._grab_number, pylon.GrabStrategy_OneByOne)
            logging.info(
                f'Ready to receive triggers from {self.read_trigger_source()}. Image retrieve will be stopped after receiving {self._grab_number} images')

    @command()
    def send_software_trigger(self):
        if self.camera.TriggerSource.Value != "Software":
            logging.info(
                f'Please set the "trigger source" to "software" to send software trigger. Abort!')
            return
        logging.info("Sending software trigger....................")
        self.camera.TriggerSoftware.Execute()
        # if not self._save_data:
        #     self.enable_polling('is_new_image')
        self.set_state(DevState.ON)

    @command()
    def relax(self):
        self.camera.StopGrabbing()
        self.set_state(DevState.ON)
        logging.info("Grabbing stops")


if __name__ == "__main__":
    Basler.run_server()
