from tkinter import *
from tkinter import ttk
import sys
import os
import platform
import subprocess
from functools import partial
import atexit
import signal


class Menu:
    def __init__(self, root):
        root.title("Laser warning sign menu")
        frame1 = ttk.Frame(root, padding="3 3 12 12")
        frame1.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        s = ttk.Style()
        self.fontsize = sys.argv[1] if len(sys.argv) > 1 else 20

        s.configure('Sty1.TButton',
                    font=('Helvetica', self.fontsize))
        s.configure('Sty1.TEntry',
                    font=('Helvetica', self.fontsize))
        root.option_add("*TCombobox*Listbox.font", "Helvetica 20")

        s.configure('Sty1.TCombobox',
                    font=('Helvetica', self.fontsize))

        venv_path = os.path.dirname(os.path.dirname(__file__))
        if platform.system() == 'Linux':
            self.python_path = os.path.join(venv_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                venv_path, 'venv', 'Scripts', 'python.exe')

        self.menu_dict = {'start server': [
            'server.py', ('testsr', 'laser_warning_sign_sr')], }
        for idx, (key, value) in enumerate(self.menu_dict.items()):
            setattr(self, value[0][:-3], StringVar())
            setattr(self, f'{value[0][:-3]}_combobox', ttk.Combobox(frame1, textvariable=getattr(
                self, value[0][:-3]),  font=('Helvetica', self.fontsize), width=15))
            getattr(self, f'{value[0][:-3]}_combobox').grid(
                column=0, row=idx, columnspan=1, sticky=[N, E, S])
            ttk.Button(frame1, text=f"{key}", command=partial(self.start_window, f'{key}'), style='Sty1.TButton').grid(
                column=1, row=idx, columnspan=1, sticky=[W, E])
            getattr(self, f'{value[0][:-3]}_combobox')['value'] = value[1]
            ttk.Button(frame1, text=f"X", command=partial(self.terminate, f'{key}'), style='Sty1.TButton', width=5).grid(
                column=2, row=idx, columnspan=1, sticky=[W])
        for child in frame1.winfo_children():
            child.grid_configure(padx=[self.fontsize, 0], pady=3)

    def start_window(self, key):
        script_path = os.path.join(
            os.path.dirname(__file__), self.menu_dict[key][0])
        input_txt = getattr(self, self.menu_dict[key][0][:-3]).get()
        # using os.system cause hang up in server code
        # os.system(
        #     f'{self.python_path} {script_path} {input_txt}')
        p = subprocess.Popen(
            f'{self.python_path} {script_path} {input_txt}')
        setattr(self, f'{self.menu_dict[key][0][:-3]}_subprocess', p.pid)
        print(f'{p.pid} is started')

    def terminate_all(self):
        for key, value in self.__dict__.items():
            if '_subprocess' in key:
                print(f'trying to kill {key} {value}')
                os.kill(value, signal.SIGTERM)

    def terminate(self, key):
        pid = getattr(self, f'{self.menu_dict[key][0][:-3]}_subprocess')
        print(f'try to kill {key} {pid}')
        os.kill(pid, signal.SIGTERM)


if __name__ == '__main__':
    root = Tk()
    dummy = Menu(root)
    atexit.register(dummy.terminate_all)
    root.mainloop()
