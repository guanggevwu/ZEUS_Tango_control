from tkinter import *
from tkinter import ttk
import sys
import os
import platform
import subprocess
from functools import partial


class GentecMenu:
    def __init__(self, root):
        root.title("Gentec menu")
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

        venv_path = os.path.dirname(os.path.dirname(__file__))
        if platform.system() == 'Linux':
            self.python_path = os.path.join(venv_path, 'venv', 'bin', 'python')
        elif platform.system() == 'Windows':
            self.python_path = os.path.join(
                venv_path, 'venv', 'Scripts', 'python.exe')

        self.menu_dict = {'start server': 'gentec_server.py',
                          'start Taurus GUI': 'gentec_GUI.py', 'start Tkinter GUI': 'tkinter_GUI.py'}
        for idx, (key, value) in enumerate(self.menu_dict.items()):
            ttk.Button(frame1, text=f"{key}", command=partial(self.start_window, f'{key}'), style='Sty1.TButton').grid(
                column=0, row=idx, columnspan=1, sticky=[W, E])
            setattr(self, value[:-3], StringVar())
            ttk.Entry(frame1, textvariable=getattr(
                self, value[:-3]), style='Sty1.TEntry', font=('Helvetica', self.fontsize), width=10).grid(
                column=1, row=idx, columnspan=1, sticky=[N, E, S])
        for child in frame1.winfo_children():
            child.grid_configure(padx=[self.fontsize, 0], pady=3)
        key = '12'

    def start_window(self, key):
        script_path = os.path.join(
            os.path.dirname(__file__), self.menu_dict[key])
        input_txt = getattr(self, self.menu_dict[key][:-3]).get()
        # using os.system cause hang up in server code
        # os.system(
        #     f'{self.python_path} {script_path} {input_txt}')
        subprocess.Popen(
            f'{self.python_path} {script_path} {input_txt}', shell=True)
        print('done')


if __name__ == '__main__':
    root = Tk()
    dummy = GentecMenu(root)
    root.mainloop()
