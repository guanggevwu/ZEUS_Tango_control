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
import json
import platform
import ctypes
import csv
from collections import defaultdict
from queue import Queue
from tango import AttributeProxy
from pypylon import pylon
import time

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
        self.container = {'cameras': {'show_name': 'Cameras', 'class': {'Basler': None, 'Vimba': None, 'FileReader': {'included_device': ['facility/file_reader/andor_1']}}, }, 'motion_control': {'show_name': 'Motion Control', 'class': {'ESP301': None, 'Owis': None}}, 'delay_generator': {'show_name': 'Delay Generator', 'class': {'DG535': {'code_path': os.path.join(self.root_path, 'DG', 'dg535_server.py')}, 'DG645': {'server_code_path': os.path.join(self.root_path, 'DG', 'dg645_server.py'), 'GUI_code_path': os.path.join(self.root_path, 'DG', 'GUI.py')}}},
                          'energy_meter': {'show_name': 'Energy Meters', 'class': {'GentecEO': None}}, '1D_devices': {'show_name': '1-D Devices', 'class': {'FileReader': {'included_device': ['facility/file_reader/spectrometer', 'other/file_reader/oscilloscope']}}},
                          'pressure_regulator': {'show_name': 'Pressure Regulators', 'class': {'GXRegulator': None}}, 'TH': {'show_name': 'TH', 'class': {'TSP01B': None}}, 'Labview_translator': {'show_name': 'Labview Translator', 'class': {'LabviewProgram': None}}, 'laser_warning_sign': {'show_name': 'Laser Status', 'class': {'LaserWarningSign': None}}
                          }

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
            text, tag_config, with_alarm = self.logging_q.get(block=False)
            self.t['state'] = 'normal'
            self.t.insert('end', f'{text}\n', tag_config)
            self.t.see("end")
            self.t['state'] = 'disabled'
            if with_alarm:
                messagebox.showerror(message=text)
        except Exception as e:
            pass
        finally:
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
        self.after_id = {'usual_status_check': None,
                         'device_specific_status_check': {}}
        self.device_status_checking_event_id = 0
        self.parent = parent
        self.category_name = category_name
        self.class_name = [i for i in parent.container[
            category_name]['class']]
        self.category_container = {}
        for c in self.class_name:
            class_info = parent.container[category_name]['class'][c]
            if class_info is None or 'included_device' not in class_info:
                if c == 'Basler':
                    Basler_class_device = self.parent.db.get_device_name(
                        '*', c)
                self.category_container.update({device_name: {'tango_class': c}
                                                for device_name in self.parent.db.get_device_name('*', c)})
            elif 'included_device' in class_info:
                self.category_container.update({device_name: {
                                               'tango_class': c} for device_name in class_info['included_device']})
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
        self.device_idx = 0
        self.interval = 1
        self.parent.insert_to_disabled(
            f'Opened {self.parent.container[self.category_name]["show_name"]} category window.')
        self.update_device_status()

    def update_device_status(self, event=None):
        '''

        :param event. event is a dict that contains the information for checking the device status. An example is: {'id': self.device_status_checking_event_id, 'current_iter': 0,
                     'max_iter': 10, 'device_index': idx}. id is an increasing index for a scheduled event. One event can contain multiple synchronous scheduled functions. current_iter and max_iter are used to control how many times the checking will be repeated. device_index is the index of the device to check in self.category_container. 
        '''
        if event is None:
            idx = self.device_idx
        else:
            idx = event['device_index']
        device_name = list(self.category_container.keys())[idx]
        this_button = self.category_container[device_name]['server_widget']
        try:
            t0 = time.time()
            dp = tango.DeviceProxy(device_name)
            # print(f'create dp: {time.time() - t0:.6f} seconds')
            dp.ping()
            # print(f'ping dp: {time.time() - t0:.6f} seconds')
            # If we are trying to checking a device status after turnin it on, we want (1) a quick quit after the decies is on to avoid unnecessary checking, and (2) button color to be green to indicate the device server is started locally.
            if event is not None and event['id'] in self.after_id['device_specific_status_check']:
                this_button.configure(
                    style='Sty2_local_online_text_small.TButton')
                del self.after_id['device_specific_status_check'][event['id']]
                self.parent.insert_to_disabled(
                    f'{device_name} is started successfully.', tag_config='green_text')
                return
            if event is None and this_button.cget('style') not in ['Sty2_local_online_text_small.TButton', 'Sty2_connecting.TButton']:
                this_button.configure(
                    style='Sty2_online_text_small.TButton')

        except Exception as e:
            if this_button.cget('style') != 'Sty2_connecting.TButton' or (event is not None and event['current_iter'] == event['max_iter']):
                this_button.configure(
                    style='Sty2_offline_text_small.TButton')

        if event is None:
            if self.device_idx == len(self.category_container) - 1:
                self.interval = 500
            self.device_idx = (self.device_idx +
                               1) % len(self.category_container)
            self.after_id['usual_status_check'] = self.after(
                self.interval, lambda: self.update_device_status())
        else:
            if event['current_iter'] < event['max_iter']:
                event['current_iter'] += 1
                after_id = self.after(
                    2000, lambda: self.update_device_status(event))
                'device_specific_status_check'
                self.after_id['device_specific_status_check'][event['id']] = after_id
                # print(
                #     f'schedule next check with after_id {after_id}, current_iter: {event["current_iter"]}, max_iter: {event["max_iter"]}, device_index: {event["device_index"]}')
                # print(self.after_id)
            else:
                del self.after_id['device_specific_status_check'][event['id']]

    def start_stop_device_server(self, device_name):
        idx = list(self.category_container.keys()).index(device_name)
        c = self.category_container[device_name]['tango_class']
        self.device_status_checking_event_id += 1
        try:
            dp = tango.DeviceProxy(device_name)
            dp.ping()
            admin_device_name = dp.adm_name()
            admin_proxy = tango.DeviceProxy(admin_device_name)
            admin_proxy.command_inout("Kill")
            event = {'id': self.device_status_checking_event_id, 'current_iter': 0,
                     'max_iter': 2, 'device_index': idx}
            self.update_device_status(event=event)
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
            self.update_device_status(event=event)

    def open_close_gui(self, device_name):
        idx = list(self.category_container.keys()).index(device_name)
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
            p = subprocess.Popen(
                [f'{self.parent.python_path}', f'{script_path}', device_name])
            self.category_container[device_name]['gui_pid'] = p.pid
            self.category_container[device_name][
                'gui_widget']['style'] = 'Sty2_online_text_small.TButton'

    def on_close(self):
        for key, after_id in self.after_id.items():
            if isinstance(after_id, dict):
                for sub_after_id in after_id.values():
                    self.after_cancel(sub_after_id)
            elif after_id is not None:
                self.after_cancel(after_id)
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
