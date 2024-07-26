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
    '''
    is_polling_periodically attribute. If is_polling_periodically is False, the polling is manually controlled by the acquisition script, else the polling is made by the polling period "polling".
    '''
    polling = 200
    polling_infinite = -1
    # memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    # The image attribute should not be polled periodically since images are large. They will be pushed when is_new_image attribute is True.
    image = attribute(
        label="image",
        max_dim_x=4096,
        max_dim_y=4096,
        dtype=((int,),),
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
        doc='save data path on the server, use ";" to seperate multiple paths'
    )

    trigger_source = attribute(
        label="trigger source",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='off or software or external'
    )

    trigger_selector = attribute(
        label="trigger selector",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='usually use acquisition start'
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

    binning_horizontal = attribute(
        label="binning_horizontal",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # hw_memorized=True,
    )

    binning_vertical = attribute(
        label="binning_vertical",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        # hw_memorized=True,
    )

    sensor_readout_mode = attribute(
        label="sensor readout mode",
        dtype=str,
        access=AttrWriteType.READ,
    )

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    is_debug_mode = attribute(
        label='debug',
        dtype=bool,
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
        memorized=is_memorized,
        access=AttrWriteType.READ_WRITE,
    )

    def read_polling_period(self):
        return self.get_attribute_poll_period('is_new_image')

    def write_polling_period(self, value):
        if self._exposure/1000 > 0.9 * value * self._timeout_polling_ratio:
            logging.info(
                f'{value} ms is too short compared to the exposure time {self._exposure/1000} ms. Minimum value is {self._exposure/1000/0.9/self._timeout_polling_ratio}. Discard!')
        else:
            self.poll_attribute('is_new_image', value)

    image_number = attribute(
        label='image #',
        dtype=int,
        access=AttrWriteType.READ,
        polling_period=polling,
        doc="image number since reset"
    )

    def read_image_number(self):
        return self._image_number

    def read_polling_period(self):
        return self.get_attribute_poll_period('is_new_image')

    def write_polling_period(self, value):
        if self._exposure/1000 > 0.9 * value * self._timeout_polling_ratio:
            logging.info(
                f'{value} ms is too short compared to the exposure time {self._exposure/1000} ms. Minimum value is {self._exposure/1000/0.9/self._timeout_polling_ratio}. Discard!')
        else:
            self.poll_attribute('is_new_image', value)

    def initialize_dynamic_attributes(self):
        '''To dynamically add attribute. The reason is the min_value and max_value are not available until the camera is open'''
        exposure = attribute(
            name="exposure",
            label="exposure",
            dtype=float,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,
            unit="us",
            # min_value=self.camera.ExposureTimeAbs.Min,
            # max_value=self.camera.ExposureTimeAbs.Max
        )
        gain = attribute(
            name="gain",
            label="gain",
            dtype=float,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,
            # min_value=self.camera.GainRaw.Min,
            # max_value=self.camera.GainRaw.Max
        )
        width = attribute(
            name="width",
            label="width of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,
            min_value=self.camera.Width.Min,
            max_value=self.camera.Width.Max,
        )

        height = attribute(
            name='height',
            label="height of the image",
            dtype=int,
            access=AttrWriteType.READ_WRITE,
            memorized=self.is_memorized,
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
        if self._model in self.model_type:
            self._exposure = self.camera.ExposureTime.Value
        else:
            self._exposure = self.camera.ExposureTimeAbs.Value
        return self._exposure

    def write_exposure(self, attr):
        if attr.get_write_value()/1000 > 0.9 * self._polling * self._timeout_polling_ratio:
            self._polling = attr.get_write_value()/1000/0.9/self._timeout_polling_ratio
            self.poll_attribute('is_new_image', int(self._polling))
            logging.info(
                f'Changed the image retrieve timeout to {self._polling} to match the long exposure time')
        # "a2A1920-51gmBAS" is the farfield camera
        if self._model in self.model_type:
            self.camera.ExposureTime.Value = attr.get_write_value()
        else:
            self.camera.ExposureTimeAbs.Value = attr.get_write_value()
        self._exposure = attr.get_write_value()

    def read_gain(self, attr):
        if self._model in self.model_type:
            self._gain = self.camera.Gain.Value
        else:
            self._gain = self.camera.GainRaw()
        return float(self._gain)

    def write_gain(self, attr):
        if self._model in self.model_type:
            self.camera.Gain.Value = float(attr.get_write_value())
        else:
            self.camera.GainRaw.Value = int(attr.get_write_value())
        self._gain = attr.get_write_value()

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
        self.model_type = ['a2A1920-51gmBAS', 'a2A2590-22gmBAS']
        self._is_polling_periodically = False
        self._debug = False
        self._save_data = False
        self._image_number = 0
        super().init_device()
        self.set_state(DevState.INIT)
        self.idx = 0
        try:
            self.device = self.get_camera_device()
            if self.device is not None:
                instance = pylon.TlFactory.GetInstance()
                self.camera = pylon.InstantCamera(
                    instance.CreateDevice(self.device))
                self.camera.Open()
                self.read_model()
                self.read_exposure('')
                self.read_frames_per_trigger()
                self._polling = self.get_attribute_poll_period('is_new_image')
                if self._polling == 0:
                    self._polling = self.polling
                self._timeout_polling_ratio = 0.75
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

    def read_is_polling_periodically(self):
        if not self._is_polling_periodically:
            self.disable_polling('is_new_image')
        else:
            self.enable_polling('is_new_image')
        return self._is_polling_periodically

    def write_is_polling_periodically(self, value):
        self._is_polling_periodically = value
        self.read_is_polling_periodically()

    def read_save_path(self):
        # The value of save path (short name) can be different from the self._save_path (full name).
        if not hasattr(self, '_save_path'):
            self._save_path = os.path.join(
                os.path.dirname(__file__), 'basler_tmp_data')
        # if len(self._save_path) > 20:
        #     if ";" in self._save_path:
        #         return ";".join([f'{e[0:2]}...{e[-2:-1]}' for e in self._save_path.split(';')])
        #     return f'{self._save_path[0:5]}...{self._save_path[-5:]}'
        # else:
        return self._save_path

    def write_save_path(self, value):
        try:
            os.makedirs(value, exist_ok=True)
        except FileNotFoundError:
            return
        self._save_path = value

    def read_model(self):
        self._model = self.camera.GetDeviceInfo().GetModelName()
        return self._model

    def read_format_pixel(self):
        return self.camera.PixelFormat.Value

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
            self._is_polling_periodically = True
        else:
            self.camera.TriggerMode.SetValue('On')
            if value.lower() == 'external':
                self.camera.TriggerSource.SetValue('Line1')
            else:
                self.camera.TriggerSource.SetValue(value.capitalize())
        self.get_ready()

    def read_frames_per_trigger(self):
        if self._model in self.model_type:
            self._frames_per_trigger = self.camera.AcquisitionBurstFrameCount.Value
        else:
            self._frames_per_trigger = self.camera.AcquisitionFrameCount.Value
        return self._frames_per_trigger

    def write_frames_per_trigger(self, value):
        is_grabbing = self.camera.IsGrabbing()
        if is_grabbing:
            self.camera.StopGrabbing()
        if self._model in self.model_type:
            self.camera.AcquisitionBurstFrameCount.SetValue(value)
        else:
            self.camera.AcquisitionFrameCount.SetValue(value)
        self._frames_per_trigger = value
        if is_grabbing:
            self.get_ready()

    def read_repetition(self):
        return self._repetition

    def write_repetition(self, value):
        is_grabbing = self.camera.IsGrabbing()
        if is_grabbing:
            self.camera.StopGrabbing()
        self._repetition = value
        if is_grabbing:
            self.get_ready()

    def read_fps(self):
        if self.camera.AcquisitionFrameRateEnable.Value:
            if self._model in self.model_type:
                self._fps = self.camera.AcquisitionFrameRate.Value
            else:
                self._fps = self.camera.AcquisitionFrameRateAbs.Value
            return self._fps
        else:
            return 0

    def write_fps(self, value):
        if value:
            self.camera.AcquisitionFrameRateEnable.SetValue(True)
            if self._model in self.model_type:
                self.camera.AcquisitionFrameRate.SetValue(value)
            else:
                self.camera.AcquisitionFrameRateAbs.SetValue(value)
            self._fps = value
        else:
            self.camera.AcquisitionFrameRateEnable.SetValue(False)
            self._fps = 0

    def read_is_new_image(self):
        self.idx += 1
        self._is_new_image = False
        while self.camera.IsGrabbing():
            # the retrieve time out may need to be reconsidered.
            grabResult = self.camera.RetrieveResult(
                int(100), pylon.TimeoutHandling_Return)
            if grabResult and grabResult.GrabSucceeded():
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
                # self.push_change_event("image", self._image)
                self.push_change_event("image", self.read_image())
                self.push_change_event(
                    "image_number", self.read_image_number())
                # show image count while not in live mode
                if self.read_trigger_source().lower() != "off":
                    self.i += 1
                    self._image_number += 1
                    logging.info(
                        f'{self.i}')
            else:
                if self._debug:
                    logging.info(
                        "Started grabbing but no images retrieved yet!")
            return self._is_new_image
        if self._debug:
            logging.info(
                f"{self.idx} old images. mean intensity: {np.mean(self._image)}")
        # return False if there is no new image
        return self._is_new_image

    def read_image(self):
        # now read_image() is only triggered when it is a new image.
        return self._image

    def disable_polling(self, attr):
        if self.is_attribute_polled(attr):
            self.stop_poll_attribute(attr)
            logging.info(f'polling for {attr} is disabled')

    def enable_polling(self, attr):
        if not self.is_attribute_polled(attr):
            self.poll_attribute(attr, self._polling)
            logging.info(f'polling period of {attr} is set to {self._polling}')

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
            self._grab_number = 9999
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

    @command()
    def reset_number(self):
        self._image_number = 0
        self.set_state(DevState.ON)
        logging.info("Reset image number")


if __name__ == "__main__":
    Basler.run_server()
