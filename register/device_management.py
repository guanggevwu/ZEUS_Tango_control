import socket
from tkinter import Tk, messagebox, Toplevel, Text, StringVar, IntVar, DoubleVar, BooleanVar, PhotoImage, Listbox, END, MULTIPLE
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
from device_combinations import device_name_table, save_combination
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

    def refresh_serial_number_vs_friendly_name(self):
        '''Refresh the map of locally detected Basler cameras.'''
        self.serial_number_vs_friendly_name = {}
        for device in pylon.TlFactory.GetInstance().EnumerateDevices():
            serial_number = device.GetSerialNumber()
            self.serial_number_vs_friendly_name[serial_number] = \
                f'{device.GetUserDefinedName()}({serial_number})'

    def is_basler_online(self, device_name):
        serial_number = device_name.split('/')[-1].split('_')[-1]
        return serial_number in self.serial_number_vs_friendly_name

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
        if category_name == 'cameras':
            self.refresh_serial_number_vs_friendly_name()
        if not (hasattr(self, category_name) and getattr(self, category_name).winfo_exists()):
            setattr(self, category_name,
                    DeviceUnderCatergoryWindow(self, category_name))
        getattr(self, category_name).deiconify()
        getattr(self, category_name).attributes('-topmost', True)
        getattr(self, category_name).attributes('-topmost', False)


class DevicePropertiesWindow(Toplevel):
    def __init__(self, parent, device_name):
        super().__init__(master=parent)
        self.parent = parent
        self.device_name = device_name
        self.db = parent.parent.db
        self.title(f'Properties - {device_name}')
        self.geometry('700x420')

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self, padding=10)
        table_frame.grid(column=0, row=0, sticky='nsew')
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.property_table = ttk.Treeview(
            table_frame, columns=('name', 'value'), show='headings', selectmode='browse')
        self.property_table.heading('name', text='Property')
        self.property_table.heading('value', text='Value')
        self.property_table.column('name', width=220, minwidth=120)
        self.property_table.column('value', width=430, minwidth=180)
        self.property_table.grid(column=0, row=0, sticky='nsew')
        self.property_table.bind('<<TreeviewSelect>>',
                                 self.on_property_selected)

        scrollbar = ttk.Scrollbar(
            table_frame, orient='vertical', command=self.property_table.yview)
        scrollbar.grid(column=1, row=0, sticky='ns')
        self.property_table.configure(yscrollcommand=scrollbar.set)

        editor = ttk.Labelframe(self, text='Add or edit property', padding=10)
        editor.grid(column=0, row=1, padx=10, pady=(0, 10), sticky='ew')
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text='Name').grid(column=0, row=0, sticky='w')
        self.property_name = StringVar()
        self.property_name_entry = ttk.Entry(
            editor, textvariable=self.property_name)
        self.property_name_entry.grid(
            column=1, row=0, columnspan=4, padx=(8, 0), sticky='ew')

        ttk.Label(editor, text='Value').grid(
            column=0, row=1, pady=(8, 0), sticky='nw')
        self.property_value = Text(editor, height=4, wrap='none')
        self.property_value.grid(
            column=1, row=1, columnspan=4, padx=(8, 0), pady=(8, 0), sticky='ew')
        ttk.Label(editor, text='Use one line per value for array properties.').grid(
            column=1, row=2, columnspan=4, padx=(8, 0), sticky='w')

        ttk.Button(editor, text='Save', command=self.save_property).grid(
            column=1, row=3, padx=(8, 4), pady=(10, 0), sticky='ew')
        ttk.Button(editor, text='New', command=self.clear_editor).grid(
            column=2, row=3, padx=4, pady=(10, 0), sticky='ew')
        ttk.Button(editor, text='Remove', command=self.remove_property).grid(
            column=3, row=3, padx=4, pady=(10, 0), sticky='ew')
        ttk.Button(editor, text='Refresh', command=self.load_properties).grid(
            column=4, row=3, padx=(4, 0), pady=(10, 0), sticky='ew')

        self.load_properties()
        self.transient(parent)
        self.lift()

    def load_properties(self):
        try:
            property_datum = self.db.get_device_property_list(
                self.device_name, '*')
            property_names = list(property_datum.value_string)
            properties = self.db.get_device_property(
                self.device_name, property_names) if property_names else {}
        except Exception as e:
            messagebox.showerror(
                'Cannot load properties', str(e), parent=self)
            return

        self.property_table.delete(*self.property_table.get_children())
        for name in sorted(property_names, key=str.lower):
            values = properties.get(name, [])
            if isinstance(values, str):
                values = [values]
            else:
                values = list(values)
            self.property_table.insert(
                '', 'end', iid=name, values=(name, '\n'.join(str(value) for value in values)))
        self.clear_editor()

    def on_property_selected(self, event=None):
        selection = self.property_table.selection()
        if not selection:
            return
        name = selection[0]
        values = self.property_table.item(name, 'values')
        self.property_name.set(name)
        self.property_value.delete('1.0', 'end')
        self.property_value.insert('1.0', values[1] if len(values) > 1 else '')

    def clear_editor(self):
        self.property_table.selection_remove(*self.property_table.selection())
        self.property_name.set('')
        self.property_value.delete('1.0', 'end')
        self.property_name_entry.focus_set()

    def save_property(self):
        name = self.property_name.get().strip()
        if not name:
            messagebox.showwarning(
                'Missing property name', 'Enter a property name.', parent=self)
            return
        values = self.property_value.get('1.0', 'end-1c').splitlines()
        if not values:
            values = ['']
        try:
            self.db.put_device_property(self.device_name, {name: values})
        except Exception as e:
            messagebox.showerror(
                'Cannot save property', str(e), parent=self)
            return
        self.parent.parent.insert_to_disabled(
            f'Updated property {name} for {self.device_name}.', tag_config='green_text')
        self.load_properties()

    def remove_property(self):
        name = self.property_name.get().strip()
        if not name:
            messagebox.showwarning(
                'No property selected', 'Select a property to remove.', parent=self)
            return
        if not messagebox.askyesno(
                'Remove property',
                f'Remove property "{name}" from {self.device_name}?', parent=self):
            return
        try:
            self.db.delete_device_property(self.device_name, name)
        except Exception as e:
            messagebox.showerror(
                'Cannot remove property', str(e), parent=self)
            return
        self.parent.parent.insert_to_disabled(
            f'Removed property {name} from {self.device_name}.', tag_config='green_text')
        self.load_properties()


