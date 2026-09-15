import atexit
import sys
from functools import partial
from tkinter import E, N, S, W, StringVar, Tk, ttk

from common.start_menu import Menu


class Newmark(Menu):
    def __init__(self, root):
        super().__init__()
        self.get_class_related_info()
        root.title(f"{self.class_name} menu")
        self.menu_dict = {
            "start server": ["server.py", self.instances, []],
            "start GUI": ["GUI.py", self.device_names, []],
        }

        frame = ttk.Frame(root, padding="3 3 12 12")
        frame.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        style = ttk.Style()
        self.fontsize = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        style.configure("Sty1.TButton", font=("Helvetica", self.fontsize))
        style.configure("Sty1.TEntry", font=("Helvetica", self.fontsize))
        style.configure("Sty1.TCombobox", font=("Helvetica", self.fontsize))
        root.option_add("*TCombobox*Listbox.font", "Helvetica 20")

        for row, (label, values) in enumerate(self.menu_dict.items()):
            variable_name = values[0][:-3]
            setattr(self, variable_name, StringVar())
            combobox = ttk.Combobox(
                frame,
                textvariable=getattr(self, variable_name),
                font=("Helvetica", self.fontsize),
                width=25,
            )
            setattr(self, f"{variable_name}_combobox", combobox)
            combobox.grid(column=0, row=row, sticky=[N, E, S])
            combobox["values"] = values[1]

            ttk.Button(
                frame,
                text=label,
                command=partial(self.start_window, __file__, label),
                style="Sty1.TButton",
            ).grid(column=1, row=row, sticky=[W, E])
            ttk.Button(
                frame,
                text="X",
                command=partial(self.terminate, label),
                style="Sty1.TButton",
                width=5,
            ).grid(column=2, row=row, sticky=[W])

        for child in frame.winfo_children():
            # type: ignore[attr-defined]
            child.grid_configure(padx=(self.fontsize, 0), pady=3)


if __name__ == "__main__":
    root = Tk()
    menu = Newmark(root)
    atexit.register(menu.terminate_all)
    root.mainloop()
