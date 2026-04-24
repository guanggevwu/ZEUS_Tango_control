import socket
from tkinter import Tk, messagebox, Toplevel, Text, StringVar, IntVar, DoubleVar, BooleanVar, PhotoImage
from tkinter import ttk
import tango
import numpy as np
from datetime import datetime
import os
import logging
import subprocess
import signal
import platform
import atexit
from threading import Thread, Event
import platform
import ctypes
from collections import defaultdict
from queue import Queue
from tango import AttributeProxy
from pypylon import pylon
import time
import sys
import json
from device_management_combination_config import container
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.config import device_name_table, instance_table, image_panel_config
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s %(message)s")

# Streamheandler is not neede because logging.basicConfig is set in some imported files.
logger.setLevel(logging.DEBUG)
log_file_path = os.path.join(os.path.dirname(
    __file__), 'Tango_device_management_log.txt')
fh = logging.FileHandler(log_file_path)
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)

logger.addHandler(fh)


class TangoDeviceManagement:
    def __init__(self, root):
        self.root = root
        self.db = tango.Database()
        self.root_path = os.path.dirname(os.path.dirname(__file__))
        self.logging_q = Queue()
        if platform.system() == 'Linux':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                self.root_path, 'venv', 'Scripts', 'python.exe')
        self.container = container
        root.title(f"ZEUS Tango Device Management")

        s = ttk.Style()
        s.theme_use('alt')

        self.font_large = 15
        self.font_mid = 10
        self.font_small = 8
        s.configure('Sty1.TLabelframe.Label',
                    foreground="blue", font=('Times', self.font_large))
        style_widgets = ['TButton', 'TLabel',
                         'TCombobox']

        for w in style_widgets:
            s.configure(f'Sty1.{w}',
                        font=('Helvetica', self.font_mid))
        s.configure('small_button.TButton', font=(
            'Helvetica', self.font_small))
        s.configure('Sty1.TCheckbutton', font=(
            'Helvetica', self.font_small))
        s.configure('highlight.TCheckbutton', font=(
            'Helvetica', self.font_small))
        s.map("highlight.TCheckbutton",
              background=[('selected', '#5dade2'), ('!selected', 'lightgrey')])
        s.configure('Sty2_offline.TButton', font=(
            'Helvetica', self.font_mid), background='#85929e')
        s.configure('Sty2_offline_text_small.TButton', font=(
            'Helvetica', self.font_small), background='#85929e')
        s.configure('Sty2_connecting.TButton', font=(
            'Helvetica', self.font_small), background='yellow')
        s.configure('Sty2_online_text_small.TButton', font=(
            'Helvetica', self.font_small), background='#5dade2')
        s.configure('Sty2_local_online_text_small.TButton', font=(
            'Helvetica', self.font_mid), background='#52be80')
        s.configure('Sty3_start_small.TButton', font=(
            'Helvetica', self.font_small), background='green')
        s.configure('Sty3_stop_small.TButton', font=(
            'Helvetica', self.font_small), background='red')
        s.configure("Treeview", font=('Helvetica', self.font_mid))
        s.configure('Treeview.Heading', font=(
            'Helvetica', self.font_small), background="PowderBlue")
        # frame1 = ttk.Frame(root, padding="3 3 12 12")
        # frame1.grid(column=0, row=0, sticky='nsew')
        # root.columnconfigure(0, weight=1)
        # root.rowconfigure(0, weight=1)

        pad_widget = "0 0 0 10"
        # ---------------------frame 1

        self.frame1 = ttk.Labelframe(
            root, text='Devices Category', padding=pad_widget, style='Sty1.TLabelframe')
        for i in range(4):  # 4 columns
            self.frame1.columnconfigure(i, weight=1, uniform='g1')
        self.frame1.grid(column=0, row=0, sticky='nsew')
        i = 0
        for key, value in self.container.items():
            value['button'] = ttk.Button(self.frame1, text=value['show_name'], command=lambda key=key: self.open_a_catergory(key), style='Sty1.TButton').grid(
                column=i % 4, row=i // 4, sticky='WE')
            i += 1

        self.frame4 = ttk.Labelframe(
            root, text='Logging', padding=pad_widget, style='Sty1.TLabelframe')
        self.frame4.grid(column=0, row=3, sticky='nsew')
        self.t = Text(self.frame4, width=75, height=12, font=(
            'Helvetica', int(self.font_mid)), wrap='word')
        self.t.tag_config("red_text", foreground="red")
        self.t.tag_config("green_text", foreground="green")
        self.t.tag_config("blue_text", foreground="blue")
        self.t.grid(column=0, row=0, sticky='W')
        self.insert_to_disabled("Tango Device Management Tool is started.")
        sb = ttk.Scrollbar(self.frame4,
                           orient='vertical',
                           command=self.t.yview)

        sb.grid(column=1, row=0, sticky='NS')
        self.t['yscrollcommand'] = sb.set
        self.schedule_logging_message()

        self.pad_space(self.frame1)
        self.pad_space(self.frame4)

    def pad_space(self, frame):
        for child in frame.winfo_children():
            child.grid_configure(padx=[15, 0], pady=3)

    def insert_to_disabled(self, text, tag_config=None, with_timestamp=True, with_alarm=None):
        if with_alarm is None:
            if tag_config == 'red_text':
                with_alarm = True
            else:
                with_alarm = False
        logger.info(text)
        if with_timestamp:
            time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.logging_q.put([f'{time}, {text}', tag_config, with_alarm])
        else:
            self.logging_q.put([text, tag_config, with_alarm])

    def schedule_logging_message(self):
        try:
            while True:
                text, tag_config, with_alarm = self.logging_q.get(block=False)
                self.t['state'] = 'normal'
                self.t.insert('end', f'{text}\n', tag_config)
                self.t.see("end")
                self.t['state'] = 'disabled'
                if with_alarm:
                    messagebox.showerror(message=text)
        except Exception as e:
            pass
        self.root.after(200, self.schedule_logging_message)

    def open_a_catergory(self, category_name):
        '''Command for the select button in frame1. It opens a new window with a list of devices.'''
        if not (hasattr(self, category_name) and getattr(self, category_name).winfo_exists()):
            setattr(self, category_name,
                    DeviceUnderCatergoryWindow(self, category_name))
        getattr(self, category_name).deiconify()
        getattr(self, category_name).attributes('-topmost', True)
        getattr(self, category_name).attributes('-topmost', False)


class DeviceUnderCatergoryWindow(Toplevel):
    def __init__(self, parent, category_name):
        super().__init__(master=parent.root)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.thread_stop_event = Event()
        self.gui_update_queue = Queue()
        self.device_status_checking_event_id = 0
        self.parent = parent
        self.category_name = category_name
        self.class_name = [i for i in parent.container[
            category_name]['class']]
        # catergory_container is a dict to store the device name and its corresponding tango_class, server_widget (ttk.Button), gui_widget (ttk.Button), gui_pid, combination_device_names (only for device names containing "_combination").
        self.category_container = {}
        for c in self.class_name:
            if c == 'Basler':
                Basler_class_device = self.parent.db.get_device_name(
                    '*', c)
            class_info = parent.container[category_name]['class'][c]
            if class_info is not None and 'only_these_devices' in class_info:
                self.category_container.update({device_name: {
                                               'tango_class': c} for device_name in class_info['only_these_devices']})
            else:
                self.category_container.update({device_name: {'tango_class': c}
                                                for device_name in self.parent.db.get_device_name('*', c)})
            if class_info is not None and 'extra_devices' in class_info:
                self.category_container.update(
                    {device_name: {'tango_class': c} for device_name in class_info['extra_devices']})

        self.title(category_name)
        newframe1 = ttk.Frame(self)
        newframe1.grid(column=0, row=0, columnspan=1, sticky='nsew')
        if category_name == "cameras":
            # only applied to basler cameras
            self.serial_number_vs_friendly_name = dict()
            for device in pylon.TlFactory.GetInstance().EnumerateDevices():
                self.serial_number_vs_friendly_name[device.GetSerialNumber(
                )] = f'{device.GetUserDefinedName()}({device.GetSerialNumber()})'

            devices_seperated_by_location = defaultdict(list)
            locations = ['laser', 'TA1', 'TA2', 'TA3', 'Others']
            for device_name in self.category_container:
                device_area = device_name.split('/')[0]
                if device_name in Basler_class_device:
                    sn = device_name.split('/')[-1].split('_')[-1]
                    if sn in self.serial_number_vs_friendly_name and '-' in self.serial_number_vs_friendly_name[sn]:
                        device_area = self.serial_number_vs_friendly_name[sn].split(
                            '-')[0]
                for location in locations[:-1]:
                    if location == device_area:
                        devices_seperated_by_location[location].append(
                            device_name)
                        break
                else:
                    devices_seperated_by_location[locations[-1]].append(
                        device_name)
            devices_seperated_by_location = dict(sorted(
                devices_seperated_by_location.items(), key=lambda x: locations.index(x[0])))

            for col, (location, device_sub_list) in enumerate(devices_seperated_by_location.items()):
                col = col*2
                sub_frame = ttk.Labelframe(
                    newframe1, text=location, padding="0 0 10 0", style='Sty1.TLabelframe')
                sub_frame.grid(column=col, row=0, sticky='N')
                for row, device_name in enumerate(device_sub_list):
                    # If this is a basler camera and its serial name has a friendly name. The serial number is obtained by parse the device name, i.e., xxx/xxx/xxx_[serial_number]
                    if device_name in Basler_class_device and device_name.split('/')[-1].split('_')[-1] in self.serial_number_vs_friendly_name:
                        button_text = self.serial_number_vs_friendly_name[device_name.split(
                            '/')[-1].split('_')[-1]]
                    else:
                        button_text = device_name
                    c = self.category_container[device_name]['tango_class']
                    self.category_container[device_name]['server_widget'] = ttk.Button(
                        sub_frame, text=button_text, command=lambda device_name=device_name: self.start_stop_device_server(device_name), style='small_button.TButton')
                    self.category_container[device_name]['server_widget'].grid(
                        column=col, row=row, sticky='NSEW')
                    self.category_container[device_name]['gui_widget'] = ttk.Button(
                        sub_frame, text='UI', command=lambda device_name=device_name: self.open_close_gui(device_name), style='small_button.TButton')
                    self.category_container[device_name]['gui_widget'].grid(
                        column=col+1, row=row, sticky='NSEW')

        else:
            item_per_col = 10
            for idx, device_name in enumerate(self.category_container):
                c = self.category_container[device_name]['tango_class']
                server_widget = ttk.Button(
                    newframe1, text=device_name, command=lambda device_name=device_name: self.start_stop_device_server(device_name))
                server_widget.grid(column=2*(idx // item_per_col), row=idx %
                                   item_per_col, sticky='NSEW')
                self.category_container[device_name]['server_widget'] = server_widget
                gui_widget = ttk.Button(
                    newframe1, text='UI', command=lambda device_name=device_name: self.open_close_gui(device_name), style='small_button.TButton')
                gui_widget.grid(column=(2*(idx // item_per_col)) + 1,
                                row=idx % item_per_col, sticky='NSEW')
                self.category_container[device_name]['gui_widget'] = gui_widget
        self.interval = 0
        self.parent.insert_to_disabled(
            f'Opened {self.parent.container[self.category_name]["show_name"]} category window.')
        t = Thread(target=self.routine_check_device_status, daemon=True)
        t.start()
        self.update_gui()

    def update_gui(self):
        try:
            while True:
                this_widget, action = self.gui_update_queue.get(block=False)
                if action == 'action1':
                    if this_widget.cget('style') not in ['Sty2_local_online_text_small.TButton', 'Sty2_connecting.TButton']:
                        this_widget.configure(
                            style='Sty2_online_text_small.TButton')
                elif action == 'action2':
                    if this_widget.cget('style') not in ['Sty2_offline_text_small.TButton', 'Sty2_connecting.TButton']:
                        this_widget.configure(
                            style='Sty2_offline_text_small.TButton')
                elif action == 'action3':
                    if this_widget.cget('style') != 'Sty2_local_online_text_small.TButton':
                        this_widget.configure(
                            style='Sty2_local_online_text_small.TButton')
                        self.parent.insert_to_disabled(
                            f'{this_widget.cget("text")} is started successfully.', tag_config='green_text')
                elif action == 'action4':
                    this_widget.configure(
                        style='Sty2_offline_text_small.TButton')
        except Exception as e:
            pass
        if not self.thread_stop_event.is_set():
            self.after(100, self.update_gui)

    def routine_check_device_status(self):
        i = 0
        while True:
            for device_name in list(self.category_container.keys()):
                if not self.thread_stop_event.is_set():
                    this_button = self.category_container[device_name]['server_widget']
                    try:
                        if '_combination' in device_name:
                            device_names_in_combination = device_name_table[device_name]
                            for device_name_in_combination in device_names_in_combination:
                                dp = tango.DeviceProxy(
                                    device_name_in_combination)
                                dp.ping()
                        else:
                            dp = tango.DeviceProxy(device_name)
                            dp.ping()
                        self.gui_update_queue.put([this_button, 'action1'])
                    except Exception as e:
                        self.gui_update_queue.put([this_button, 'action2'])
                else:
                    return
                if i:
                    time.sleep(0.1)
            i = 1

    def click_check_device_status(self, device_name, max_iter=10):
        '''This function is called when we want to check the device status after clicking the button to start the device server. We want to check the device status more frequently and for a certain number of times before giving up, because we want to give the device server enough time to start and update the button color and give a success message as soon as the device server is started.'''
        iter = 0
        this_button = self.category_container[device_name]['server_widget']
        while not self.thread_stop_event.is_set():
            try:
                dp = tango.DeviceProxy(device_name)
                dp.ping()
                self.gui_update_queue.put([this_button, 'action3'])
                return
            except Exception as e:
                iter += 1
                if iter == max_iter:
                    self.gui_update_queue.put([this_button, 'action4'])
                    return
            time.sleep(1)

    def start_stop_device_server(self, device_name):
        if '_combination' in device_name:
            self.parent.insert_to_disabled(
                f'{device_name} is a combination device. The included devices are {device_name_table[device_name]}. They can be modified in "/common/config.py". Please start/stop the each device seperately.', tag_config='red_text')
            return
        idx = list(self.category_container.keys()).index(device_name)
        self.device_status_checking_event_id += 1
        try:
            dp = tango.DeviceProxy(device_name)
            dp.ping()
            admin_device_name = dp.adm_name()
            admin_proxy = tango.DeviceProxy(admin_device_name)
            admin_proxy.command_inout("Kill")
            self.category_container[device_name]['server_widget'].configure(
                style='Sty2_offline_text_small.TButton')
            self.parent.insert_to_disabled(
                f'{device_name} device server is stopped.')
        except Exception as e:
            device_class = self.parent.db.get_device_info(
                device_name).class_name
            device_instance = self.parent.db.get_device_info(
                device_name).ds_full_name.split('/')[-1]
            if self.parent.container[self.category_name]['class'][device_class] and 'server_code_path' in self.parent.container[self.category_name]['class'][device_class]:
                script_path = self.parent.container[self.category_name]['class'][device_class]['server_code_path']
            else:
                class_folder = os.path.join(
                    self.parent.root_path, device_class)
                script_path = os.path.join(
                    class_folder, [i for i in os.listdir(class_folder) if 'server.py' in i][0])
            p = subprocess.Popen(
                [f'{self.parent.python_path}', f'{script_path}', device_instance])
            self.category_container[device_name]['server_widget'].configure(
                style='Sty2_connecting.TButton')
            self.parent.insert_to_disabled(
                f'Starting server for {device_name}...', tag_config='yellow_text')
            event = {'id': self.device_status_checking_event_id, 'current_iter': 0,
                     'max_iter': 10, 'device_index': idx}
            t = Thread(target=self.click_check_device_status,
                       args=(device_name, 10), daemon=True)
            t.start()

    def open_close_gui(self, device_name):
        c = self.category_container[device_name]['tango_class']
        if 'gui_pid' in self.category_container[device_name]:
            try:
                os.kill(
                    self.category_container[device_name]['gui_pid'], signal.SIGTERM)
            except OSError:
                self.parent.insert_to_disabled(
                    f'Not able to kill the GUI process for {device_name}, maybe already killed.')
            del self.category_container[device_name]['gui_pid']
            self.category_container[device_name]['gui_widget']['style'] = 'small_button.TButton'
            self.parent.insert_to_disabled(
                f'Client GUI of {device_name} is killed.')
        else:
            if self.parent.container[self.category_name]['class'][c] and 'GUI_code_path' in self.parent.container[self.category_name]['class'][c]:
                script_path = self.parent.container[self.category_name]['class'][c]['GUI_code_path']
            else:
                class_folder = os.path.join(
                    self.parent.root_path, c)
                script_path = os.path.join(
                    class_folder, [i for i in os.listdir(class_folder) if 'GUI' in i][0])
            if '_combination' in device_name:
                self.parent.insert_to_disabled(
                    f'{device_name} is a combination device. The included devices are {device_name_table[device_name]}. They can be modified in "/common/config.py".')
            p = subprocess.Popen(
                [f'{self.parent.python_path}', f'{script_path}', device_name])
            self.category_container[device_name]['gui_pid'] = p.pid
            self.category_container[device_name][
                'gui_widget']['style'] = 'Sty2_online_text_small.TButton'

    def on_close(self):
        self.thread_stop_event.set()
        self.destroy()
        self.parent.insert_to_disabled(
            f'{self.parent.container[self.category_name]["show_name"]} window is destroyed.')


if __name__ == '__main__':
    if platform.system() == 'Windows':
        myappid = 'zeus.device_management'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    root = Tk()
    root.iconphoto(True, PhotoImage(file=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'common', 'img', 'title.png')))
    dummy = TangoDeviceManagement(root)
    root.mainloop()
