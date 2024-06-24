import tango
from pypylon import pylon
import numpy as np
from datetime import datetime
import time
import os
from PIL import Image
import logging
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, dir, device_name_prefix='TA2/basler/', select_cam_list=None, shots=1, debug=False):
        self.dir = dir
        self.device_name_prefix = device_name_prefix
        self.select_cam_list = select_cam_list
        self.shots = shots
        self.debug = debug
        self.cams = []
        self.cams_names = []
        self.shot_numbers = []
        self.cam_dir = []
        for name in self.select_cam_list:
            try:
                bs = tango.DeviceProxy(self.device_name_prefix + name)
                self.cams.append(bs)
                self.cams_names.append(name)
                self.cam_dir.append(os.path.join(self.dir, name))
                os.makedirs(os.path.join(self.dir, name), exist_ok=True)
                self.shot_numbers.append(1)
            except:
                logging.info(f"{name} is not found!")
        logging.info(f'Connected: {self.cams_names}')

    def set_camera_default_configuration(self):
        if self.cams:
            for i, bs in enumerate(self.cams):
                bs.is_debug_mode = self.debug
                bs.relax()
                bs.format_pixel = "Mono12"
                bs.exposure = 200000  # in us
                if 'nearfield' in bs.dev_name():
                    bs.gain = 230
                elif 'farfield' in bs.dev_name():
                    bs.gain = 0
                bs.trigger_selector = "FrameStart"
                bs.trigger_source = "external"
                bs.is_polling_periodically = False
            logging.info('Boring! Waiting for a trigger.')

    def set_aquisition_start_mode(self):
        if self.cams:
            for i, bs in enumerate(self.cams):
                bs.trigger_selector = "AcquisitionStart"
                bs.frames_per_trigger = 1
                bs.repetition = self.shots

    def test_mode(self):
        """
        test the camera using software trigger
        """
        if self.cams:
            for i, bs in enumerate(self.cams):
                bs.trigger_source = "software"

    def simulate_send_software_trigger(self, interval):
        for i in range(self.shots):
            for bs in self.cams:
                if bs.trigger_source.lower() == "software":
                    bs.send_software_trigger()
            time.sleep(interval)
            logging.info(f"trigger {i} sent!")

    def acquisition(self):

        while True:
            is_new_flag = []
            for idx, bs in enumerate(self.cams):
                start_time = datetime.now()
                is_new_flag.append(bs.is_new_image)
                if is_new_flag[-1]:
                    logging.info(
                        f'getting is_new_image from {bs.dev_name()}: {datetime.now()-start_time}')
            for idx, bs in enumerate(self.cams):
                if is_new_flag[idx]:
                    now = datetime.now()
                    dt_string = now.strftime("%d-%m-%Y-%H-%M-%S")
                    bits = bs.format_pixel.lower().replace('mono', '')
                    if int(bits) > 8:
                        bits = '16'
                    current_image = bs.image.astype(f'uint{bits}')
                    array_size = current_image.shape
                    data = Image.fromarray(current_image)
                    data.save(os.path.join(
                        self.cam_dir[idx], f'{dt_string}.tiff'))
                    logging.info("Shot {} taken for {} saved {}:".format(
                        self.shot_numbers[idx], self.cams_names[idx],  {array_size}))
                    self.shot_numbers[idx] += 1


if __name__ == "__main__":
    # save_dir = r'Z:\user_data\2024\Hill\test'
    save_dir = '/home/qzhangqz/Tango/ZEUS_Tango_control/ignored_folder'
    select_cam_list = ['TA2-NearField', 'TA2-FarField']
    daq = Daq(save_dir, select_cam_list=select_cam_list, shots=20)
    daq.set_camera_default_configuration()
    # daq.set_aquisition_start_mode()
    daq.test_mode()
    daq.acquisition()