class CombinationDevicesWindow(Toplevel):
    def __init__(self, parent, combination_name, tango_class):
        super().__init__(master=parent)
        self.parent = parent
        self.combination_name = combination_name
        self.tango_class = tango_class
        self.db = parent.parent.db
        self.title(f'Included Devices - {combination_name}')
        self.geometry('850x430')
        self.minsize(650, 320)
        self.transient(parent)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text=f'Available {tango_class} devices').grid(
            column=0, row=0, padx=10, pady=(10, 4), sticky='w')
        ttk.Label(self, text='Included devices (in launch order)').grid(
            column=2, row=0, padx=10, pady=(10, 4), sticky='w')

        self.available_devices = Listbox(
            self, selectmode=MULTIPLE, exportselection=False)
        self.available_devices.grid(
            column=0, row=1, padx=(10, 5), sticky='nsew')
        self.available_devices.bind('<Double-Button-1>', self.add_devices)

        controls = ttk.Frame(self)
        controls.grid(column=1, row=1, padx=5)
        ttk.Button(controls, text='Add  >', command=self.add_devices).grid(
            column=0, row=0, pady=4, sticky='ew')
        ttk.Button(controls, text='<  Remove', command=self.remove_devices).grid(
            column=0, row=1, pady=4, sticky='ew')
        ttk.Separator(controls).grid(
            column=0, row=2, pady=10, sticky='ew')
        ttk.Button(controls, text='Move up', command=lambda: self.move_device(-1)).grid(
            column=0, row=3, pady=4, sticky='ew')
        ttk.Button(controls, text='Move down', command=lambda: self.move_device(1)).grid(
            column=0, row=4, pady=4, sticky='ew')

        self.included_devices = Listbox(
            self, selectmode=MULTIPLE, exportselection=False)
        self.included_devices.grid(
            column=2, row=1, padx=(5, 10), sticky='nsew')
        self.included_devices.bind('<Double-Button-1>', self.remove_devices)

        actions = ttk.Frame(self, padding=10)
        actions.grid(column=0, row=2, columnspan=3, sticky='e')
        ttk.Button(actions, text='Reload', command=self.load_devices).grid(
            column=0, row=0, padx=4)
        ttk.Button(actions, text='Cancel', command=self.destroy).grid(
            column=1, row=0, padx=4)
        ttk.Button(actions, text='Save', command=self.save_devices).grid(
            column=2, row=0, padx=4)

        self.load_devices()
        self.lift()

    def load_devices(self):
        included = list(device_name_table.get(self.combination_name, []))
        try:
            registered = list(self.db.get_device_name('*', self.tango_class))
            if self.tango_class.lower() == 'basler':
                self.parent.parent.refresh_serial_number_vs_friendly_name()
                registered = [
                    device_name for device_name in registered
                    if self.parent.parent.is_basler_online(device_name)
                ]
        except Exception as e:
            messagebox.showerror(
                'Cannot load devices', str(e), parent=self)
            return

        self.available_devices.delete(0, END)
        self.included_devices.delete(0, END)
        for device_name in sorted(set(registered) - set(included), key=str.lower):
            self.available_devices.insert(END, device_name)
        for device_name in included:
            self.included_devices.insert(END, device_name)

    def add_devices(self, event=None):
        selected = [self.available_devices.get(index)
                    for index in self.available_devices.curselection()]
        existing = set(self.included_devices.get(0, END))
        for device_name in selected:
            if device_name not in existing:
                self.included_devices.insert(END, device_name)
        self._remove_selected(self.available_devices)

    def remove_devices(self, event=None):
        selected = [self.included_devices.get(index)
                    for index in self.included_devices.curselection()]
        self._remove_selected(self.included_devices)
        existing = set(self.available_devices.get(0, END))
        for device_name in selected:
            if device_name not in existing:
                self.available_devices.insert(END, device_name)

    @staticmethod
    def _remove_selected(listbox):
        for index in reversed(listbox.curselection()):
            listbox.delete(index)

    def move_device(self, direction):
        selection = self.included_devices.curselection()
        if len(selection) != 1:
            return
        old_index = selection[0]
        new_index = old_index + direction
        if new_index < 0 or new_index >= self.included_devices.size():
            return
        device_name = self.included_devices.get(old_index)
        self.included_devices.delete(old_index)
        self.included_devices.insert(new_index, device_name)
        self.included_devices.selection_set(new_index)

    def save_devices(self):
        devices = list(self.included_devices.get(0, END))
        if not devices and not messagebox.askyesno(
                'Empty combination',
                f'Save {self.combination_name} without any included devices?',
                parent=self):
            return
        try:
            save_combination(self.combination_name, devices)
        except Exception as e:
            messagebox.showerror(
                'Cannot save combination', str(e), parent=self)
            return
        self.parent.parent.insert_to_disabled(
            f'Updated included devices for {self.combination_name}: {devices}',
            tag_config='green_text')
        self.destroy()


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
        Basler_class_device = []
        for c in self.class_name:
            if c == 'Basler':
                Basler_class_device = [
                    device_name
                    for device_name in self.parent.db.get_device_name('*', c)
                    if self.parent.is_basler_online(device_name)
                ]
            class_info = parent.container[category_name]['class'][c]
            if class_info is not None and 'only_these_devices' in class_info:
                device_names = class_info['only_these_devices']
            else:
                device_names = Basler_class_device if c == 'Basler' else \
                    self.parent.db.get_device_name('*', c)
            if c == 'Basler':
                device_names = [
                    device_name for device_name in device_names
                    if self.parent.is_basler_online(device_name)
                ]
            self.category_container.update({
                device_name: {'tango_class': c}
                for device_name in device_names
            })
            if class_info is not None and 'extra_devices' in class_info:
                extra_devices = class_info['extra_devices']
                if c == 'Basler':
                    extra_devices = [
                        device_name for device_name in extra_devices
                        if '_combination' in device_name
                        or self.parent.is_basler_online(device_name)
                    ]
                self.category_container.update({
                    device_name: {'tango_class': c}
                    for device_name in extra_devices
                })

        self.title(category_name)
        newframe1 = ttk.Frame(self)
        newframe1.grid(column=0, row=0, columnspan=1, sticky='nsew')
        if category_name == "cameras":
            self.serial_number_vs_friendly_name = \
                self.parent.serial_number_vs_friendly_name

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
                col = col*3
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
                    self.category_container[device_name]['property_widget'] = ttk.Button(
                        sub_frame, text='Properties', command=lambda device_name=device_name: self.open_properties(device_name), style='small_button.TButton')
                    self.category_container[device_name]['property_widget'].grid(
                        column=col+2, row=row, sticky='NSEW')

        else:
            item_per_col = 10
            for idx, device_name in enumerate(self.category_container):
                c = self.category_container[device_name]['tango_class']
                server_widget = ttk.Button(
                    newframe1, text=device_name, command=lambda device_name=device_name: self.start_stop_device_server(device_name))
                server_widget.grid(column=3*(idx // item_per_col), row=idx %
                                   item_per_col, sticky='NSEW')
                self.category_container[device_name]['server_widget'] = server_widget
                gui_widget = ttk.Button(
                    newframe1, text='UI', command=lambda device_name=device_name: self.open_close_gui(device_name), style='small_button.TButton')
                gui_widget.grid(column=(3*(idx // item_per_col)) + 1,
                                row=idx % item_per_col, sticky='NSEW')
                self.category_container[device_name]['gui_widget'] = gui_widget
                property_widget = ttk.Button(
                    newframe1, text='Properties', command=lambda device_name=device_name: self.open_properties(device_name), style='small_button.TButton')
                property_widget.grid(column=(3*(idx // item_per_col)) + 2,
                                     row=idx % item_per_col, sticky='NSEW')
                self.category_container[device_name]['property_widget'] = property_widget
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
        # check all devices every 60 seconds
        time_interval = max(0.1, 60//len(self.category_container))
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
                    time.sleep(time_interval)
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
                f'{device_name} is a combination device. The included devices are {device_name_table[device_name]}. Use its Properties button to modify them. Please start/stop each device separately.', tag_config='red_text')
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
            if 'server_pid' in self.category_container[device_name]:
                del self.category_container[device_name]['server_pid']
        except Exception as e:
            if 'server_pid' not in self.category_container[device_name]:
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
                self.category_container[device_name]['server_pid'] = p.pid
                self.category_container[device_name]['server_widget'].configure(
                    style='Sty2_connecting.TButton')
                self.parent.insert_to_disabled(
                    f'Starting server for {device_name}...', tag_config='yellow_text')
                t = Thread(target=self.click_check_device_status,
                           args=(device_name, 10), daemon=True)
                t.start()
            else:
                try:
                    os.kill(self.category_container[device_name]
                            ['server_pid'], signal.SIGTERM)
                except OSError:
                    self.parent.insert_to_disabled(
                        f'{device_name} server was already killed somewhere else. Ignore.')
                self.category_container[device_name]['server_widget']['style'] = 'Sty2_offline_text_small.TButton'
                del self.category_container[device_name]['server_pid']
                self.parent.insert_to_disabled(
                    f'{device_name} starting is interrupted.')

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
                    f'{device_name} is a combination device. The included devices are {device_name_table[device_name]}. Use its Properties button to modify them.')
            p = subprocess.Popen(
                [f'{self.parent.python_path}', f'{script_path}', device_name])
            self.category_container[device_name]['gui_pid'] = p.pid
            self.category_container[device_name][
                'gui_widget']['style'] = 'Sty2_online_text_small.TButton'

    def open_properties(self, device_name):
        if '_combination' in device_name:
            window = self.category_container[device_name].get(
                'property_window')
            if window is None or not window.winfo_exists():
                window = CombinationDevicesWindow(
                    self, device_name,
                    self.category_container[device_name]['tango_class'])
                self.category_container[device_name][
                    'property_window'] = window
            else:
                window.load_devices()
                window.deiconify()
                window.lift()
            return
        window = self.category_container[device_name].get('property_window')
        if window is None or not window.winfo_exists():
            window = DevicePropertiesWindow(self, device_name)
            self.category_container[device_name]['property_window'] = window
        else:
            window.load_properties()
            window.deiconify()
            window.lift()

    def kill_started_device_servers(self):
        for device_name, info in self.category_container.items():
            if 'server_pid' not in info:
                continue
            try:
                os.kill(info['server_pid'], signal.SIGTERM)
                self.parent.insert_to_disabled(
                    f'{device_name} device server started from this window is killed.')
            except OSError:
                self.parent.insert_to_disabled(
                    f'{device_name} device server was already killed somewhere else. Ignore.')
            finally:
                if 'server_pid' in info:
                    del info['server_pid']
                info['server_widget']['style'] = 'Sty2_offline_text_small.TButton'

    def on_close(self):
        self.thread_stop_event.set()
        self.kill_started_device_servers()
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
