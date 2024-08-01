from tkinter import *
from tkinter import ttk
import sys
import os
from functools import partial
import atexit

if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.start_menu import Menu


class BaslerMenu(Menu):
    def __init__(self, root):
        super().__init__()
        class_name = type(self).__name__.replace('Menu', '')
        root.title(f"{class_name} menu")
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

        device_names = self.db.get_device_name('*', class_name)
        instances = [e.split('/')[-1]
                     for e in self.servers if e.split('/')[0] == class_name]
        # list(self.combination_table_server) is just the keys, i.e., the text shown in the dropdown list.
        instances = list(self.combination_table_server)+(instances)
        self.menu_dict = {'start server': ['server.py', instances, []],
                          'start Taurus GUI': ['GUI.py', (*list(self.combination_table_client), *tuple(device_names.value_string)), []]}
        for idx, (key, value) in enumerate(self.menu_dict.items()):
            # value[0][:-3], i.e., 'gentec_server' is the attribute name
            setattr(self, value[0][:-3], StringVar())
            setattr(self, f'{value[0][:-3]}_combobox', ttk.Combobox(frame1, textvariable=getattr(
                self, value[0][:-3]),  font=('Helvetica', self.fontsize), width=15))
            getattr(self, f'{value[0][:-3]}_combobox').grid(
                column=0, row=idx, columnspan=1, sticky=[N, E, S])
            ttk.Button(frame1, text=f"{key}", command=partial(self.start_window, __file__, f'{key}'), style='Sty1.TButton').grid(
                column=1, row=idx, columnspan=1, sticky=[W, E])
            getattr(self, f'{value[0][:-3]}_combobox')['value'] = value[1]
            ttk.Button(frame1, text=f"X", command=partial(self.terminate, f'{key}'), style='Sty1.TButton', width=5).grid(
                column=2, row=idx, columnspan=1, sticky=[W])
        for child in frame1.winfo_children():
            child.grid_configure(padx=[self.fontsize, 0], pady=3)


if __name__ == '__main__':
    root = Tk()
    dummy = BaslerMenu(root)
    atexit.register(dummy.terminate_all)
    root.mainloop()
