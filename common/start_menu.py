import platform
import os
import subprocess
import signal
import tango
import psutil
import time
from .config import device_name_table, instance_table


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
        self.instance_table = instance_table

    def start_window(self, menu_file_path, key):
        script_path = os.path.join(
            os.path.dirname(menu_file_path), self.menu_dict[key][0])
        # the input from input text field
        input_txt = getattr(self, self.menu_dict[key][0][:-3]).get()
        # if this is a combination for start server command, get the real instance from the combination table.
        if 'server' in key and input_txt in self.instance_table:
            input_txts = self.instance_table[input_txt]
        else:
            input_txts = [input_txt]
        i = 0
        for input_txt in input_txts:
            if 'server' in key and input_txt in [i[1] for i in self.menu_dict[key][2]]:
                print(
                    f'{key} for {input_txt} has run already. Ignore the operation.')
            else:
                input_txt = input_txt.split()
                p = subprocess.Popen(
                    [f'{self.python_path}', f'{script_path}', *input_txt])
                self.menu_dict[key][2].append([p.pid, input_txt[0]])
                print(f'{p.pid} is started for {input_txt[0]}')
                i += 1
                if i != len(input_txts):
                    time.sleep(3)

    def terminate_all(self):
        for key, value in self.menu_dict.items():
            for pid in [i[0] for i in value[2]]:
                os.kill(pid, signal.SIGTERM)
                print(f'Killed {key}:{pid}')

    def terminate(self, key):
        if self.menu_dict[key][2]:
            for pid in [i[0] for i in self.menu_dict[key][2]]:
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGTERM)
                    print(f'Killed {key} {pid}')
            self.menu_dict[key][2] = []
        else:
            print('No process to kill')
