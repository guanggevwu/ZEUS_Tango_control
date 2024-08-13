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
import sys
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.other import generate_basename

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, select_cam_list, dir='', debug=False, check_exist=True):
        self.cam_info = defaultdict(dict)
        self.dir = dir
        self.select_cam_list = select_cam_list
        for c in select_cam_list:
            try:
                bs = tango.DeviceProxy(c)
                self.cam_info[c] = {}
                self.cam_info[c]['device_proxy'] = bs
                self.cam_info[c]['shortname'] = c.split('/')[-1]
                self.cam_info[c]['cam_dir'] = os.path.join(
                    self.dir, self.cam_info[c]['shortname'])
                self.cam_info[c]['images_to_stitch'] = {}
                Yes_for_all = False
                if dir and check_exist and not Yes_for_all and os.path.exists(self.cam_info[c]['cam_dir']):
                    files_num = sum(
                        [len(files) for r, d, files in os.walk(self.cam_info[c]['cam_dir'])])
                    if files_num:
                        is_overwrite = input(
                            f'{self.cam_info[c]["cam_dir"]} already exists and has {files_num} files in it. Overwrite? yes(y)/all(a)/no(n)')
                        if is_overwrite.lower() == 'a':
                            Yes_for_all = True
                        elif is_overwrite.lower() != 'y':
                            logging.info(
                                "Raise because of not wanting to overwrite!")
                            raise
                if dir:
                    os.makedirs(os.path.join(
                        self.dir, self.cam_info[c]['shortname']), exist_ok=True)
                    os.makedirs(os.path.join(
                        self.dir, 'stitching'), exist_ok=True)

                logging.info(f'Connected: {c}')
            except:
                logging.info(f"{c} is not found!")
        if not len(select_cam_list):
            logging.info("No cameras are found! Raise!")
            raise
        self.debug = debug

    def set_camera_configuration(self, config_dict=None, saving=True):
        if config_dict is None:
            # use lower case
            config_dict = {'ta2-nearfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 230, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}, 'ta2-farfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
                           'ta2-gossip': {'format_pixel': "Mono12", "exposure": 1000, "gain": 240, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False}, 'PW_Comp_In'.lower(): {'format_pixel': "Mono12", "exposure": 5000, "gain": 136, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False, "saving_format": '%s_%t_%e_%h.%f'}, 'testcam': {'format_pixel': "Mono8", "exposure": 1000, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False, "saving_format": '%s_%t_%e_%h.%f'}, 'all': {}}
        self.config_dict = config_dict
        if saving:
            json_object = json.dumps(config_dict)
            os.makedirs(self.dir, exist_ok=True)
            with open(os.path.join(self.dir, "settings.json"), "w+") as settings_File:
                settings_File.write(json_object)
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            dev_short_name = bs.dev_name().split('/')[-1]
            if dev_short_name.lower() in config_dict:
                cam_settings = config_dict[dev_short_name.lower()]
            elif 'all' in config_dict:
                cam_settings = config_dict['all']
            info['config_dict'] = cam_settings
            bs.relax()
            for key, value in cam_settings.items():
                if hasattr(bs, key):
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
        adjusted_image = (adjusted_image - np.min(adjusted_image)) / \
            (np.max(adjusted_image) - np.min(adjusted_image))*255
        return adjusted_image

    def take_background(self, stitch=True):
        '''take a background image'''
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            bs.trigger_source = "software"
            time.sleep(0.5)
            bs.send_software_trigger()
            time.sleep(0.5)
            if bs.is_new_image:
                data, data_array = self.get_image(bs)
                data.save(os.path.join(
                    info['cam_dir'], f'background.tiff'))
                logging.info(f"background is saved {data.size}")
                if stitch:
                    adjusted_image = self.stretch_image(data_array)
                    info['images_to_stitch']['background'] = adjusted_image
                    if len([value['background'] for key, value in info.items() if key == 'images_to_stitch']) == len(self.cam_info):
                        self.stitch_images('background').save(
                            os.path.join(self.dir, 'stitching', f'background.tiff'))
            else:
                logging.info('error')

            bs.trigger_source = "external"

    def set_acquisition_start_mode(self):
        '''Use AcquisitionStart mode to acquire a set of image from just one trigger
        '''
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            # trigger_selector not applicable for one of the cameras. need fix it.
            bs.trigger_selector = "AcquisitionStart"
            bs.frames_per_trigger = 1
            bs.repetition = self.shots

    def test_mode(self):
        """
        test the camera using software trigger
        """
        for c, info in self.cam_info.items():
            info['device_proxy'].trigger_source = "software"

    def simulate_send_software_trigger(self, interval, shots=1):
        for i in range(shots):
            for c in self.cam_info:
                bs = self.cam_info[c]['device_proxy']
                if bs.trigger_source.lower() == "software":
                    bs.send_software_trigger()
            time.sleep(interval)
            logging.info(f"trigger {i} sent!")

    def acquisition(self, stitch=True, shot_limit=float('inf'), interval_threshold=0):
        '''
        Main acquisition function. Use external trigger and save data.
        interval_threshold. The saving is triggered only when the interval is larger than the threshold.
        '''
        logging.info('Waiting for a trigger...')
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            bs.reset_number()
            info['shot_num'] = 1
        while True:
            for c, info in self.cam_info.items():
                bs = info['device_proxy']
                # when there is a short limit, the acquisition stops after the requested image numbers are reached.
                info['is_completed'] = False
                if info['shot_num'] > shot_limit:
                    info['is_completed'] = True
                elif bs.is_new_image:
                    data, data_array = self.get_image(bs)
                    # info['time1'] = time.perf_counter()
                    # if info['shot_num'] > 1:
                    #     info['time_interval'] = info['time1'] - info['time0']
                    #     if info['time_interval'] < interval_threshold:
                    #         os.remove(os.path.join(
                    #             info['cam_dir'], f'{info["file_name"]}.tiff'))
                    # info['time0'] = info['time1']
                    info['file_name'] = '%s.%f' if 'saving_format' not in info['config_dict'] else info['config_dict']['saving_format']
                    info['file_name'] = generate_basename(
                        info['file_name'], {'%s': f'Shot{info["shot_num"]}', '%t': f'Time{bs.read_time}', '%e': f'Energy{bs.energy:.3f}J', '%h': f'Energy{bs.hot_spot:.4f}Jcm-2', '%f': 'tiff'})
                    # the saving interval threshold has been enabled in server side.
                    # if info['shot_num'] == 1 or (info['time_interval'] > interval_threshold):
                    data.save(os.path.join(
                        info['cam_dir'], info["file_name"]))
                    logging.info("Shot {} taken for {} saved {} to {}:".format(
                        info['shot_num'], info['shortname'],  {data.size}, {os.path.join(
                            info['cam_dir'], info["file_name"])}))
                    if stitch:
                        adjusted_image = self.stretch_image(data_array)
                        info['images_to_stitch'][f'shot{info["shot_num"]}'] = adjusted_image
                        if len([value[f'shot{info["shot_num"]}'] for key, value in info.items() if key == 'images_to_stitch']) == len(self.cam_info):
                            self.stitch_images(f'shot{info["shot_num"]}').save(
                                os.path.join(self.dir, 'stitching', f'shot{info["shot_num"]}.tiff'))
                    info['shot_num'] += 1
            if not False in [value['is_completed'] for value in self.cam_info.values()]:
                return

    def imadjust(self, input, tol=0.01):
        """
        input: numpy array
        tol: set the smallest tol and the largest tol value to tol value and (1-tol) value
        """
        tolindex1 = int((input.size)*tol)
        tolindex2 = int((input.size)*(1-tol))
        value_at_tol = np.partition(input.flatten(), tolindex1)[tolindex1]
        value_at_one_mninus_tol = np.partition(
            input.flatten(), tolindex2)[tolindex2]
        output = input.copy()
        output[input < value_at_tol] = value_at_tol
        output[input > value_at_one_mninus_tol] = value_at_one_mninus_tol
        return output

    def stitch_images(self, image_name):
        '''stitch images and add camera name text
        The image_name is usually "background" or "shot1", "shot2"...
        '''
        if not hasattr(self, 'col'):
            layout = {(1, 2): 1, (2, 5): 2, (5, 10): 3, (10, 17): 4}
            for key, value in layout.items():
                if len(self.cam_info) >= key[0] and len(self.cam_info) < key[1]:
                    self.col = value
                    self.row = int(len(self.cam_info)/self.col) + \
                        bool(len(self.cam_info) % self.col)
                    break
        gap_x, gap_y = 30, 30
        tile_size_x, tile_size_y = 600, 400
        large_image_p = Image.new(
            "L", [(gap_x+tile_size_x)*self.col+gap_x, (gap_y+tile_size_y)*self.row+gap_y])
        # for cam_name, image in self.image_list[image_name].items():
        for idx, (c, info) in enumerate(self.cam_info.items()):
            cam_name = info['shortname']
            # idx = self.cam_info.index(cam_name)
            y_i, x_i = np.unravel_index(idx, (self.row, self.col))
            image_resized = Image.fromarray(
                info['images_to_stitch'][image_name]).resize((tile_size_x, tile_size_y))
            large_image_p.paste(
                image_resized, (gap_x+x_i*(gap_x+tile_size_x), gap_y+y_i*(gap_y+tile_size_y)))

            I1 = ImageDraw.Draw(large_image_p)
            # Add Text to an image
            I1.text((gap_x+x_i*(gap_x+tile_size_x)+0.5*tile_size_x, gap_y+y_i *
                    (gap_y+tile_size_y)-0.5*gap_y), cam_name, fill="white", anchor="mm")
            del info['images_to_stitch'][image_name]
        # large_image_p.show()
        return large_image_p

    def termination(self, config_dict=None):
        logging.info('terminating...')
        if config_dict is None:
            config_dict = {'all': {"is_polling_periodically": True}}
        self.set_camera_configuration(
            config_dict=config_dict)


if __name__ == "__main__":
    dt_string = datetime.now().strftime("%Y%m%d")
    run_num = input('\nPlease input a run number: ')
    save_dir = os.path.join(r'N:\2024\Qing_test', f'{dt_string}_run{run_num}')
    # select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
    select_cam_list = ['TA2-NearField', 'TA2-FarField']
    daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
    daq.set_camera_configuration()
    daq.take_background()
    # daq.set_aquisition_start_mode()
    # daq.test_mode()
    # daq.acquisition()
