import platform
import os
import subprocess
import signal
import tango
import psutil


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

    def start_window(self, menu_file_path, key):
        script_path = os.path.join(
            os.path.dirname(menu_file_path), self.menu_dict[key][0])
        input_txt = getattr(self, self.menu_dict[key][0][:-3]).get()
        # using os.system cause hang up in server code
        # os.system(
        #     f'{self.python_path} {script_path} {input_txt}')
        if self.menu_dict[key][2] and "server" in key:
            print(f'{key} was already started. Ignore the operation.')
        else:
            p = subprocess.Popen(
                [f'{self.python_path}', f'{script_path}', f'{input_txt}'])
            self.menu_dict[key][2].append(p.pid)
            print(f'{p.pid} is started')

    def terminate_all(self):
        for key, value in self.menu_dict.items():
            for pid in value[2]:
                os.kill(pid, signal.SIGTERM)
                print(f'Killed {key}:{pid}')

    def terminate(self, key):
        if self.menu_dict[key][2]:
            for pid in self.menu_dict[key][2]:
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGTERM)
                    print(f'Killed {key} {pid}')
            self.menu_dict[key][2] = []
        else:
            print('No process to kill')
