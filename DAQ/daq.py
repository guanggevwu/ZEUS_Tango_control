import tango
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
                    os.makedirs(os.path.join(self.dir, 'stitching'), exist_ok=True)
                    self.cam_dir.append(os.path.join(self.dir, name))
            except:
                logging.info(f"{name} is not found!")
        logging.info(f'Connected: {self.cams_names}')

    def set_camera_default_configuration(self):
        config_dict = {'ta2-nearfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 230, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}, 'ta2-farfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
                       'ta2-gossip': {'format_pixel': "Mono12", "exposure": 1000, "gain": 240, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}}
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

    def save_image(self, bs, stitch=True):
        bits = bs.format_pixel.lower().replace('mono', '')
        if int(bits) > 8:
            bits = '16'
        current_image = bs.image.astype(f'uint{bits}')
        if stitch:
            adjusted_image = self.imadjust(current_image)
            adjusted_image = (adjusted_image - np.min(adjusted_image)) / (np.max(adjusted_image) - np.min(adjusted_image))*255
            self.image_list.append(adjusted_image)
        array_size = current_image.shape
        data = Image.fromarray(current_image)
        return data, array_size

    def take_background(self, *args, **kwargs):
        '''take a background image'''
        self.image_list=[]
        for i, bs in enumerate(self.cams):
            bs.trigger_source = "software"
            time.sleep(0.5)
            bs.send_software_trigger()
            time.sleep(0.5)
            if bs.is_new_image:
                data, array_size = self.save_image(bs, *args, **kwargs)
                data.save(os.path.join(
                    self.cam_dir[i], f'background.tiff'))
                logging.info(f"background is saved {array_size}")
            else:
                logging.info('error')
            bs.trigger_source = "external"
        self.stitch_images().save(os.path.join(
            self.dir, 'stitching', f'background.tiff'))

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

    def acquisition(self, stitch = True):
        '''
        Main acquisition function. Use external trigger and save data.
        '''
        for idx, bs in enumerate(self.cams):
            bs.reset()
        while True:
            self.image_list = []
            is_new_flag = []
            for idx, bs in enumerate(self.cams):
                is_new_flag.append(bs.is_new_image)
            for idx, bs in enumerate(self.cams):
                if is_new_flag[idx]:
                    data, array_size = self.save_image(bs)
                    data.save(os.path.join(
                        self.cam_dir[idx], f'shot{self.shot_numbers[idx]}.tiff'))
                    logging.info("Shot {} taken for {} saved {}:".format(
                        self.shot_numbers[idx], self.cams_names[idx],  {array_size}))
                    self.shot_numbers[idx] += 1
            self.stitch_images().save(os.path.join(
                        self.dir, 'stitching', f'shot{self.shot_numbers[idx]}.tiff'))

    def imadjust(self, input, tol=0.01):
        """
        input: numpy array
        tol: set the smallest tol and the largest tol value to tol value and (1-tol) value
        """
        tolindex1 = int((input.size)*tol)
        tolindex2 = int((input.size)*(1-tol))
        value_at_tol = np.partition(input.flatten(), tolindex1)[tolindex1]
        value_at_one_mninus_tol = np.partition(input.flatten(), tolindex2)[tolindex2]
        output = input.copy()
        output[input<value_at_tol] = value_at_tol
        output[input>value_at_one_mninus_tol] = value_at_one_mninus_tol
        return output
                 
    def stitch_images(self):
        # large = Image.new("RGB", (1920, 1000), (255, 255, 255))
        layout = {(1,2): 1, (2,5):2, (5,10): 3, (10,17):4}
        for key, value in layout.items():
            if len(self.image_list)>= key[0] and len(self.image_list) < key[1]:
                col = value
                row = int(len(self.image_list)/col) + bool(len(self.image_list)%col)
                break
        gap_x, gap_y = 30, 30
        tile_size_x, tile_size_y = 600, 400        
        large_image_p = Image.new("L", [(gap_x+tile_size_x)*col+gap_x, (gap_y+tile_size_y)*col+gap_y])
        for idx, image in enumerate(self.image_list):
            y_i, x_i = np.unravel_index(idx, (row, col))
            image = Image.fromarray(image).resize((tile_size_x, tile_size_y))
            large_image_p.paste(image, (gap_x+x_i*(gap_x+tile_size_x), gap_y+y_i*(gap_y+tile_size_y)))
        # large_image_p.show()
        return large_image_p

if __name__ == "__main__":
    dt_string = datetime.now().strftime("%Y%m%d")
    run_num = input('\nPlease input a run number: ')
    save_dir = os.path.join(r'N:\2024\Qing_test', f'{dt_string}_run{run_num}')
    # select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
    select_cam_list = ['TA2-NearField', 'TA2-FarField']
    daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
    daq.set_camera_default_configuration()
    daq.take_background()
    # daq.set_aquisition_start_mode()
    # daq.test_mode()
    # daq.acquisition()
