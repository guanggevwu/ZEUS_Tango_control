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
import platform
from config import default_config_dict
import shutil
import matplotlib.pyplot as plt
from threading import Thread
import csv
from playsound3 import playsound
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class Daq:
    def __init__(self, select_cam_list, dir='', debug=False, check_exist=True, thread_event=None, GUI=None):
        if GUI is None:
            self.logger = logging.getLogger(__name__).info
        else:
            # call the GUI logger
            self.GUI = GUI
            self.logger = GUI.insert_to_disabled
        # Structure of self.cam_info. The key is the full device name 'xx/xx/xx'. Each value is a dictionray.
        # The value dictionary has key-value pairs of ['device_proxy', tango.DeviceProxy()], ['user_defined_name', tango.DeviceProxy().user_defined_name], ['cam_dir', path_of_the_camera_data_folder:string], ['shot_number', shot_number:int]['images_to_stitch', images_to_stitch_dict:dictionary]
        # images_to_stitch_dict has key-value pairs of format [shot_number:string, image_to_stitch]. shot_number:string is "background", "shot1"... image_to_stitch is the adjust numpy image array.
        self.cam_info = defaultdict(dict)
        self.dir = dir
        if self.GUI.options['save_copy']:
            date = datetime.now().strftime("%Y%m%d")
            if platform.system() == 'Linux':
                self.hidden_dir = f"~/DAQ_hidden/{date}"
            elif platform.system() == 'Windows':
                self.hidden_dir = f"C:\\DAQ_hidden\\{date}"
            self.path_list = [self.dir, self.hidden_dir]
        else:
            self.path_list = [self.dir]
        self.select_cam_list = select_cam_list
        self.thread_event = thread_event
        Yes_for_all = False
        if not len(select_cam_list):
            raise Exception("Please select cameras!")
        for c in select_cam_list:
            try:
                bs = tango.DeviceProxy(c)
                bs.ping()
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
                for p in self.path_list:
                    if p:
                        os.makedirs(os.path.join(
                            p, self.cam_info[c]['user_defined_name']), exist_ok=True)
                        if self.GUI.options['stitch']:
                            os.makedirs(os.path.join(
                                p, 'stitching'), exist_ok=True)
                logging.info(f'Connected: {c}')
            except:
                if 'exception' in locals():
                    raise exception
                else:
                    raise Exception(f"{c} is not found!")
        self.debug = debug
        # atexit.register(self.termination)

    def set_camera_configuration(self, config_dict=None, saving=True, default_config_dict=default_config_dict):
        # list of user defined names of the cameras
        user_defined_name_list = [one_cam_dict['user_defined_name']
                                  for one_cam_dict in self.cam_info.values()]
        # retrieve selected camera configurations from the default configurations
        combined_config = {}
        # the overwrite priority is "specified camera in config_dict" > "all in config_dict" > "specified camera in default_config_dict" > "all in default_config_dict"
        # 2025/02/05 change that if a configuration is passed to config_dict, then use the configuration which is basically just change polling and image number. All other changes are made by GUI. Otherwise, use default in config.py.
        # Although the option that "use default config.py" in the GUI is removed, config_dict is stilled used in the termination function.
        for cam in user_defined_name_list:
            new_config = {}
            if not config_dict:
                if "all" in default_config_dict:
                    new_config.update(default_config_dict["all"])
                if cam in default_config_dict:
                    new_config.update(default_config_dict.get(cam))
            else:
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
            if bs.info().dev_class.lower() in ['basler', 'vimba']:
                bs.relax()
            elif bs.info().dev_class.lower() == 'filereader':
                bs.read_files()
            for key, value in info['config_dict'].items():
                if hasattr(bs, key):
                    try:
                        old_value = getattr(bs, key)
                        if key == "trigger_source" and old_value == value:
                            setattr(bs, key, value)
                        elif old_value != value:
                            setattr(bs, key, value)
                            # as "is_polling_periodically" is not an important information for the operators.
                            if key != "is_polling_periodically":
                                self.logger(
                                    f"{info['user_defined_name']}/{key} is changed from {old_value} to {value}")
                    except:
                        self.logger(
                            f"Failed to change {info['user_defined_name']}/{key} from {getattr(bs, key)} to {value}")
            # if the saving_format is not set in the configuration
            if ('saving_format' not in info['config_dict']):
                info['file_name'] = '%s'
            else:
                info['file_name'] = info['config_dict']['saving_format']
        if saving:
            Key_list = ['model', 'format_pixel', "exposure", "gain",
                        "trigger_selector", "trigger_source"]
            full_configuration = dict()
            for c, info in self.cam_info.items():
                if info['device_proxy'].info().dev_class.lower() in ['basler', 'vimba']:
                    full_configuration[c] = {key: getattr(
                        info['device_proxy'], key, None) for key in Key_list}
            json_object = json.dumps(full_configuration)
            for p in self.path_list:
                os.makedirs(p, exist_ok=True)
                with open(os.path.join(p, "settings.json"), "w+") as settings_File:
                    settings_File.write(json_object)

    def get_image(self, bs):
        bits = ''.join([i for i in bs.format_pixel if i.isdigit()])
        if getattr(bs, 'format_pixel', '').lower() == "rgb8":
            image = np.dstack((bs.image_r, bs.image_g, bs.image_b))
        else:
            image = bs.image
        if int(bits) > 8:
            bits = '16'
        data_PIL = Image.fromarray(image.astype(f'uint{bits}'))
        if hasattr(bs, "image_with_MeV_mark"):
            data_array = bs.image_with_MeV_mark.astype(f'uint{bits}')
        else:
            data_array = image.astype(f'uint{bits}')
        return data_PIL, data_array

    def stretch_image(self, current_image):
        adjusted_image = self.imadjust(current_image)
        if np.max(adjusted_image) != np.min(adjusted_image):
            adjusted_image = (adjusted_image - np.min(adjusted_image)) / \
                (np.max(adjusted_image) - np.min(adjusted_image))*255
        return adjusted_image

    def take_background(self, stitch=True):
        '''take a background image
        haven't updated it for a while. For example, hidden save folder.
        '''
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            if bs.info().dev_class.lower() in ['basler', 'vimba']:
                trigger_source = bs.trigger_source
                bs.trigger_source = "software"
                time.sleep(0.5)
                bs.send_software_trigger()
                time.sleep(1)
            if bs.is_new_image:
                data, data_array = self.get_image(bs)
                file_name = self.generate_file_name(info, bs, shoot=False)
                file_name = file_name.replace('%f', 'tiff')
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
            if bs.info().dev_class.lower() in ['basler', 'vimba']:
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
            if info['device_proxy'].info().dev_class.lower() in ['basler', 'vimba']:
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
        # set scan value
        # self.scan_attr_proxies is a dictionary. Its key is a string device/attr and its value is the attribute proxy
        self.scan_attr_proxies = {}
        if self.GUI.options['scan'] and scan_table and any(scan_table.values()):
            self.scan_table = scan_table

            for device_attr_name, value in self.scan_table.items():
                if not hasattr(self, "scan_shot_range"):
                    self.scan_shot_range = range(
                        self.GUI.row_shotnum, self.GUI.row_shotnum + len(value))
                self.scan_attr_proxies[device_attr_name] = tango.AttributeProxy(
                    device_attr_name)
                if shot_start in self.scan_shot_range:
                    self.set_scan_value(
                        self.scan_attr_proxies[device_attr_name], value, shot_start)
        self.scalars = {attr: tango.AttributeProxy(
            attr) for attr in self.GUI.checked_savable_attributes}
        resulting_fps_dict = {}
        if len(self.cam_info) < 2:
            stitch = False
        # compare shot number of each camera with self.current_shot_for_all_cam to determine if it is time to stitch and inform "shot xx is compeleted"
        # reset shot number and set the start shot number
        self.current_shot_for_all_cam = shot_start
        for c, info in self.cam_info.items():
            bs = info['device_proxy']
            if hasattr(bs, 'reset_number'):
                bs.reset_number(shot_start-1)
            info['shot_num'] = shot_start
            # when there is a shot limit, the acquisition stops after the requested image numbers are reached.
            info['is_completed'] = False
            if hasattr(bs, 'resulting_fps'):
                resulting_fps_dict[bs.user_defined_name] = (
                    f'{bs.bandwidth:.1f} {bs.get_attribute_config("bandwidth").unit}', bs.resulting_fps)
        if resulting_fps_dict:
            self.logger(
                f'Bandwidth and resulting fps: {resulting_fps_dict}. Triggering rate is limited by the slowest camera.')
        threads = []
        for c, info in self.cam_info.items():
            t = Thread(target=self.thread_acquire_data, args=[
                       info, stitch, shot_end,], daemon=True)
            threads.append(t)
            t.start()
        t_shot_completion = Thread(target=self.thread_stitch_and_go_to_next_scan_point, args=[
                                   stitch, scan_table], daemon=True)
        threads.append(t_shot_completion)
        t_shot_completion.start()
        self.logger('Waiting for a trigger...')
        for t in threads:
            t.join()
        # acquisition

    def thread_acquire_data(self, info, stitch, shot_end,):
        try:
            xy_reader_count = 0
            while True:
                if self.thread_event is not None and self.thread_event.is_set():
                    # self.logger(
                    #     f"{info['user_defined_name']} acquisition thread stopped.")
                    break
                bs = info['device_proxy']
                # self.logger(f'{bs.dev_name()}, {info["shot_num"]}, start')
                t0 = datetime.now()
                if info['shot_num'] > shot_end:
                    info['is_completed'] = True
                elif bs.is_new_image:
                    if (bs.info().dev_class.lower() in ['basler', 'vimba']) or (bs.info().dev_class.lower() == 'filereader' and bs.data_type == "image"):
                        data, data_array = self.get_image(bs)
                        file_name = self.generate_file_name(info, bs)
                        file_name = file_name.replace('%f', 'tiff')
                        # self.logger(
                        #     f"It takes {datetime.now()-t0} to acquire {info['user_defined_name']} {info['shot_num']}.")
                        save_path = os.path.join(info['cam_dir'], file_name)
                        message = f"Shot {info['shot_num']} for {info['user_defined_name']} {data.size} is saved."
                        Thread(target=self.thread_saving,
                               args=(data, save_path, message)).start()
                        add_number = 1
                        # For scope, it saves multiple files per shot. stitch_local set to True only every bs.files_per_shot.
                        stitch_local = True
                    elif bs.info().dev_class.lower() == 'filereader' and bs.data_type == "xy":
                        file_name = self.generate_file_name(info, bs)
                        file_name = file_name.replace('%f', 'csv')
                        source_path = os.path.join(
                            bs.folder_path, bs.current_file)
                        destination_path = os.path.join(
                            info['cam_dir'], file_name)
                        message = f"Shot {info['shot_num']} for {info['user_defined_name']} is saved."
                        Thread(target=self.thread_copy, args=(
                            source_path, destination_path, message)).start()
                        xy_reader_count += 1
                        if xy_reader_count == bs.files_per_shot:
                            data_array = self.save_plot_data(bs.x, bs.y)
                            add_number = 1
                            xy_reader_count = 0
                            stitch_local = True
                        else:
                            add_number = 0
                            stitch_local = False
                    if stitch and stitch_local:
                        if getattr(bs, 'format_pixel', '').lower() == "rgb8":
                            data_array = 0.299 * \
                                data_array[:, :, 0] + 0.587 * data_array[:,
                                                                         :, 1] + 0.114 * data_array[:, :, 2]
                        adjusted_image = self.stretch_image(data_array)
                        info['images_to_stitch'][f'shot{info["shot_num"]}'] = adjusted_image
                    info['shot_num'] += add_number
                    # self.logger(
                    #     f"It takes {datetime.now()-t0} to save {info['user_defined_name']} {info['shot_num']-1} out of thread.")
        except Exception as e:
            self.logger(
                f'Error in {info["user_defined_name"]} "thread_acquire_data" thread: {e}', 'red_text')

    def thread_stitch_and_go_to_next_scan_point(self, stitch, scan_table):
        try:
            while True:
                if self.thread_event is not None and self.thread_event.is_set():
                    # self.logger(f'stitching and scan thread stopped.')
                    break
                # t0 = datetime.now()
                # check if all cameras have a new shot
                if all([i['shot_num'] > self.current_shot_for_all_cam for i in self.cam_info.values()]):
                    if stitch:
                        stitch_save_path = os.path.join(
                            self.dir, 'stitching', f'shot{self.current_shot_for_all_cam}_{datetime.now().strftime("%H%M%S.%f")}.tiff')
                        large_image_p = self.stitch_images(
                            f'shot{self.current_shot_for_all_cam}')
                        message = f"Shot {self.current_shot_for_all_cam} for stitching is saved."
                        Thread(target=self.thread_saving, args=(
                            large_image_p, stitch_save_path, message)).start()
                        # self.logger(
                        #     f"Shot {self.current_shot_for_all_cam} for stitching {large_image_p.size} is queued.")
                        # self.logger(f"It takes {datetime.now() - t0} to save out of thread.")
                    self.current_shot_for_all_cam += 1
                    self.logger(
                        f"Shot {self.current_shot_for_all_cam-1} is completed.", 'green_text')
                    playsound(os.path.join(os.path.dirname(__file__), 'media',
                                           'sound', 'shot_completion_1.mp3'), block=False)
                    # send plasma mirror ready signal
                    if not self.GUI.options['use_plasma_mirror']:
                        self.GUI.send_message_to_laser_side('TA2_ready')
                    # remove highlight in scan module window
                    if hasattr(self.GUI, 'scan_window') and self.GUI.scan_window.winfo_exists() and self.GUI.scan_window.tree.tag_has(f'#{self.current_shot_for_all_cam-1}'):
                        self.GUI.scan_window.tree.tag_configure(
                            f'#{self.current_shot_for_all_cam-1}', background='white')
                    # save scala data
                    if self.GUI.options["save_metadata"]:
                        self.csv_header = ['shot_number', 'time']
                        self.save_scalars(self.current_shot_for_all_cam)
                    if self.GUI.options["scan"] and scan_table is not None and hasattr(self, "scan_shot_range") and self.current_shot_for_all_cam in self.scan_shot_range:
                        for device_attr_name, ap in self.scan_attr_proxies.items():
                            self.set_scan_value(
                                ap, self.scan_table[device_attr_name], self.current_shot_for_all_cam)

                if not False in [value['is_completed'] for value in self.cam_info.values()]:
                    self.logger("All shots completed!")
                    self.thread_event.set()
                    return
                time.sleep(0.3)
        except Exception as e:
            self.logger(
                f'Error in "thread_stitch_and_go_to_next_scan_point" thread: {e}', 'red_text')

    def generate_file_name(self, info, bs, shoot=True):
        rep = info['file_name']
        if '%s' in rep:
            if not shoot:
                rep = rep.replace('%s', 'Background')
            else:
                rep = rep.replace('%s', f'Shot{info["shot_num"]}')
        if '%t' in rep:
            rep = rep.replace('%t', f'Time{bs.read_time}')
        if '%e' in rep:
            rep = rep.replace('%e', f'Energy{bs.energy:.3f}J')
        if '%h' in rep:
            rep = rep.replace('%h', f'HotSpot{bs.hot_spot:.4f}Jcm-2')
        # if '%id' in rep:
        #     rep = rep.replace('%id', f'id{self.labview.shot_id}')
        if '%o' in rep:
            rep = rep.replace('%o', f'{bs.current_file}')
        return rep

    def set_scan_value(self, attr_proxy, value_list: list, shot_number: int):
        """
        Set the value for an attribute. Highlight the current row.

        :param attr_proxy: Tango attribute
        :param value_list: value list for this attribute
        :param shot_number: the shot number to be set
        :returns: None
        """

        if value_list[self.scan_shot_range.index(shot_number)]:
            value = value_list[self.scan_shot_range.index(shot_number)]
            '''
            AttributeProxy.get_config().date_type returns an int representing the data type. It looks like the mapping is:
            0: tango.CmdArgType.DEV_VOID (No data)
            1: tango.CmdArgType.DEV_BOOLEAN
            2: tango.CmdArgType.DEV_SHORT
            3: tango.CmdArgType.DEV_LONG
            4: tango.CmdArgType.DEV_FLOAT
            5: tango.CmdArgType.DEV_DOUBLE
            6: tango.CmdArgType.DEV_USHORT
            7: tango.CmdArgType.DEV_ULONG
            8: tango.CmdArgType.DEV_STRING
            9: tango.CmdArgType.DEV_VAR_SHORT_ARRAY (1D Array)
            10: tango.CmdArgType.DEV_VAR_LONG_ARRAY (1D Array)
            11: tango.CmdArgType.DEV_VAR_FLOAT_ARRAY (1D Array)
            12: tango.CmdArgType.DEV_VAR_DOUBLE_ARRAY (1D Array)
            13: tango.CmdArgType.DEV_VAR_USHORT_ARRAY (1D Array)
            14: tango.CmdArgType.DEV_VAR_ULONG_ARRAY (1D Array)
            15: tango.CmdArgType.DEV_VAR_STRING_ARRAY (1D Array)
            16: tango.CmdArgType.DEV_VAR_LONG64_ARRAY (1D Array)
            17: tango.CmdArgType.DEV_VAR_ULONG64_ARRAY (1D Array)
            18: tango.CmdArgType.DEV_LONG64
            19: tango.CmdArgType.DEV_ULONG64
            20: tango.CmdArgType.DEV_ENCODED (e.g., JPEG, PNG, or custom) 
            '''
            data_type_map = {1: bool, 8: str}
            if attr_proxy.get_config().data_type in data_type_map:
                convert_func = data_type_map[attr_proxy.get_config().data_type]
            else:
                convert_func = float
            attr_proxy.write(convert_func(value))
            self.logger(
                f'Shot {shot_number}. {attr_proxy.get_device_proxy().dev_name().split("/")[-1]}/{attr_proxy.name()}: {value}')
        else:
            self.logger(
                f'Shot {shot_number}. {attr_proxy.get_device_proxy().dev_name().split("/")[-1]}/{attr_proxy.name()}: empty scan value. It was {attr_proxy.read().value} {attr_proxy.get_config().unit}.')
        self.GUI.current_shot_number = shot_number
        if self.GUI.scan_window.winfo_exists():
            self.GUI.scan_window.tree.tag_configure(
                f'#{shot_number}', background='yellow')

    def save_scalars(self, shot_number,):
        self.csv_header.extend(self.scalars.keys())
        for p in self.path_list:
            with open(os.path.join(p, 'scalars.csv'), 'a+', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.csv_header)
                csvfile.seek(0)
                current_header = csvfile.readline()
                if (not current_header) or (current_header.strip() != ','.join(self.csv_header)):
                    writer.writeheader()
                    csvfile.seek(0, os.SEEK_END)
                data_to_write = {'shot_number': shot_number-1,
                                 'time': datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")}
                other_data = {
                    key: f'{value.read().value: .6g}{value.get_config().unit}' for key, value in self.scalars.items()}
                data_to_write.update(other_data)
                writer.writerow(data_to_write)
        self.logger(f'Write scalars: {other_data}')

    def thread_saving(self, data, save_path, message):
        try:
            data.save(save_path)
            self.logger(message)
            if self.GUI.options['save_copy']:
                data.save(save_path.replace(self.dir, self.hidden_dir, 1))
        except Exception as e:
            self.logger(f"Error saving file: {e}", 'red_text')

    def thread_copy(self, source_path, destination_path, message):
        try:
            shutil.copy(source_path, destination_path)
            self.logger(message)
            if self.GUI.options['save_copy']:
                shutil.copy(source_path, destination_path.replace(
                    self.dir, self.hidden_dir, 1))
        except Exception as e:
            self.logger(f"Error copying file: {e}", 'red_text')

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

    def __del__(self):
        logging.info("destroying Daq() in daq.py")
        config_dict = {'all': {"is_polling_periodically": True}}
        self.set_camera_configuration(
            config_dict=config_dict, saving=False, default_config_dict={})
