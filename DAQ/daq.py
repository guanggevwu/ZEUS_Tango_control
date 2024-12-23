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
import shutil
import matplotlib.pyplot as plt
from threading import Thread

if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.other import generate_basename

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, select_cam_list, dir='', debug=False, check_exist=True, thread_event=None, GUI=None):
        if GUI is None:
            self.logger = logging.getLogger(__name__).info
        else:
            self.GUI = GUI
            self.logger = GUI.insert_to_disabled
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
                self.cam_info[c]['user_defined_name'] = bs.user_defined_name
                self.cam_info[c]['cam_dir'] = os.path.join(
                    self.dir, self.cam_info[c]['user_defined_name'])
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
                        self.dir, self.cam_info[c]['user_defined_name']), exist_ok=True)
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

    def set_camera_configuration(self, config_dict=None, saving=True, default_config_dict=default_config_dict):
        if config_dict is None:
            config_dict = {}
        # list of user defined names of the cameras
        user_defined_name_list = [one_cam_dict['user_defined_name']
                                  for one_cam_dict in self.cam_info.values()]
        # retrieve selected camera configurations from the default configurations
        combined_config = {}
        # the overwrite priority is "specified camera in config_dict" > "all in config_dict" > "specified camera in default_config_dict" > "all in default_config_dict"
        for cam in user_defined_name_list:
            new_config = {}
            if "all" in default_config_dict:
                new_config.update(default_config_dict["all"])
            if cam in default_config_dict:
                new_config.update(default_config_dict.get(cam))
            if "all" in config_dict:
                new_config.update(config_dict["all"])
            if cam in config_dict:
                new_config.update(config_dict[cam])
            combined_config[cam] = new_config
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            # if the device name is found in combined_config, use it. if not, use "all" instead. Else, pass an empty dict.
            if bs.user_defined_name in combined_config:
                info['config_dict'] = combined_config[bs.user_defined_name]
            elif 'all' in config_dict:
                info['config_dict'] = combined_config['all']
            else:
                info['config_dict'] = dict()
            if 'basler' in bs.dev_name():
                bs.relax()
            for key, value in info['config_dict'].items():
                if hasattr(bs, key):
                    if key == "trigger_source":
                        setattr(bs, key, value)
                    elif getattr(bs, key) != value:
                        self.logger(
                            f"{info['user_defined_name']}/{key} is changed from {getattr(bs, key)} to {value}")
                        setattr(bs, key, value)

            # if the saving_format is not set in the configuration
            if ('saving_format' not in info['config_dict']):
                info['file_name'] = '%s.%f'
            else:
                info['file_name'] = info['config_dict']['saving_format']
        if saving:
            Key_list = ['model', 'format_pixel', "exposure", "gain",
                        "trigger_selector", "trigger_source"]
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
        data_PIL = Image.fromarray(bs.image.astype(f'uint{bits}'))
        if hasattr(bs, "image_with_MeV_mark"):
            data_array = bs.image_with_MeV_mark.astype(f'uint{bits}')
        else:
            data_array = bs.image.astype(f'uint{bits}')
        return data_PIL, data_array

    def stretch_image(self, current_image):
        adjusted_image = self.imadjust(current_image)
        if np.max(adjusted_image) != np.min(adjusted_image):
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
                self.logger(
                    f"Background for {info['user_defined_name']} is saved {data.size}")
                if stitch:
                    adjusted_image = self.stretch_image(data_array)
                    info['images_to_stitch']['background'] = adjusted_image
                    if sum([1 for one_cam in self.cam_info.values() if 'background' in one_cam['images_to_stitch']]) == len(self.cam_info):
                        back_image = self.stitch_images('background')
                        back_image.save(
                            os.path.join(self.dir, 'stitching', f'background.tiff'))
                        self.logger(
                            f"Background for stitching {back_image.size} is saved.")
            else:
                self.logger('Error when taking background image.')
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

    def acquisition(self, stitch=True, shot_start=1, shot_end=float('inf'), scan_table=None):
        '''
        Main acquisition function. Use external trigger and save data.
        '''
        scan_tango_device = {}
        if scan_table is not None:
            for regulator, value in scan_table.items():
                scan_tango_device[regulator] = tango.DeviceProxy(regulator)
                if shot_start<=len(scan_table[regulator]):
                    self.set_scan_value(scan_tango_device[regulator], scan_table[regulator], shot_start)
        self.logger('Waiting for a trigger...')
        xy_reader_count = 0
        if len(self.cam_info) < 2:
            stitch = False
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            bs.reset_number(shot_start-1)
            info['shot_num'] = shot_start
        while True:
            if self.thread_event is not None:
                if self.thread_event.is_set():
                    break
            for c, info in self.cam_info.items():
                bs = info['device_proxy']
                # when there is a short limit, the acquisition stops after the requested image numbers are reached.
                info['is_completed'] = False
                if info['shot_num'] > shot_end:
                    info['is_completed'] = True
                elif bs.is_new_image:
                    if 'basler' in bs.dev_name() or bs.data_type == "image":
                        data, data_array = self.get_image(bs)
                        file_name = generate_basename(
                            info['file_name'], {'%s': f'Shot{info["shot_num"]}', '%t': 'Time{read_time}', '%e': 'Energy{energy:.3f}J', '%h': 'HotSpot{hot_spot:.4f}Jcm-2', '%f': 'tiff', 'device_proxy': bs})
                        freezed_shot_number = info["shot_num"]
                        Thread(target=self.thread_saving,
                               args=(data, info, file_name, freezed_shot_number)).start()
                        add_number = 1
                        stitch_local = True
                    elif 'file_reader' in bs.dev_name() or bs.data_type == "xy":
                        file_name = generate_basename(
                            info['file_name'], {'%s': f'Shot{info["shot_num"]}', '%t': 'Time{read_time}', '%o': '{current_file}', '%f': 'csv', 'device_proxy': bs})
                        shutil.copy(os.path.join(bs.folder_path, bs.current_file), os.path.join(
                            info['cam_dir'], file_name))
                        xy_reader_count += 1
                        if xy_reader_count == bs.files_per_shot:
                            data_array = self.save_plot_data(bs.x, bs.y)
                            add_number = 1
                            xy_reader_count = 0
                            # For scope, it saves multiple files per shot. stitch_local set to True only every bs.files_per_shot.
                            stitch_local = True
                        else:
                            add_number = 0
                            stitch_local = False
                    if stitch and stitch_local:
                        adjusted_image = self.stretch_image(data_array)
                        info['images_to_stitch'][f'shot{info["shot_num"]}'] = adjusted_image
                        # check if the images to stitch are all available.
                        if sum([1 for one_cam in self.cam_info.values() if f'shot{info["shot_num"]}' in one_cam['images_to_stitch']]) == len(self.cam_info):
                            stitch_save_path = os.path.join(
                                self.dir, 'stitching', f'shot{info["shot_num"]}_{datetime.now().strftime("%H%M%S.%f")}.tiff')
                            large_image_p = self.stitch_images(
                                f'shot{info["shot_num"]}')
                            large_image_p.save(stitch_save_path)
                            self.logger(
                                f"Shot {info['shot_num']} for stitching {large_image_p.size} is saved.")
                    info['shot_num'] += add_number
                    # head to next scan point when all cameras completed a shot.
                    if all([i['shot_num']>=info['shot_num'] for i in self.cam_info.values()]):
                        self.logger(f"shot {info['shot_num']-1} is completed.")
                        if scan_table is not None:
                            for scan_device, dp in scan_tango_device.items():
                                self.set_scan_value(dp, scan_table[scan_device], info['shot_num'])                        
            if not False in [value['is_completed'] for value in self.cam_info.values()]:
                self.logger("All shots completed!")
                return

    def set_scan_value(self, device_proxy, value_list, shot_number):
        if shot_number<= len(value_list) and value_list[shot_number-1]:
            device_proxy.pressure_psi = float(value_list[shot_number-1])
            self.logger(f'{device_proxy.dev_name().split("/")[-1]} pressure set to {value_list[shot_number-1]}')
        else:
            self.logger(f'{device_proxy.dev_name().split("/")[-1]} pressure, empty scan value. It is {device_proxy.pressure_psi} psi.')

    def thread_saving(self, data, info, file_name, freezed_shot_number):
        data.save(os.path.join(info['cam_dir'], file_name))
        self.logger(
            f"Shot {freezed_shot_number} for {info['user_defined_name']} {data.size} is saved.")

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
            cam_name = info['user_defined_name']
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

    def save_plot_data(self, x, y):
        fig, ax = plt.subplots(1, 1)
        ax.plot(x, y)
        # If we haven't already shown or saved the plot, then we need to
        # draw the figure first...
        fig.canvas.draw()
        data = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        data = data.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        return data[:, :, 0]

    def termination(self, config_dict=None):
        if config_dict is None:
            config_dict = {'all': {"is_polling_periodically": True}}
        self.set_camera_configuration(
            config_dict=config_dict, saving=False, default_config_dict={})

# if __name__ == "__main__":
#     dt_string = datetime.now().strftime("%Y%m%d")
#     run_num = input('\nPlease input a run number: ')
#     save_dir = os.path.join(r'N:\2024\Qing_test', f'{dt_string}_run{run_num}')
#     # select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
#     select_cam_list = ['TA2-NearField', 'TA2-FarField']
#     daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
#     daq.set_camera_configuration()
#     daq.take_background()
