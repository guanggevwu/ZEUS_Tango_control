from tkinter import *
from tkinter import ttk
import tango
import sys


class Gentec:
    def __init__(self, root):
        self.fontsize = 50
        if len(sys.argv) > 1:
            if sys.argv[1] == 'all':
                device_name = ['laser/gentec/MA1',
                               'laser/gentec/MA2', 'laser/gentec/MA3']
            else:
                device_name = [sys.argv[1]]
            if len(sys.argv) > 2:
                self.fontsize = sys.argv[2]
        self.dp = []
        for dn in device_name:
            self.dp.append(tango.DeviceProxy(dn))
        # attrs = self.dp.get_attribute_list()
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
            for device_idx, dp in enumerate(self.dp):
                setattr(self, f'{key}_{device_idx}', StringVar())
                ttk.Label(frame1, textvariable=getattr(self, f'{key}_{device_idx}'), style='Sty1.TLabel').grid(
                    column=1+device_idx, row=idx, sticky='W')

        for child in frame1.winfo_children():
            child.grid_configure(padx=[self.fontsize, 0], pady=3)
        self.update()

    def update(self):
        for key, value in self.required_list.items():
            for device_idx, dp in enumerate(self.dp):
                try:
                    getattr(self, f'{key}_{device_idx}').set(
                        getattr(self.dp[device_idx], key))
                except:
                    pass
        root.after(100, self.update)


if __name__ == '__main__':
    root = Tk()
    dummy = Gentec(root)
    root.mainloop()
