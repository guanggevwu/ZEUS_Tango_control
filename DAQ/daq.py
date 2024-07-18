import tango
from pypylon import pylon
import numpy as np
from datetime import datetime
import time
import os
from PIL import Image
import logging
import json
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, dir=None, device_name_prefix='TA2/basler/', select_cam_list=None, shots=1, debug=False):
        self.dir = dir
        self.device_name_prefix = device_name_prefix
        self.select_cam_list = select_cam_list
        self.shots = shots
        self.debug = debug
        self.cams = []
        self.cams_names = []
        self.shot_numbers = []
        self.cam_dir = []
        if os.path.exists(self.dir):
            files_num = sum([len(files) for r, d, files in os.walk(self.dir)])
            is_overwrite = input(
                f'{self.dir} already exists and has {files_num} files in it. Overwrite? (y/n)')
            if is_overwrite.lower() != 'y':
                raise
        for name in self.select_cam_list:
            try:
                bs = tango.DeviceProxy(self.device_name_prefix + name)
                self.cams.append(bs)
                self.cams_names.append(name)
                self.shot_numbers.append(1)
                if dir:
                    os.makedirs(os.path.join(self.dir, name), exist_ok=True)
                    self.cam_dir.append(os.path.join(self.dir, name))
            except:
                logging.info(f"{name} is not found!")
        logging.info(f'Connected: {self.cams_names}')

    def set_camera_default_configuration(self):
        config_dict = {'ta2-nearfield': {'format_pixel': "Mono12", "exposure": 200000, "gain": 230, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}, 'ta2-farfield': {'format_pixel': "Mono12", "exposure": 200000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
                       'ta2-gossip': {'format_pixel': "Mono12", "exposure": 20000, "gain": 240, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}}
        json_object = json.dumps(config_dict)
        with open(os.path.join(self.dir, "settings.json"), "w") as settings_File:
            settings_File.write(json_object)
        if self.cams:
            for i, bs in enumerate(self.cams):
                dev_short_name = bs.dev_name().split('/')[-1]
                if dev_short_name.lower() in config_dict:
                    cam_settings = config_dict[dev_short_name.lower()]
                bs.relax()
                for key, value in cam_settings.items():
                    setattr(bs, key, value)
            logging.info('Boring! Waiting for a trigger.')

    def take_background(self):
        for i, bs in enumerate(self.cams):
            bs.trigger_source = "software"
            time.sleep(0.5)
            bs.send_software_trigger()
            time.sleep(0.5)
            if bs.is_new_image:
                bits = bs.format_pixel.lower().replace('mono', '')
                if int(bits) > 8:
                    bits = '16'
                current_image = bs.image.astype(f'uint{bits}')
                array_size = current_image.shape
                data = Image.fromarray(current_image)
                data.save(os.path.join(
                    self.cam_dir[i], f'background.tiff'))
                logging.info(f"background is saved {array_size}")
            else:
                logging.info('error')
            bs.trigger_source = "external"

    def set_aquisition_start_mode(self):
        if self.cams:
            for i, bs in enumerate(self.cams):
                # trigger_selector not applicable for one of the cameras. need fix it.
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
        for idx, bs in enumerate(self.cams):
            bs.reset()
        while True:
            is_new_flag = []
            for idx, bs in enumerate(self.cams):
                is_new_flag.append(bs.is_new_image)
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
                        self.cam_dir[idx], f'shot{self.shot_numbers[idx]}.tiff'))
                    logging.info("Shot {} taken for {} saved {}:".format(
                        self.shot_numbers[idx], self.cams_names[idx],  {array_size}))
                    self.shot_numbers[idx] += 1


if __name__ == "__main__":
    dt_string = datetime.now().strftime("%Y%m%d")
    run_num = input('\nPlease input a run number: ')
    save_dir = os.path.join(r'N:\2024\Hill', f'{dt_string}_run{run_num}')
    select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
    daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
    daq.set_camera_default_configuration()
    daq.take_background()
    # daq.set_aquisition_start_mode()
    # daq.test_mode()
    daq.acquisition()
