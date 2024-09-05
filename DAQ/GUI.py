from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import tango
import sys
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


class DaqGUI:
    def __init__(self, root):
        self.db = tango.Database()
        self.root_path = os.path.dirname(os.path.dirname(__file__))
        if platform.system() == 'Linux':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'Scripts', 'python.exe')
        # self.selected_devices is a dictionary. Key is the device name, value is another dictionary. In the sub-dictionary, the keys are "checkbutton" and "server_pid".
        self.selected_devices = dict()
        self.client_GUI = dict()
        self.acquisition = {'status': False}

        root.title(f"ZEUS DAQ GUI")

        s = ttk.Style()
        s.theme_use('alt')

        self.font_large = 20
        self.font_mid = 15
        s.configure('Sty1.TLabelframe.Label',
                    foreground="blue", font=('Times', self.font_large))
        style_widgets = ['TButton', 'TLabel',
                         'TCombobox', 'TCheckbutton']

        for w in style_widgets:
            s.configure(f'Sty1.{w}',
                        font=('Helvetica', self.font_mid))
        s.configure('Sty2_offline.TButton', font=(
            'Helvetica', self.font_mid), background='#85929e')
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

        self.frame2_checkbutton_content = {'default_config': {'text': 'Use the default configuration for the cameras', 'init_status': True},  'save_config': {'text': 'Save the configurations to a file', 'init_status': True}, 'background_image': {
            'text': 'Save backgrounds image before acquisition', 'init_status': True}, 'stitch': {'text': 'Stitch the images from multiple cameras and save a large image', 'init_status': True}, }

        for idx, (key, value) in enumerate(self.frame2_checkbutton_content.items()):
            # checkbox_var = BooleanVar(value=value['init_status'])
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
        dt_string = datetime.now().strftime("%Y%m%d")
        self.path_var = StringVar(
            value=fr'Z:\user_data\2024\Qing_Zhang\TA_data\{dt_string}_run')
        ttk.Entry(self.frame3, textvariable=self.path_var, font=(
            'Helvetica', int(self.font_mid*0.75)), width=60).grid(
            column=1, row=0, sticky='W')

        self.acquisition['button'] = ttk.Button(
            self.frame3, text='Start', command=self.thread_acquisition, style='Sty3_start.TButton')
        self.acquisition['button'].grid(
            column=0, row=1, columnspan=2, sticky='WE')

        self.pad_space(self.frame1)
        for child in self.frame2.winfo_children():
            child.grid_configure(padx=[self.font_mid, 0], pady=3)
        for child in self.frame3.winfo_children():
            child.grid_configure(padx=[self.font_mid, 0], pady=3)

    def pad_space(self, frame):
        for child in frame.winfo_children():
            child.grid_configure(padx=[self.font_mid, 0], pady=3)

    def open_device_list(self):
        # if not (hasattr(self, "window1") and self.window1.winfo_exists()):
        if not (hasattr(self, "window1") and self.window1.winfo_exists()):
            self.window1 = DeviceListWindow(
                update_selected_devices=self.update_selected_devices, selected_devices=self.selected_devices, db=self.db)
            self.window1.title("Device List")
        self.window1.attributes('-topmost', True)
        self.window1.attributes('-topmost', False)

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
            self.selected_devices[device_name]['checkbutton']['style'] = 'Sty2_online.TButton'
        else:
            try:
                os.kill(self.selected_devices[device_name]
                        ['server_pid'], signal.SIGTERM)
            except OSError:
                logging.info(
                    f"{self.selected_devices[device_name]['server_pid']}  doesn't exist")
            del self.selected_devices[device_name]['server_pid']
            self.selected_devices[device_name]['checkbutton']['style'] = 'Sty2_offline.TButton'
            logging.info(f'{device_name} server is killed!')

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
                logging.info('GUI is killed somewhere else!')
            del self.client_GUI['client_pid']
            self.client_GUI['button']['style'] = 'Sty2_client_offline.TButton'
            logging.info(f'Client GUI is killed!')

    def terminate(self):
        for key, value in self.selected_devices.items():
            if 'server_pid' in value:
                os.kill(value['server_pid'], signal.SIGTERM)
            if 'client_pid' in value:
                os.kill(value['client_pid'], signal.SIGTERM)
        logging.info("terminated!")

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
            value['checkbutton'].grid(
                column=idx % self.selected_device_per_row, row=self.device_row+int(idx/self.selected_device_per_row), sticky='W')
        self.pad_space(self.frame1)

    def thread_acquisition(self):
        if self.acquisition['status']:
            self.my_event.set()
            self.acquisition['status'] = False
            self.acquisition['button']['style'] = 'Sty3_start.TButton'
            self.acquisition['button']['text'] = 'Start'
            logging.info("Stopped acquisition in thread")
        else:
            self.acquisition['status'] = True
            self.my_event = Event()
            Thread(target=self.start_acquisition).start()
            self.acquisition['button']['style'] = 'Sty3_stop.TButton'
            self.acquisition['button']['text'] = 'Stop'
            logging.info("Started acquisition in thread")

    def start_acquisition(self):
        config_dict = None if self.frame2_checkbutton_content['default_config']['var'].get() else dict(
        )
        save_config = self.frame2_checkbutton_content['save_config']['var'].get(
        )
        if_background = self.frame2_checkbutton_content['background_image']['var'].get(
        )
        if_stitch = self.frame2_checkbutton_content['stitch']['var'].get(
        )
        self.daq = Daq(self.selected_devices,
                       dir=self.path_var.get(), thread_event=self.my_event, check_exist=False)
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
        self.daq.set_camera_configuration(
            config_dict=config_dict, saving=save_config)
        if if_background:
            self.daq.take_background(stitch=if_stitch)
        self.daq.acquisition(stitch=if_stitch)


class DeviceListWindow(Toplevel):
    def __init__(self, update_selected_devices, selected_devices, db):
        self.update_selected_devices = update_selected_devices
        self.selected_devices = selected_devices
        self.db = db
        super().__init__(master=root)
        self.class_name = ['Basler', 'FileReader']
        self.device_names = []
        for c in self.class_name:
            self.device_names.extend(self.db.get_device_name('*', c))
        newframe1 = ttk.Frame(self)
        newframe1.grid(column=0, row=0, columnspan=1, sticky=(N, W, E, S))
        item_each_row = 1
        checkboxes = dict()
        for idx, device_name in enumerate(self.device_names):
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


if __name__ == '__main__':
    root = Tk()
    dummy = DaqGUI(root)
    atexit.register(dummy.terminate)
    root.mainloop()
