from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import tango
import numpy as np
from datetime import datetime
import os
import logging
from daq import Daq
import subprocess
import signal
import platform
import atexit
from threading import Thread, Event
import json
import platform
import ctypes
import csv
from collections import defaultdict

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO)


class DaqGUI:
    def __init__(self, root):
        self.db = tango.Database()
        self.root_path = os.path.dirname(os.path.dirname(__file__))
        # self.current_shot_numbern is for highlight function. O indicate no highlight before start acquisition.
        self.current_shot_number = 0
        # self.row_shotnum is for define start shot on scan list.
        self.row_shotnum = 1
        if platform.system() == 'Linux':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'Scripts', 'python.exe')
        self.client_GUI = dict()
        self.acquisition = {'status': False, 'is_completed': False}

        root.title(f"ZEUS DAQ GUI")

        s = ttk.Style()
        s.theme_use('alt')

        self.font_large = 20
        self.font_mid = 15
        self.font_small = 12
        s.configure('Sty1.TLabelframe.Label',
                    foreground="blue", font=('Times', self.font_large))
        style_widgets = ['TButton', 'TLabel',
                         'TCombobox']

        for w in style_widgets:
            s.configure(f'Sty1.{w}',
                        font=('Helvetica', self.font_mid))
        s.configure('Sty1.TCheckbutton', font=(
            'Helvetica', self.font_small))
        s.configure('Sty2_offline.TButton', font=(
            'Helvetica', self.font_mid), background='#85929e')
        s.configure('Sty2_connecting.TButton', font=(
            'Helvetica', self.font_mid), background='yellow')
        s.configure('Sty2_online.TButton', font=(
            'Helvetica', self.font_mid), background='#5dade2')
        s.configure('Sty2_client_offline.TButton', font=(
            'Helvetica', self.font_mid), background='#85929e')
        s.configure('Sty2_client_online.TButton', font=(
            'Helvetica', self.font_mid), background='#52be80')
        s.configure('Sty3_start.TButton', font=(
            'Helvetica', self.font_mid), background='green')
        s.configure('Sty3_stop.TButton', font=(
            'Helvetica', self.font_mid), background='red')
        s.configure("Treeview", font=('Helvetica', self.font_mid))
        s.configure('Treeview.Heading', font=(
            'Helvetica', self.font_small), background="PowderBlue")
        # frame1 = ttk.Frame(root, padding="3 3 12 12")
        # frame1.grid(column=0, row=0, sticky=(N, W, E, S))
        # root.columnconfigure(0, weight=1)
        # root.rowconfigure(0, weight=1)

        pad_widget = "0 0 0 10"
        # ---------------------frame 1

        self.frame1 = ttk.Labelframe(
            root, text='Devices', padding=pad_widget, style='Sty1.TLabelframe')
        self.frame1.grid(column=0, row=0, sticky=(N, W, E, S))
        ttk.Button(self.frame1, text='Select', command=self.open_device_list, style='Sty1.TButton').grid(
            column=0, row=0, sticky='W')
        self.client_GUI['button'] = ttk.Button(
            self.frame1, text='Device GUI', command=self.start_device_GUI, style='Sty2_client_offline.TButton')
        self.client_GUI['button'].grid(column=1, row=0, sticky='W')
        self.device_row, self.selected_device_per_row = 1, 4

        # ---------------------frame 2
        self.frame2 = ttk.Labelframe(
            root, text='Options', padding=pad_widget, style='Sty1.TLabelframe')
        self.frame2.grid(column=0, row=1, sticky=(N, W, E, S))

        self.frame2_checkbutton_content = {'overwrite_config': {'text': 'Use the config.py configuration for the cameras', 'init_status': True},  'save_config': {'text': 'Save the configurations to a file', 'init_status': True}, 'background_image': {
            'text': 'Save backgrounds image before acquisition', 'init_status': True}, 'stitch': {'text': 'Stitch the images from multiple cameras and save a large image', 'init_status': True}, 'laser_shot_id': {'text': 'save shot id table', 'init_status': False}, }

        for idx, (key, value) in enumerate(self.frame2_checkbutton_content.items()):
            checkbox_var = BooleanVar(value=value['init_status'])
            checkbox = ttk.Checkbutton(self.frame2, text=value['text'],
                                       variable=checkbox_var, style='Sty1.TCheckbutton')
            checkbox.grid(
                column=0, row=idx, sticky=W)
            value['var'] = checkbox_var

        # ---------------------frame 3

        self.frame3 = ttk.Labelframe(
            root, text='Acquisition', padding=pad_widget, style='Sty1.TLabelframe')
        self.frame3.grid(column=0, row=2, sticky=(N, W, E, S))
        ttk.Label(self.frame3, text='Save path:', font=(
            'Helvetica', int(self.font_mid*0.75))).grid(
            column=0, row=0, sticky='W')
        # dt_string = datetime.now().strftime("%Y%m%d")
        self.path_var = StringVar()
        ttk.Entry(self.frame3, textvariable=self.path_var, font=(
            'Helvetica', int(self.font_mid*0.75)), width=60).grid(
            column=1, row=0, columnspan=4, sticky='W')

        ttk.Label(self.frame3, text='Start', font=(
            'Helvetica', int(self.font_mid*0.75))).grid(
            column=0, row=1, sticky='W')
        self.shot_start_var = IntVar(value=1)
        ttk.Entry(self.frame3, textvariable=self.shot_start_var, font=(
            'Helvetica', int(self.font_mid*0.75)), width=10).grid(
            column=1, row=1, sticky='W')

        ttk.Label(self.frame3, text='End', font=(
            'Helvetica', int(self.font_mid*0.75))).grid(
            column=2, row=1, sticky='W')
        self.shot_end_var = IntVar(value=9999)
        ttk.Entry(self.frame3, textvariable=self.shot_end_var, font=(
            'Helvetica', int(self.font_mid*0.75)), width=10).grid(
            column=3, row=1, sticky='W')
        ttk.Button(self.frame3, text='Scan', command=self.open_scan_list, style='Sty1.TButton').grid(
            column=4, row=1, sticky='W')
        self.acquisition['button'] = ttk.Button(
            self.frame3, text='Start', command=self.toggle_acquisition, style='Sty3_start.TButton')
        self.acquisition['button'].grid(
            column=0, row=2, columnspan=5, sticky='WE')

        self.frame4 = ttk.Labelframe(
            root, text='Logging', padding=pad_widget, style='Sty1.TLabelframe')
        self.frame4.grid(column=0, row=3, sticky=(N, W, E, S))
        self.t = Text(self.frame4, width=70, height=20, font=(
            'Helvetica', int(self.font_mid*0.75)), wrap=WORD)
        self.t.tag_config("red_text", foreground="red")
        self.t.tag_config("green_text", foreground="green")
        self.t.grid(column=0, row=0, sticky=W)
        self.insert_to_disabled("DAQ GUI is started.")
        sb = ttk.Scrollbar(self.frame4,
                           orient='vertical',
                           command=self.t.yview)

        sb.grid(column=1, row=0, sticky=NS)
        self.t['yscrollcommand'] = sb.set
        self.pad_space(self.frame1)
        self.pad_space(self.frame2)
        self.pad_space(self.frame3)
        self.pad_space(self.frame4)

        self.init_settings()

    def init_settings(self):
        # self.selected_devices is a dictionary. Key is the device name, value is another dictionary. In the sub-dictionary, the keys are "checkbutton" and "server_pid".
        self.init_file_path = os.path.join(
            os.path.dirname(__file__), 'init.json')
        self.class_name = ['Basler', 'FileReader', 'Vimba']
        self.device_names_in_db = []
        for c in self.class_name:
            self.device_names_in_db.extend(self.db.get_device_name('*', c))
        if os.path.isfile(self.init_file_path) and os.stat(self.init_file_path).st_size:
            with open(self.init_file_path) as jsonfile:
                self.init_dict = json.load(jsonfile)
                self.selected_devices = self.init_dict['selected_devices'] if 'selected_devices' in self.init_dict else dict(
                )
                self.selected_devices = {key: value for key, value in self.selected_devices.items(
                ) if key in self.device_names_in_db}
                self.options = self.init_dict['options'] if 'options' in self.init_dict and self.init_dict['options'] is not None else dict(
                )
                self.path_var.set(
                    self.init_dict['save_path']) if "save_path" in self.init_dict else ''

                for key, value in self.options.items():
                    if key in self.frame2_checkbutton_content:
                        self.frame2_checkbutton_content[key]['var'].set(value)
        else:
            self.selected_devices = dict()
            self.options = None
        for key in self.selected_devices:
            self.update_selected_devices(key, BooleanVar(value=True))

    def pad_space(self, frame):
        for child in frame.winfo_children():
            child.grid_configure(padx=[self.font_mid, 0], pady=3)

    def open_device_list(self):
        if not (hasattr(self, "device_list_window") and self.device_list_window.winfo_exists()):
            self.device_list_window = DeviceListWindow(
                update_selected_devices=self.update_selected_devices, selected_devices=self.selected_devices, device_names_in_db=self.device_names_in_db)
            self.device_list_window.title("Device List")
        self.device_list_window.attributes('-topmost', True)
        self.device_list_window.attributes('-topmost', False)

    def open_scan_list(self):
        if not (hasattr(self, "scan_window") and self.scan_window.winfo_exists()):
            self.scan_window = ScanWindow(self)
            self.scan_window.title("Scan Module")
        self.scan_window.attributes('-topmost', True)
        self.scan_window.attributes('-topmost', False)

    def connect_to_device(self, device_name):
        if 'server_pid' not in self.selected_devices[device_name]:
            device_class = self.db.get_device_info(
                device_name).class_name
            device_instance = self.db.get_device_info(
                device_name).ds_full_name.split('/')[-1]
            class_folder = os.path.join(
                self.root_path, device_class)
            script_path = os.path.join(
                class_folder, [i for i in os.listdir(class_folder) if 'server' in i][0])
            p = subprocess.Popen(
                [f'{self.python_path}', f'{script_path}', device_instance])
            self.selected_devices[device_name]['server_pid'] = p.pid
            self.selected_devices[device_name]['checkbutton']['style'] = 'Sty2_connecting.TButton'
            self.insert_to_disabled(f'Connecting {device_name}...')
            # Thread(target=self.check_device_server_status,
            #        args=(device_name,)).start()
            # self.check_device_server_status(device_name)
            self.selected_devices[device_name]['connection_try_times'] = 0
            root.after(
                3000, lambda: self.check_device_server_status(device_name))
        else:
            self.kill_device_server(device_name)

    def kill_device_server(self, device_name):
        try:
            os.kill(self.selected_devices[device_name]
                    ['server_pid'], signal.SIGTERM)
        except OSError:
            self.insert_to_disabled(
                f"{self.selected_devices[device_name]['server_pid']}  doesn't exist.")
        del self.selected_devices[device_name]['server_pid']
        del self.selected_devices[device_name]['connection_try_times']
        self.selected_devices[device_name]['checkbutton']['style'] = 'Sty2_offline.TButton'
        self.insert_to_disabled(f'{device_name} server is killed.')

    def check_device_server_status(self, device_name):
        if 'connection_try_times' not in self.selected_devices[device_name]:
            return
        self.selected_devices[device_name]['connection_try_times'] += 1
        try:
            dp = tango.DeviceProxy(device_name)
            dp.ping()
            self.selected_devices[device_name]['checkbutton']['style'] = 'Sty2_online.TButton'
            self.insert_to_disabled(f'{device_name} is connected.')
        except (tango.DevFailed, tango.ConnectionFailed) as e:
            if self.selected_devices[device_name]['connection_try_times'] >= 5:
                if type(e) is tango.DevFailed:
                    self.insert_to_disabled(
                        f'Type: {type(e)}. Check if {device_name} exists in the data base.')
                elif type(e) is tango.ConnectionFailed:
                    self.insert_to_disabled(
                        f'Type: {type(e)}. Check if {device_name} server is started.')
                self.kill_device_server(device_name)
            else:
                root.after(
                    3000, lambda: self.check_device_server_status(device_name))

    def start_device_GUI(self):
        if 'client_pid' not in self.client_GUI:
            if len(self.selected_devices) == 0:
                messagebox.showinfo(message='Please select devices!')
                return
            class_folder = os.path.join(
                self.root_path, 'Basler')
            script_path = os.path.join(
                class_folder, [i for i in os.listdir(class_folder) if 'GUI' in i][0])
            p = subprocess.Popen(
                [f'{self.python_path}', f'{script_path}', *[i for i in self.selected_devices]])
            self.client_GUI['client_pid'] = p.pid
            self.client_GUI['button']['style'] = 'Sty2_client_online.TButton'
        else:
            try:
                os.kill(self.client_GUI['client_pid'], signal.SIGTERM)
            except OSError:
                self.insert_to_disabled(
                    'GUI was already killed somewhere else. Ignore.')
            del self.client_GUI['client_pid']
            self.client_GUI['button']['style'] = 'Sty2_client_offline.TButton'
            self.insert_to_disabled(f'Client GUI is killed.')

    def terminate(self):
        for key, value in self.selected_devices.items():
            if 'server_pid' in value:
                os.kill(value['server_pid'], signal.SIGTERM)
            if 'client_pid' in value:
                os.kill(value['client_pid'], signal.SIGTERM)
        logging.info(
            "Terminate. All processes are killed.")

    def update_selected_devices(self, device_name, checkbox_var):
        if checkbox_var.get():
            device_button = ttk.Button(
                self.frame1, command=lambda device_name=device_name: self.connect_to_device(device_name), text=device_name.split('/')[-1], style='Sty2_offline.TButton')
            device_button.grid(
                column=len(self.selected_devices) % self.selected_device_per_row, row=self.device_row+int(len(self.selected_devices)/self.selected_device_per_row), sticky='W')
            self.selected_devices[device_name] = dict()
            self.selected_devices[device_name]['checkbutton'] = device_button
        elif 'server_pid' in self.selected_devices[device_name]:
            checkbox_var.set(True)
            messagebox.showinfo(
                message='Please disconnect the selected device first!')
        else:
            self.selected_devices[device_name]['checkbutton'].destroy()
            del self.selected_devices[device_name]
        for idx, value in enumerate(self.selected_devices.values()):
            if value is not None:
                value['checkbutton'].grid(
                    column=idx % self.selected_device_per_row, row=self.device_row+int(idx/self.selected_device_per_row), sticky='W')
        self.pad_space(self.frame1)

    def toggle_acquisition(self):
        if self.acquisition['status']:
            self.my_event.set()
            self.acquisition['status'] = False
            self.acquisition['button']['style'] = 'Sty3_start.TButton'
            self.acquisition['button']['text'] = 'Start'
            self.daq.termination()
            self.insert_to_disabled("Stopped acquisition.", 'red_text')
        else:
            self.acquisition['status'] = True
            self.acquisition['is_completed'] = False
            self.my_event = Event()
            Thread(target=self.start_acquisition).start()
            self.acquisition['button']['style'] = 'Sty3_stop.TButton'
            self.acquisition['button']['text'] = 'Stop'
            self.insert_to_disabled(
                "Started acquisition in a new thread.", 'green_text')

    def start_acquisition(self):
        self.options = {
            "overwrite_config": self.frame2_checkbutton_content['overwrite_config']['var'].get(),
            "save_config": self.frame2_checkbutton_content['save_config']['var'].get(),
            "background_image": self.frame2_checkbutton_content['background_image']['var'].get(),
            "stitch": self.frame2_checkbutton_content['stitch']['var'].get(),
            "laser_shot_id": self.frame2_checkbutton_content['laser_shot_id']['var'].get()
        }
        with open(self.init_file_path, 'w') as jsonfile:
            json.dump({"selected_devices": {key: None for key in self.selected_devices}, "options": self.options, "save_path": self.path_var.get()},
                      jsonfile)
        # if the checkbox is checked, then we use the config saved in config.py file and we pass None here. If it is unchecked, then we pass the basic configuration and ignore the configuration in the file.
        overwrite_config = None if self.options["overwrite_config"] else {"all": {
            "repetition": self.shot_end_var.get()-self.shot_start_var.get()+1, "is_polling_periodically": False, "trigger_source": "External", }}
        self.daq = Daq(self.selected_devices,
                       dir=self.path_var.get(), thread_event=self.my_event, check_exist=False, GUI=self)
        '''
        # dont confirm at the moment. Maybe add it back after adding the file format setting.
        self.Yes_for_all = False
        for c in self.selected_devices:
            cam_dir = os.path.join(
                self.path_var.get(), c.split('/')[-1])
            if not self.Yes_for_all and cam_dir:
                files_num = sum([len(files)
                                for r, d, files in os.walk(cam_dir)])
                if files_num:
                    answer = messagebox.askyesno(
                        message=f'{cam_dir} has {files_num} files in it. Are you sure you want to overwrite?', icon='question', title='Install')
                    if not answer:
                        self.acquisition['status'] = False
                        self.acquisition['button']['style'] = 'Sty3_start.TButton'
                        self.acquisition['button']['text'] = 'Start'
                        return
        '''
        self.daq.set_camera_configuration(
            config_dict=overwrite_config, saving=self.options['save_config'])
        if self.options['background_image']:
            self.daq.take_background(stitch=self.options['stitch'])
        scan_table = self.scan_window.scan_table if hasattr(
            self, 'scan_window') else None
        self.daq.acquisition(
            shot_start=self.shot_start_var.get(), shot_end=self.shot_end_var.get(), stitch=self.options['stitch'], laser_shot_id=self.options['laser_shot_id'], scan_table=scan_table)
        if not self.my_event.is_set():
            self.toggle_acquisition()

    def insert_to_disabled(self, text, tag_config=None):
        time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        logging.info(text)
        self.t['state'] = 'normal'
        self.t.insert(END, f'{time}, {text}\n', tag_config)
        self.t.see("end")
        self.t['state'] = 'disabled'


