from tkinter import *
from tkinter import ttk
import tango
import sys


class Gentec:
    def __init__(self, root):
        self.fontsize = 50
        device_name = 'laser/gentec/1'
        if len(sys.argv) > 1:
            device_name = sys.argv[1]
            if len(sys.argv) > 2:
                self.fontsize = sys.argv[2]
        self.dp = tango.DeviceProxy(device_name)
        attrs = self.dp.get_attribute_list()
        self.required_list = {
            'name_attr': 'name', 'main_value': 'main value'}
        root.title("Simplified Gentec")
        frame1 = ttk.Frame(root, padding="3 3 12 12")
        frame1.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        s = ttk.Style()

        s.configure('Sty1.TLabel',
                    font=('Helvetica', self.fontsize))
        for idx, (key, value) in enumerate(self.required_list.items()):
            ttk.Label(frame1, text=f'{value}: ', style='Sty1.TLabel').grid(
                column=0, row=idx, sticky='W')

            setattr(self, key, StringVar())
            ttk.Label(frame1, textvariable=getattr(self, key), style='Sty1.TLabel').grid(
                column=1, row=idx, sticky='W')

        for child in frame1.winfo_children():
            child.grid_configure(padx=[self.fontsize, 0], pady=3)
        self.update()

    def update(self):
        for key, value in self.required_list.items():
            getattr(self, key).set(getattr(self.dp, key))
        root.after(100, self.update)


if __name__ == '__main__':
    root = Tk()
    dummy = Gentec(root)
    root.mainloop()
