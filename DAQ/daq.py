import tango
import numpy as np
from datetime import datetime
import time
import os
from PIL import Image
import logging
import json
from collections import defaultdict
from PIL import ImageDraw

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
        self.image_list = defaultdict(dict)
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
                # start from shot 1, not shot 0
                self.shot_numbers.append(1)
                if dir:
                    os.makedirs(os.path.join(self.dir, name), exist_ok=True)
                    os.makedirs(os.path.join(self.dir, 'stitching'), exist_ok=True)
                    self.cam_dir.append(os.path.join(self.dir, name))
            except:
                logging.info(f"{name} is not found!")
        logging.info(f'Connected: {self.cams_names}')

    def set_camera_default_configuration(self, config_dict=None):
        if config_dict is None:
            config_dict = {'ta2-nearfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 230, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}, 'ta2-farfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
                        'ta2-gossip': {'format_pixel': "Mono12", "exposure": 1000, "gain": 240, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},'PW_Comp_In':{'format_pixel': "Mono12", "exposure": 5000, "gain": 136, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}}
        json_object = json.dumps(config_dict)
        with open(os.path.join(self.dir, "settings.json"), "w+") as settings_File:
            settings_File.write(json_object)
        if self.cams:
            for i, bs in enumerate(self.cams):
                dev_short_name = bs.dev_name().split('/')[-1]
                if dev_short_name.lower() in config_dict:
                    cam_settings = config_dict[dev_short_name.lower()]
                bs.relax()
                for key, value in cam_settings.items():
                    setattr(bs, key, value)
            

    def get_image(self, bs):
        bits = bs.format_pixel.lower().replace('mono', '')
        if int(bits) > 8:
            bits = '16'
        current_image = bs.image.astype(f'uint{bits}')
        data = Image.fromarray(current_image)
        return data, current_image

    def stretch_image(self, current_image):
        adjusted_image = self.imadjust(current_image)
        adjusted_image = (adjusted_image - np.min(adjusted_image)) / (np.max(adjusted_image) - np.min(adjusted_image))*255
        return adjusted_image

    def take_background(self, stitch=True):
        '''take a background image'''
        for i, bs in enumerate(self.cams):
            bs.trigger_source = "software"
            time.sleep(0.5)
            bs.send_software_trigger()
            time.sleep(0.5)
            if bs.is_new_image:
                data, data_array  = self.get_image(bs)
                data.save(os.path.join(
                    self.cam_dir[i], f'background.tiff'))
                logging.info(f"background is saved {data.size}")
                if stitch:
                    adjusted_image = self.stretch_image(data_array)
                    self.image_list['background'][self.select_cam_list[i]] = adjusted_image
                    if len(self.image_list['background']) == len(self.select_cam_list):
                        self.stitch_images('background').save(os.path.join(self.dir, 'stitching', f'background.tiff'))
            else:
                logging.info('error')

            bs.trigger_source = "external"

    def set_aquisition_start_mode(self):
        '''Use AcquisitionStart mode to acquire a set of image from just one trigger
        '''
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

    def acquisition(self, stitch = True, shot_limit=float('inf')):
        '''
        Main acquisition function. Use external trigger and save data.
        '''
        logging.info('Waiting for a trigger...')
        for idx, bs in enumerate(self.cams):
            bs.reset_number()
        while True:
            is_new_flag = []
            for idx, bs in enumerate(self.cams):
                is_new_flag.append(bs.is_new_image)
            for idx, bs in enumerate(self.cams):
                if self.shot_numbers[idx]<= shot_limit and is_new_flag[idx]:
                    data, data_array = self.get_image(bs)
                    if bs.name == 'PW_Comp_In':
                        file_name = '_'.join([f'shot{self.shot_numbers[idx]}', f'{bs.inferred_energy}J'])
                    else:
                        file_name = f'shot{self.shot_numbers[idx]}'
                    data.save(os.path.join(
                        self.cam_dir[idx], f'{file_name}.tiff'))
                    logging.info("Shot {} taken for {} saved {}:".format(
                        self.shot_numbers[idx], self.cams_names[idx],  {data.size}))
                    if stitch:
                        adjusted_image = self.stretch_image(data_array)
                        self.image_list[f'shot{self.shot_numbers[idx]}'][self.select_cam_list[idx]] = adjusted_image
                        if len(self.image_list[f'shot{self.shot_numbers[idx]}']) == len(self.select_cam_list):
                            self.stitch_images(f'shot{self.shot_numbers[idx]}').save(os.path.join(self.dir, 'stitching', f'shot{self.shot_numbers[idx]}.tiff'))
                    self.shot_numbers[idx] += 1

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
                 
    def stitch_images(self, shotname):
        '''stitch images and add camera name text
        The shotname is usually "background" or "shot1", "shot2"...
        '''
        if not hasattr(self, 'col'):
            layout = {(1,2): 1, (2,5):2, (5,10): 3, (10,17):4}
            for key, value in layout.items():
                if len(self.select_cam_list)>= key[0] and len(self.select_cam_list) < key[1]:
                    self.col = value
                    self.row = int(len(self.select_cam_list)/self.col) + bool(len(self.select_cam_list)%self.col)
                    break
        gap_x, gap_y = 30, 30
        tile_size_x, tile_size_y = 600, 400        
        large_image_p = Image.new("L", [(gap_x+tile_size_x)*self.col+gap_x, (gap_y+tile_size_y)*self.row+gap_y])
        for cam_name, image in self.image_list[shotname].items():
            idx = self.select_cam_list.index(cam_name)
            y_i, x_i = np.unravel_index(idx, (self.row, self.col))
            image_resized = Image.fromarray(image).resize((tile_size_x, tile_size_y))
            large_image_p.paste(image_resized, (gap_x+x_i*(gap_x+tile_size_x), gap_y+y_i*(gap_y+tile_size_y)))

            I1 = ImageDraw.Draw(large_image_p)
            # Add Text to an image
            I1.text((gap_x+x_i*(gap_x+tile_size_x)+0.5*tile_size_x, gap_y+y_i*(gap_y+tile_size_y)-0.5*gap_y), cam_name, fill="white", anchor="mm")
        # large_image_p.show()
        del self.image_list[shotname]
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
