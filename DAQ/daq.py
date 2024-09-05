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
import atexit
from config import default_config_dict

if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.other import generate_basename

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, select_cam_list, dir='', debug=False, check_exist=True, thread_event=None):
        self.cam_info = defaultdict(dict)
        self.dir = dir
        self.select_cam_list = select_cam_list
        self.thread_event = thread_event
        Yes_for_all = False
        if not len(select_cam_list):
            raise Exception("Please select cameras!")
        for c in select_cam_list:
            try:
                bs = tango.DeviceProxy(c)
                self.cam_info[c] = {}
                self.cam_info[c]['device_proxy'] = bs
                self.cam_info[c]['shortname'] = c.split('/')[-1]
                self.cam_info[c]['cam_dir'] = os.path.join(
                    self.dir, self.cam_info[c]['shortname'])
                self.cam_info[c]['images_to_stitch'] = {}
                if dir and check_exist and not Yes_for_all and os.path.exists(self.cam_info[c]['cam_dir']):
                    files_num = sum(
                        [len(files) for r, d, files in os.walk(self.cam_info[c]['cam_dir'])])
                    if files_num:
                        is_overwrite = input(
                            f'{self.cam_info[c]["cam_dir"]} already exists and has {files_num} files in it. Overwrite? yes(y)/all(a)/no(n)')
                        if is_overwrite.lower() == 'a':
                            Yes_for_all = True
                        elif is_overwrite.lower() != 'y':
                            # will not be terminated because this is in a try closure
                            exception = Exception(
                                "Raise because of refusing to overwrite!")
                            raise
                if dir:
                    os.makedirs(os.path.join(
                        self.dir, self.cam_info[c]['shortname']), exist_ok=True)
                    os.makedirs(os.path.join(
                        self.dir, 'stitching'), exist_ok=True)

                logging.info(f'Connected: {c}')
            except:
                if 'exception' in locals():
                    raise exception
                else:
                    raise Exception(f"{c} is not found!")
        self.debug = debug
        atexit.register(self.termination)

    def set_camera_configuration(self, config_dict=None, saving=True):
        if config_dict is None:
            config_dict = default_config_dict
        config_dict = {key: value for key,
                       value in config_dict.items() if (key.lower() in [v['shortname'].lower() for v in self.cam_info.values()]) or (key == 'all')}

        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            dev_short_name = bs.dev_name().split('/')[-1]
            # if the device name is found in config_dict, use it. if not, use "all" instead. Else, pass an empty dict.
            if dev_short_name.lower() in config_dict:
                info['config_dict'] = config_dict[dev_short_name.lower()]
            elif 'all' in config_dict:
                info['config_dict'] = config_dict['all']
            else:
                info['config_dict'] = dict()
            if 'basler' in bs.dev_name():
                bs.relax()
            for key, value in info['config_dict'].items():
                if hasattr(bs, key):
                    setattr(bs, key, value)
            # if the saving_format is not set in the configuration
            if ('saving_format' not in info['config_dict']):
                info['file_name'] = '%s.%f'
            else:
                info['file_name'] = info['config_dict']['saving_format']
        if saving:
            Key_list = ['model', 'format_pixel', "exposure", "gain",
                        "trigger_selector", "trigger_source", "is_polling_periodically"]
            full_configuration = dict()
            for c, info in self.cam_info.items():
                if 'basler' in info['device_proxy'].dev_name():
                    full_configuration[c] = {key: getattr(
                        info['device_proxy'], key) for key in Key_list}
            json_object = json.dumps(full_configuration)
            os.makedirs(self.dir, exist_ok=True)
            with open(os.path.join(self.dir, "settings.json"), "w+") as settings_File:
                settings_File.write(json_object)

    def get_image(self, bs):
        bits = ''.join([i for i in bs.format_pixel if i.isdigit()])
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
            if 'basler' in bs.dev_name():
                trigger_source = bs.trigger_source
                bs.trigger_source = "software"
                time.sleep(0.5)
                bs.send_software_trigger()
                time.sleep(1)
            if bs.is_new_image:
                data, data_array = self.get_image(bs)
                file_name = generate_basename(
                    info['file_name'], {'%s': f'Background', '%t': 'Time{read_time}', '%e': 'Energy{energy:.3f}J', '%h': 'HotSpot{hot_spot:.4f}Jcm-2', '%f': 'tiff', 'device_proxy': bs})
                data.save(os.path.join(
                    info['cam_dir'], file_name))
                logging.info(f"Background is saved {data.size}")
                if stitch:
                    adjusted_image = self.stretch_image(data_array)
                    info['images_to_stitch']['background'] = adjusted_image
                    if sum([1 for one_cam in self.cam_info.values() if 'background' in one_cam['images_to_stitch']]) == len(self.cam_info):
                        self.stitch_images('background').save(
                            os.path.join(self.dir, 'stitching', f'background.tiff'))
            else:
                logging.info('error')
            if 'basler' in bs.dev_name():
                bs.trigger_source = trigger_source

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
            if 'basler' in info['device_proxy'].dev_name():
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
            if self.thread_event is not None:
                if self.thread_event.is_set():
                    break
            for c, info in self.cam_info.items():
                bs = info['device_proxy']
                # when there is a short limit, the acquisition stops after the requested image numbers are reached.
                info['is_completed'] = False
                if info['shot_num'] > shot_limit:
                    info['is_completed'] = True
                elif bs.is_new_image:
                    data, data_array = self.get_image(bs)
                    file_name = generate_basename(
                        info['file_name'], {'%s': f'Shot{info["shot_num"]}', '%t': 'Time{read_time}', '%e': 'Energy{energy:.3f}J', '%h': 'HotSpot{hot_spot:.4f}Jcm-2', '%f': 'tiff', 'device_proxy': bs})
                    # the saving interval threshold has been enabled in server side.
                    # if info['shot_num'] == 1 or (info['time_interval'] > interval_threshold):
                    data.save(os.path.join(
                        info['cam_dir'], file_name))
                    logging.info("Shot {} taken for {} (size: {}) saved to {}".format(
                        info['shot_num'], info['shortname'],  {data.size}, {os.path.join(
                            info['cam_dir'], file_name)}))
                    if stitch:
                        adjusted_image = self.stretch_image(data_array)
                        info['images_to_stitch'][f'shot{info["shot_num"]}'] = adjusted_image
                        if sum([1 for one_cam in self.cam_info.values() if f'shot{info["shot_num"]}' in one_cam['images_to_stitch']]) == len(self.cam_info):
                            stitch_save_path = os.path.join(
                                self.dir, 'stitching', f'shot{info["shot_num"]}.tiff')
                            large_image_p = self.stitch_images(
                                f'shot{info["shot_num"]}')
                            large_image_p.save(stitch_save_path)
                            logging.info(
                                f"Shot {info['shot_num']} taken for stitching (size: {large_image_p.size}) saved to {stitch_save_path}")
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
                    (gap_y+tile_size_y)-0.5*gap_y), cam_name, fill="white", anchor="mm", font_size=20)
            del info['images_to_stitch'][image_name]
        # large_image_p.show()
        return large_image_p

    def termination(self, config_dict=None):
        logging.info('terminating...')
        if config_dict is None:
            config_dict = {'all': {"is_polling_periodically": True}}
        self.set_camera_configuration(
            config_dict=config_dict, saving=False)


# if __name__ == "__main__":
#     dt_string = datetime.now().strftime("%Y%m%d")
#     run_num = input('\nPlease input a run number: ')
#     save_dir = os.path.join(r'N:\2024\Qing_test', f'{dt_string}_run{run_num}')
#     # select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
#     select_cam_list = ['TA2-NearField', 'TA2-FarField']
#     daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
#     daq.set_camera_configuration()
#     daq.take_background()
