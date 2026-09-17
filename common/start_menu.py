import platform
import os
import subprocess
import signal
import tango
import psutil
import time
from .ui_config import device_name_table


class Menu:
    def __init__(self):
        venv_path = os.path.dirname(os.path.dirname(__file__))
        if platform.system() == 'Linux':
            self.python_path = os.path.join(venv_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                venv_path, 'venv', 'Scripts', 'python.exe')
        self.db = tango.Database()
        self.servers = self.db.get_server_list()
        self.device_name_table = device_name_table

    def get_class_related_info(self):
        self.class_name = type(self).__name__.replace('Menu', '')
        self.device_names = self.db.get_device_name('*', self.class_name)
        # UI combinations are available only to GUI launchers. Server launchers
        # use self.instances and therefore always start one server at a time.
        self.device_names = [
            name for name in self.device_name_table
            if self.class_name.lower() in name.split('_')
        ] + list(self.device_names.value_string)
        indexed_sorted_device_names = sorted(
            enumerate([name.split('/')[-1] for name in self.device_names]), key=lambda x: x[1])
        indices1, _ = zip(
            *indexed_sorted_device_names)
        self.device_names = [self.device_names[i] for i in indices1]
        self.instances = [e.split('/')[-1]
                          for e in self.servers if e.split('/')[0] == self.class_name]
        self.instances = sorted(self.instances)

    def start_window(self, menu_file_path, key):
        script_path = os.path.join(
            os.path.dirname(menu_file_path), self.menu_dict[key][0])
        if not os.path.isfile(script_path):
            script_path = os.path.join(os.path.dirname(menu_file_path), [i for i in os.listdir(os.path.dirname(
                menu_file_path)) if self.menu_dict[key][0] in i][0])
        # the input from input text field
        input_txt = getattr(self, self.menu_dict[key][0][:-3]).get()
        if self.class_name == 'Basler':
            idx = self.menu_dict[key][3].index(input_txt)
            input_txt = self.menu_dict[key][1][idx]
        if 'server' in key and input_txt in [i[1] for i in self.menu_dict[key][2]]:
            print(
                f'{key} for {input_txt} has run already. Ignore the operation.')
            return
        input_args = input_txt.split()
        p = subprocess.Popen(
            [f'{self.python_path}', f'{script_path}', *input_args])
        self.menu_dict[key][2].append([p.pid, input_args[0]])
        print(f'{p.pid} is started for {input_args[0]}')

    def terminate_all(self):
        for key, value in self.menu_dict.items():
            for pid in [i[0] for i in value[2]]:
                os.kill(pid, signal.SIGTERM)
                print(f'Killed {key}:{pid}')

    def _call_tango_shutdown(self, instance_name):
        try:
            devices = self.db.get_device_name(
                f'{self.class_name}/{instance_name}', '*'
            )
            for dev_name in devices.value_string:
                # Skip admin devices (dserver)
                if dev_name.startswith('dserver/'):
                    continue
                try:
                    dp = tango.DeviceProxy(dev_name)
                    dp.set_timeout_millis(3000)
                    dp.command_inout('shutdown')
                    print(f'Shutdown command sent to {dev_name}')
                except Exception as exc:
                    print(f'Could not call shutdown on {dev_name}: {exc}')
        except Exception as exc:
            print(f'Could not look up devices for {instance_name}: {exc}')

    def terminate(self, key):
        if self.menu_dict[key][2]:
            if 'server' in key:
                for entry in self.menu_dict[key][2]:
                    pid, instance_name = entry[0], entry[1]
                    if psutil.pid_exists(pid):
                        self._call_tango_shutdown(instance_name)
                time.sleep(2)
            for entry in self.menu_dict[key][2]:
                pid = entry[0]
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGTERM)
                    print(f'Killed {key} {pid}')
            self.menu_dict[key][2] = []
        else:
            print('No process to kill')