class DeviceListWindow(Toplevel):
    def __init__(self, update_selected_devices, selected_devices, device_names_in_db):
        self.update_selected_devices = update_selected_devices
        self.selected_devices = selected_devices
        self.device_names_in_db = device_names_in_db
        super().__init__(master=root)
        newframe1 = ttk.Frame(self)
        newframe1.grid(column=0, row=0, columnspan=1, sticky=(N, W, E, S))
        item_each_row = 3
        checkboxes = dict()
        for idx, device_name in enumerate(self.device_names_in_db):
            row, col = int(idx/item_each_row)+1, idx % item_each_row
            checkbox_var = BooleanVar(
                value=True) if device_name in self.selected_devices else BooleanVar(value=False)
            checkbox = ttk.Checkbutton(newframe1, text=device_name, command=lambda device_name=device_name, checkbox_var=checkbox_var: self.update_selected_devices(device_name, checkbox_var),
                                       variable=checkbox_var, style='Sty1.TCheckbutton')
            checkbox.grid(
                column=col, row=row, sticky=W)
            checkboxes[device_name] = checkbox_var

        for child in newframe1.winfo_children():
            child.grid_configure(padx=[0, 0], pady=5)


class ScanWindow(Toplevel):
    def __init__(self, parent):
        super().__init__(master=root)
        self.parent = parent
        pad_widget = "10 0 0 10"
        self.scan_frame1 = ttk.Labelframe(
            self, text='Scannable Device', padding=pad_widget, style='Sty1.TLabelframe')
        self.scan_frame1.grid(column=0, row=0, columnspan=2, sticky=W)
        self.scan_frame2 = ttk.Labelframe(
            self, text='Scan Table', padding=pad_widget, style='Sty1.TLabelframe')
        self.scan_frame2.grid(column=0, row=1, rowspan=2, sticky=W)
        self.scan_frame3 = ttk.Labelframe(
            self, text='Starting shot number', padding=pad_widget, style='Sty1.TLabelframe')
        self.scan_frame3.grid(column=1, row=1, sticky=W)
        self.scan_frame4 = ttk.Labelframe(
            self, text='Input', padding=pad_widget, style='Sty1.TLabelframe')
        self.scan_frame4.grid(column=1, row=2, sticky=W)
        self.item_each_row = 4
        # getting scannable device from db and manually specify the attr name
        self.scannable_list = [
            i+'/pressure_psi' for i in self.parent.db.get_device_name('*', "GXRegulator")] + [
            i+f'/ax{axis}_position' for i in self.parent.db.get_device_name('*', "ESP301") for axis in ['1', '2', '3']] + ['sys/taurustest/1/position']
        # scan_table format: key is the device/attr string, value is string the scan value list.
        self.scan_table = defaultdict(list)
        self.scan_table_file = os.path.join(
            os.path.dirname(__file__), 'scan_table.csv')
        with open(self.scan_table_file, 'a+') as csvfile:
            csvfile.seek(0)
            reader = csv.DictReader(csvfile)
            header = reader.fieldnames
            self.scan_number = 0
            for row in reader:
                self.scan_number += 1
                for h in header:
                    self.scan_table[h].append(row[h])

        for idx, device_attr_name in enumerate(self.scannable_list):
            self.scannable_list_row, col = int(
                idx/self.item_each_row), idx % self.item_each_row
            checkbox_var = BooleanVar(
                value=True) if device_attr_name in self.scan_table else BooleanVar(value=False)
            checkbox = ttk.Checkbutton(self.scan_frame1, text='/'.join(device_attr_name.split('/')[2:]), command=lambda device_attr_name=device_attr_name, checkbox_var=checkbox_var: self.add_device_to_scan(device_attr_name, checkbox_var),
                                       variable=checkbox_var, style='Sty1.TCheckbutton')
            checkbox.grid(
                column=col, row=self.scannable_list_row, sticky=W)

        ttk.Label(
            self.scan_frame3, text='Starting from shot ', font=('Helvetica', 12)).grid(row=0, column=0)

        self.firstrow_var = IntVar(value=1)
        ttk.Entry(self.scan_frame3, textvariable=self.firstrow_var).grid(
            row=0, column=1)
        ttk.Button(
            self.scan_frame3, text='Change', command=self.change_row_shotnum, style="Sty3_start.TButton").grid(
            row=0, column=2)

        self.update_tree()
        self.update_add_section()

        remove_selected_button = ttk.Button(
            self.scan_frame2, text='Remove selected', command=self.remove_selected, style="Sty3_stop.TButton")
        remove_selected_button.grid(
            row=21, column=0, columnspan=int(self.item_each_row/2))
        clear_button = ttk.Button(
            self.scan_frame2, text='Clear all', command=self.clear_list, style='Sty2_offline.TButton')
        clear_button.grid(row=21, column=int(
            self.item_each_row/2), columnspan=int(self.item_each_row/2))

        for child in self.winfo_children():
            child.grid_configure(padx=[0, 5], pady=5)

    def add_device_to_scan(self, device_attr_name, checkbox_var):
        '''Button command: check or uncheck the devices'''
        if checkbox_var.get():
            self.scan_table[device_attr_name] = ['']*self.scan_number
        else:
            del self.scan_table[device_attr_name]
            # remove a row of data if they are all none. Maybe not because sometimes we want some empty scan?
        self.scan_table = dict(sorted(self.scan_table.items()))
        self.update_tree()
        self.update_add_section()
        self.save_scan_table_to_file()

    def change_row_shotnum(self):
        '''Button command: apply the row to shotnum value'''
        self.parent.row_shotnum = self.firstrow_var.get()
        self.update_tree()

    def add_data_to_list(self):
        '''Button command: add a new row of scan values'''
        for i in self.scan_table:
            self.scan_table[i].append(self.add_section_widget[i]['var'].get())
        self.scan_number += 1
        self.update_tree()
        self.save_scan_table_to_file()

    def clear_list(self):
        '''Button command: clear the scan list'''
        for i in self.scan_table:
            self.scan_table[i] = []
        self.update_tree()
        self.save_scan_table_to_file()

    def remove_selected(self):
        '''Button command: remove selected row'''
        selected_item = self.tree.selection()
        for key, value in self.scan_table.items():
            self.scan_table[key] = [v for idx, v in enumerate(
                value) if idx not in [int(s)-1 for s in selected_item]]
        self.update_tree()
        self.save_scan_table_to_file()

    def save_scan_table_to_file(self):
        with open(self.scan_table_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(list(self.scan_table.keys()))
            writer.writerows([[value[idx] for value in self.scan_table.values()]
                             for idx in range(len(list(self.scan_table.values())[0]))])

    def update_tree(self):
        '''Render the tree widget'''
        if hasattr(self, 'tree'):
            self.tree.destroy()
        self.tree = ttk.Treeview(self.scan_frame2, style="normal.Treeview")
        self.tree.column("#0", width=50, anchor='center')
        self.tree['columns'] = list(self.scan_table.keys())
        for i in self.scan_table:
            self.tree.column(i, width=150, anchor='center')
            self.tree.heading(i, text='/'.join(i.split('/')[-2:]))
        for key, value in self.scan_table.items():
            for idx, v in enumerate(value):
                if not self.tree.exists(str(idx+1)):
                    # assign a tag for each row so that we can change the tag configuration (for example change background color) in the future.
                    self.tree.insert('', 'end', str(idx+1),
                                     text=f'#{idx+self.parent.row_shotnum}', tags=(f'#{idx+self.parent.row_shotnum}'))
                self.tree.set(str(idx+1), key, v)
        if self.tree.tag_has(f'#{self.parent.current_shot_number}'):
            self.tree.tag_configure(
                f'#{self.parent.current_shot_number}', background='yellow')
        self.tree.grid(column=0, columnspan=self.item_each_row,
                       row=self.scannable_list_row+1, rowspan=len(self.scan_table)+1)

    def update_add_section(self):
        '''Render add new row section'''
        if hasattr(self, 'add_section_widget'):
            for i in self.add_section_widget:
                self.add_section_widget[i]['label'].grid_forget()
                self.add_section_widget[i]['entry'].grid_forget()
        self.add_section_widget = defaultdict(dict)
        for idx, i in enumerate(self.scan_table):
            self.add_section_widget[i]['label'] = ttk.Label(
                self.scan_frame4, text='/'.join(i.split('/')[-2:]), font=('Helvetica', 12))
            self.add_section_widget[i]['label'].grid(
                row=idx+1, column=len(self.scannable_list)+1)
            self.add_section_widget[i]['label'].grid_configure(
                pady=[0, 10])
            self.add_section_widget[i]['var'] = StringVar()
            self.add_section_widget[i]['entry'] = ttk.Entry(
                self.scan_frame4, textvariable=self.add_section_widget[i]['var'])
            self.add_section_widget[i]['entry'].grid(
                row=idx+1, column=len(self.scannable_list)+2)
            self.add_section_widget[i]['entry'].grid_configure(
                pady=[0, 10])

        if not hasattr(self, 'add_button'):
            self.add_button = ttk.Button(
                self.scan_frame4, text='Add to list', command=self.add_data_to_list, style="Sty3_start.TButton")
        self.add_button.grid(row=self.scannable_list_row+len(self.scan_table) +
                             1, column=len(self.scannable_list)+1, columnspan=2)


if __name__ == '__main__':
    if platform.system() == 'Windows':
        myappid = 'zeus.daq'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    root = Tk()
    root.iconphoto(True, PhotoImage(file=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'common', 'img', 'title.png')))
    dummy = DaqGUI(root)
    atexit.register(dummy.terminate)
    root.mainloop()
