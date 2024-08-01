import platform
import os
import subprocess
import signal
import tango
import psutil
import time
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
        # when start the server, the server name is derived from the full device name. When the last part of the device name is equal to the server name, we must manually define it. The 'combine' is only for GUI combination show.
        self.combination_table_client = {'TA1_conf1':['TA1/basler/TA1-Ebeam', 'TA1/basler/TA1-EspecH', 'TA1/basler/TA1-EspecL', 'TA1/basler/TA1-Shadowgraphy'], 'TA1_conf1_combine':['TA1_conf1_combine'], 'TA2_conf1':['TA2/basler/TA2-NearField', 'TA2/basler/TA2-FarField'], 'TA2_conf1_combine':['TA2_conf1_combine']}
        self.combination_table_server = {key:[i.split('/')[-1] for i in value] for key ,value in self.combination_table_client.items() if 'combine' not in key}
        # manually define the server name

    def start_window(self, menu_file_path, key):
        script_path = os.path.join(
            os.path.dirname(menu_file_path), self.menu_dict[key][0])
        input_txt = getattr(self, self.menu_dict[key][0][:-3]).get()
        if 'server' in key and input_txt in self.combination_table_server:
            input_txts = self.combination_table_server[input_txt]
        elif 'GUI' in key and input_txt.split()[0] in self.combination_table_client:
            # the input_txt format is '{device_name} [--polling {polling_period}]'
            input_txts = [' '.join([i, *input_txt.split()[1:]]) for i in self.combination_table_client[input_txt]]
        else:
            input_txts = [input_txt]
        for input_txt in input_txts:
            # using os.system cause hang up in server code
            # os.system(
            #     f'{self.python_path} {script_path} {input_txt}')
            if input_txt in [i[1] for i in self.menu_dict[key][2]]:
                print(f'{key} for {input_txt} has run already. Ignore the operation.')
            else:
                input_txt = input_txt.split()
                p = subprocess.Popen(
                    [f'{self.python_path}', f'{script_path}', *input_txt])
                self.menu_dict[key][2].append([p.pid, input_txt])
                print(f'{p.pid} is started for {input_txt}')
            time.sleep(2)

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
