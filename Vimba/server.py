#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
from tango import AttrWriteType, DevState, DevFloat, EncodedAttribute
from tango.server import Device, attribute, command, device_property
import numpy as np
import time
import datetime
import logging
import os
import sys
from PIL import Image
from threading import Thread
from queue import Queue
import platform
from vmbpy import *

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


def grabbing_wrap(func):
    def wrapper(*args, **kwargs):
        is_grabbing = args[0].camera.is_streaming()
        if is_grabbing:
            args[0].camera.stop_streaming()
            args[0].logger.info(
                f"stop grabbing temporarily in {func.__name__}")
        func(*args, **kwargs)
        if is_grabbing:
            args[0].get_ready()
    return wrapper


class Vimba(Device):
    '''
    is_polling_periodically attribute. If is_polling_periodically is False, the polling is manually controlled by the acquisition script, else the polling is made by the polling period "polling".
    '''

    image = attribute(
        label="image",
        max_dim_x=10000,
        max_dim_y=10000,
        dtype=((np.uint16,),),
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

    friendly_name = device_property(dtype=str, default_value='')

    model = attribute(
        label="model",
        dtype=str,
        access=AttrWriteType.READ,
    )

    user_defined_name = attribute(
        label="name",
        dtype=str,
        access=AttrWriteType.READ,
        doc="The user_defined_name is originally defined in the Vimba Viewer software. Some Allied Vision cameras don't support this function. Now this property is the serial number."
    )

    def read_user_defined_name(self):
        return self.camera.get_serial()

    is_polling_periodically = attribute(
        label="polling periodically",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc='polling the image periodically or by external acquisition code'
    )

    exposure = attribute(
        name="exposure",
        label="exposure",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        unit="us",
    )
    gain = attribute(
        name="gain",
        label="gain",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )

    fps = attribute(
        label="frame rate",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        doc='frame rate (only applicable in live mode trigger source or under acquisition start trigger selector)'
    )

    format_pixel = attribute(
        label="pixel format",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
    )

    is_new_image = attribute(
        label='new',
        dtype=bool,
        access=AttrWriteType.READ,
    )

    is_debug_mode = attribute(
        label='debug',
        dtype=bool,
        memorized=True,
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
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_polling_period(self):
        return self._polling

    def write_polling_period(self, value):
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

        trigger_source = attribute(
            name="trigger_source",
            label="trigger source",
            dtype=str,
            access=AttrWriteType.READ_WRITE,
            memorized=True,
            hw_memorized=True,
            doc='off or software or external'
        )

        self.add_attribute(width)
        self.add_attribute(height)
        self.add_attribute(trigger_source)

    def read_exposure(self):
        self._exposure = self.camera.ExposureTimeAbs.get()
        return self._exposure

    def write_exposure(self, value):
        self.camera.ExposureTimeAbs.set(value)
        self._exposure = value

    def read_gain(self):
        self._gain = self.camera.Gain.get()
        return self._gain

    def write_gain(self, value):
        self.camera.Gain.set(value)
        self._gain = value

    def read_width(self, attr):
        self._width = self.camera.Width.get()
        return self._width

    @grabbing_wrap
    def write_width(self, attr):
        self.camera.Width.set(attr.get_write_value())

    def read_height(self, attr):
        self._height = self.camera.Height.get()
        return self._height

    @grabbing_wrap
    def write_height(self, attr):
        self.camera.Height.set(attr.get_write_value())

    def init_device(self):
        self._host_computer = platform.node()
        self.read_trigger_source('args_holder')
        self._is_new_image = False
        self.imageq = Queue()
        self._image = np.zeros(
            (self.read_height('args_holder'), self.read_width('args_holder')))
        self.read_exposure()
        self.read_model()
        # self.read_frames_per_trigger()
        self._polling = self.get_attribute_poll_period('is_new_image')
        if self._polling == 0:
            self._polling = 200
        self.path_raw = ''
        self._is_polling_periodically = False
        self._debug = False
        self._save_data = False
        self._save_path = ''
        self._naming_format = '%t.%f'
        self._save_interval = 0
        self._image_number = 0
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
        self.logger = LoggerAdapter(self.read_user_defined_name(), logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        self.set_state(DevState.ON)

    # def read_save_data(self):
    #     return self._save_data

    # def write_save_data(self, value):
    #     if self._save_data != value:
    #         self.logger.info(f'save status is changed to {value}')
    #     self._save_data = value
    #     if value:
    #         try:
    #             os.makedirs(self._save_path, exist_ok=True)
    #         except FileNotFoundError:
    #             return

    def read_is_polling_periodically(self):
        return self._is_polling_periodically

    def write_is_polling_periodically(self, value):
        self._is_polling_periodically = value
        if not self._is_polling_periodically:
            self.disable_polling('is_new_image')
        else:
            self.enable_polling('is_new_image')

    def read_model(self):
        self._model = self.camera.DeviceModelName.get()
        return self._model

    def read_format_pixel(self):
        return str(self.camera.get_pixel_format())

    @grabbing_wrap
    def write_format_pixel(self, value):
        if "12" in value:
            value = PixelFormat.Mono12
        elif "8" in value:
            value = PixelFormat.Mono8
        self.camera.set_pixel_format(value)

    # def read_trigger_selector(self):
    #     return self.camera.TriggerSelector.Value

    # def write_trigger_selector(self, value):
    #     # somehow has to set trigger mode as off before changing trigger selector
    #     current_trigger_source = self.read_trigger_source('')
    #     if value.lower() == 'acquisitionstart':
    #         self.camera.TriggerMode.SetValue('Off')
    #         value = 'AcquisitionStart'
    #     elif value.lower() == 'framestart':
    #         self.camera.TriggerMode.SetValue('Off')
    #         value = 'FrameStart'
    #     self.camera.TriggerSelector.SetValue(value)
    #     self.logger.info(f'trigger selector is changed to {value}')
    #     if current_trigger_source != 'Off':
    #         self.write_trigger_source(current_trigger_source)

    def convert_trigger_source_text(self, trigger_source: str):
        table = [['Off', 'FixedRate'], ['External', 'Line1']]
        for innerlist in table:
            for i in innerlist:
                if i == trigger_source:
                    innerlist.remove(i)
                    return innerlist[0]
        return trigger_source

    def read_trigger_source(self, attr):
        self._trigger_source = self.convert_trigger_source_text(
            self.camera.TriggerSource.get().as_tuple()[0])
        return self._trigger_source

    def write_trigger_source(self, attr):
        if self.camera.is_streaming():
            self.camera.stop_streaming()
        if hasattr(attr, 'get_write_value'):
            value = attr.get_write_value()
        else:
            value = attr
        self._trigger_source = value
        self.camera.TriggerSource.set(self.convert_trigger_source_text(value))
        self.get_ready()

    def read_fps(self):
        self._fps = self.camera.AcquisitionFrameRateAbs.get()
        return self._fps

    def write_fps(self, value):
        self.camera.AcquisitionFrameRateAbs.set(value)
        self._fps = value

    def read_is_new_image(self):
        # self.i, grabbing successfully grabbed image. self._image_number, image counting and can be reset at any time.
        self._is_new_image = False
        if self.imageq.qsize():
            self._image = self.imageq.get()
            self.push_change_event("image", self.read_image())
            self._image_number += 1
            self._read_time = datetime.datetime.now().strftime("%H-%M-%S.%f")
            return True
        else:
            return False

    def read_image(self):
        return self._image

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

    def handler_one_by_one(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            self.logger.info('Frame acquired: {}'.format(frame))
            frame_array = np.squeeze(frame.as_numpy_ndarray())
            self.imageq.put(frame_array)
        self.camera.queue_frame(frame)

    def handler_last_frame(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            self.logger.info('Frame acquired: {}'.format(frame))
            frame_array = np.squeeze(frame.as_numpy_ndarray())
            self._image = frame_array
        self.camera.queue_frame(frame)

    @command()
    def get_ready(self):
        self.relax()
        if self._trigger_source == 'Off':
            self.camera.start_streaming(self.handler_last_frame)
            self.logger.info(
                'Starting live mode')

        if self._trigger_source in ['Software', 'External']:
            self.camera.start_streaming(self.handler_one_by_one)
            self.logger.info(
                f'Ready to receive {self._trigger_source} triggers')

    @command()
    def send_software_trigger(self):
        if self.camera.TriggerSource.get().as_tuple()[0] != "Software":
            self.logger.info(
                f'Please set the "trigger source" to "software" to send software trigger. Abort!')
            return
        self.logger.info("Sending software trigger....................")
        self.camera.TriggerSoftware.run()

    @command()
    def relax(self):
        if self.camera.is_streaming():
            self.camera.stop_streaming()
            self.imageq = Queue()
            self.logger.info("Grabbing stops")

    @command(dtype_in=int)
    def reset_number(self, number=0):
        self._image_number = number
        self.logger.info("Reset image number")


if __name__ == "__main__":
    with VmbSystem.get_instance() as vmb:
        all_cam = vmb.get_all_cameras()
        for cam in all_cam:
            if cam.get_name() == sys.argv[1] or cam.get_serial() == sys.argv[1]:
                break
        else:
            raise Exception(f'Camera {sys.argv[1]} not found!')
        with cam:
            Vimba.camera = cam
            Vimba.run_server()
