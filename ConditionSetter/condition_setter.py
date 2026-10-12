"""Tkinter client for saving and applying named sets of scalar Tango attributes.

Run directly, or with ``python -m ConditionSetter.condition_setter``.
Use ``--file PATH`` to work with a different comma-separated condition file.
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


DEFAULT_FILE = Path(r"Z:\software\Condition_setter\condition_list.txt")
CONDITION_HEADER = "name_of_condition"
REFRESH_MS = 1000


class ConditionStore:
    """Human-editable CSV; blank cells mean an attribute is not part of a condition."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return [], {}
        with self.path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = csv.reader(stream, strict=True)
            header = next(rows, None)
            if header is None:
                return [], {}
            header = [cell.strip() for cell in header]
            if not header or header[0] != CONDITION_HEADER:
                raise ValueError(f"First column must be '{CONDITION_HEADER}'.")
            attributes = header[1:]
            if any(not name for name in attributes) or len(set(attributes)) != len(attributes):
                raise ValueError(
                    "Attribute headers must be nonempty and unique.")
            conditions = {}
            for row in rows:
                if not row or all(cell == "" for cell in row):
                    continue
                if len(row) > len(header):
                    raise ValueError(
                        f"Too many columns at CSV line {rows.line_num}.")
                name = row[0].strip()
                if not name or name in conditions:
                    raise ValueError(
                        f"Missing or duplicate condition name at CSV line {rows.line_num}.")
                # Do not strip values: whitespace can be significant in a string attribute.
                conditions[name] = {
                    attribute: value for attribute, value in zip(attributes, row[1:])
                    if value != ""
                }
            return attributes, conditions

    def save(self, name, values, overwrite=False):
        name = name.strip()
        if not name:
            raise ValueError("Enter a condition name.")
        if not values:
            raise ValueError(
                "Add at least one attribute with a nonempty value.")
        if any(not attribute.strip() for attribute in values):
            raise ValueError("Attribute names cannot be empty.")
        if any(value == "" for value in values.values()):
            raise ValueError(
                "Empty values cannot be saved: blank cells mean unused attributes.")
        # Re-read here so manual edits and additions from other windows are preserved.
        attributes, conditions = self.load()
        if name in conditions and not overwrite:
            raise FileExistsError(f"Condition '{name}' already exists.")
        attributes.extend(
            attribute for attribute in values if attribute not in attributes)
        conditions[name] = dict(values)
        self._write(attributes, conditions)

    def delete(self, name):
        """Remove a condition and headers unused by all remaining conditions."""
        # Work from the latest file rather than the GUI's cached condition list.
        attributes, conditions = self.load()
        if name not in conditions:
            raise ValueError(
                f"Condition '{name}' no longer exists. Reload the file.")
        del conditions[name]
        used = {attribute for entries in conditions.values()
                for attribute in entries}
        attributes = [
            attribute for attribute in attributes if attribute in used]
        self._write(attributes, conditions)

    def _write(self, attributes, conditions):
        """Replace the file only after the complete CSV has been written."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="", dir=self.path.parent,
                    prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as stream:
                temporary = Path(stream.name)
                writer = csv.writer(stream)
                writer.writerow([CONDITION_HEADER, *attributes])
                for condition, entries in conditions.items():
                    writer.writerow(
                        [condition, *(entries.get(attribute, "") for attribute in attributes)])
            os.replace(temporary, self.path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def scalar_text(value):
    if value is None:
        raise ValueError("Attribute has no current value.")
    text = str(value)
    if text == "":
        raise ValueError(
            "Empty strings cannot be saved: blank cells mean unused attributes.")
    return text


def convert_value(text, config, tango):
    """Convert only when writing, using the device's actual scalar attribute type."""
    if config.data_format != tango.AttrDataFormat.SCALAR:
        raise ValueError(
            "Only scalar attributes are supported (no arrays or images).")
    kind = config.data_type
    types = tango.CmdArgType
    if kind == types.DevString:
        return text
    if kind == types.DevBoolean:
        normalized = text.strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
        raise ValueError("Boolean values must be true, false, 1, or 0.")
    if kind in (types.DevFloat, types.DevDouble):
        return float(text)
    if kind in (
            types.DevShort, types.DevLong, types.DevLong64, types.DevUShort,
            types.DevULong, types.DevULong64, types.DevUChar,
    ):
        return int(text)
    raise ValueError(f"Unsupported attribute type: {kind}.")


class TangoClient:
    """Used exclusively on a window's worker thread; importing the GUI needs no Tango."""

    def __init__(self):
        self.proxies = {}

    def proxy(self, name):
        import tango

        if name not in self.proxies:
            proxy = tango.AttributeProxy(name)
            proxy.get_device_proxy().set_timeout_millis(3000)
            self.proxies[name] = proxy
        return self.proxies[name]

    def read(self, name):
        import tango

        proxy = self.proxy(name)
        config = proxy.get_config()
        # Check support without attempting to stringify a spectrum/image.
        if config.data_format != tango.AttrDataFormat.SCALAR:
            raise ValueError("Only scalar attributes are supported.")
        return scalar_text(proxy.read().value)

    def write(self, name, text):
        import tango

        proxy = self.proxy(name)
        proxy.write(convert_value(text, proxy.get_config(), tango))


def read_values(client, names):
    values, errors = {}, {}
    for name in names:
        try:
            values[name] = client.read(name)
        except Exception as exc:
            errors[name] = str(exc)
    return values, errors


def write_values(client, entries, cancelled=None):
    """Issue writes left to right, stopping on the first error; never wait for motion."""
    written = []
    for name, value in entries:
        if cancelled is not None and cancelled.is_set():
            return written
        try:
            client.write(name, value)
        except Exception as exc:
            raise RuntimeError(
                f"Stopped at {name}: {exc}\n"
                f"{len(written)} earlier write(s) succeeded and were not undone. "
                "Remaining attributes were not written."
            ) from exc
        written.append(name)
    return written


class Worker:
    """Queue results for Tk to collect; background code must never call Tk."""

    def __init__(self):
        self.tasks = queue.Queue()
        self.results = queue.Queue()
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def submit(self, operation, callback):
        self.tasks.put((operation, callback))

    def run(self):
        while True:
            task = self.tasks.get()
            if task is None or self.closed.is_set():
                return
            operation, callback = task
            try:
                result, error = operation(), None
            except Exception as exc:
                result, error = None, exc
            self.results.put((callback, result, error))

    def close(self):
        self.closed.set()
        self.tasks.put(None)


class ConditionNameDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Please enter the name of this condition.").pack(
            pady=8)
        self.entry = ttk.Entry(master, width=40)
        self.entry.pack(padx=10, pady=8)
        return self.entry

    def buttonbox(self):
        box = ttk.Frame(self)
        ttk.Button(box, text="Save", command=self.ok).pack(
            side=tk.LEFT, padx=5, pady=8)
        ttk.Button(box, text="Cancel", command=self.cancel).pack(
            side=tk.LEFT, padx=5, pady=8)
        box.pack()
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        if not self.entry.get().strip():
            messagebox.showerror(
                "Condition name", "Enter a condition name.", parent=self)
            return False
        return True

    def apply(self):
        self.result = self.entry.get().strip()


class ConditionWindow(tk.Toplevel):
    def __init__(self, app, creating=False):
        super().__init__(app.root)
        self.app = app
        self.creating = creating
        self.title("Save conditions" if creating else "Load conditions")
        self.client = TangoClient()
        self.worker = Worker()
        self.conditions = {}
        self.columns = []
        self.monitor_names = ()
        self.read_pending = False
        self.writing = False
        self.closed = False
        self.refresh_id = None
        self.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        self.source_label = ttk.Label(
            outer, textvariable=app.source_text, wraplength=800)
        self.source_label.pack(anchor=tk.W, fill=tk.X, pady=(0, 8))
        self.canvas = tk.Canvas(outer, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            outer, orient=tk.HORIZONTAL, command=self.canvas.xview)
        scrollbar.pack(fill=tk.X)
        self.canvas.configure(xscrollcommand=scrollbar.set)
        self.table = ttk.LabelFrame(
            self.canvas, text="Create a condition" if creating else "Load a condition", padding=10,
        )
        self.canvas.create_window((0, 0), window=self.table, anchor=tk.NW)
        self.table.bind("<Configure>", lambda event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.status = tk.StringVar(
            value="Enter full Tango attribute names." if creating else "Select a condition.")
        ttk.Label(outer, textvariable=self.status, wraplength=800).pack(
            anchor=tk.W, pady=(10, 0))

        if creating:
            ttk.Button(self.table, text="Add an attribute column",
                       command=self.add_column).grid(row=0, column=0, padx=5)
        else:
            chooser = ttk.Frame(self.table)
            chooser.grid(row=0, column=0, padx=5, sticky="nw")
            self.selection = tk.StringVar()
            self.combo = ttk.Combobox(chooser, textvariable=self.selection, state="readonly", width=25,
                                      postcommand=self.reload_conditions)
            self.combo.pack()
            self.combo.bind("<<ComboboxSelected>>", self.select_condition)
            file_actions = ttk.Frame(chooser)
            file_actions.pack(anchor=tk.W, pady=5)
            ttk.Button(file_actions, text="Reload file",
                       command=self.reload_conditions).pack(side=tk.LEFT)
            self.delete_button = ttk.Button(
                file_actions, text="Delete this condition", command=self.delete_condition,
                state=tk.DISABLED)
            self.delete_button.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(self.table, text="Current value").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=10)
        ttk.Label(self.table, text="Request value").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=10)
        # Share the attribute grid so action buttons use the same row heights.
        self.actions = {}
        if creating:
            self.actions[0] = ttk.Button(
                self.table, text="See current value", command=self.start_monitoring)
            self.actions[2] = ttk.Button(
                self.table, text="Save request value as", command=self.save_requests)
        else:
            self.set_all = ttk.Button(
                self.table, text="Set all", command=self.set_values)
            self.actions[3] = self.set_all
        self.actions[1] = ttk.Button(
            self.table, text="Save current as", command=self.save_current)
        if creating:
            for _ in range(3):
                self.add_column()
        else:
            self.reload_conditions()
        self.resize_table()
        self.poll_id = self.after(100, self.poll_results)

    def add_column(self, name="", request=""):
        column = len(self.columns) + 1
        name_var = tk.StringVar(value=name)
        request_var = tk.StringVar(value=request)
        current_var = tk.StringVar(value="")
        widgets = []
        for row, variable in enumerate((name_var, current_var, request_var)):
            if self.creating and row != 1:
                widget = ttk.Entry(self.table, textvariable=variable, width=30)
            else:
                widget = ttk.Label(
                    self.table, textvariable=variable, width=30, wraplength=220)
            if row == 1:
                widget.configure(background="lightgreen", foreground="black")
            widget.grid(row=row, column=column, padx=8, pady=8, sticky="w")
            widgets.append(widget)
        button = None
        if not self.creating:
            button = ttk.Button(
                self.table, text="Set", command=lambda: self.set_values([(name, request)]))
            button.grid(row=3, column=column, padx=8, pady=8, sticky=tk.W)
            widgets.append(button)
        self.columns.append({"name": name_var, "request": request_var, "current": current_var,
                             "widgets": widgets, "button": button})
        if self.creating:
            name_var.trace_add("write", self.names_changed)
        self.resize_table()

    def resize_table(self):
        for row, button in self.actions.items():
            button.grid(row=row, column=len(self.columns) + 1,
                        padx=(15, 5), pady=8, sticky="ew")
        self.update_idletasks()
        width = min(self.table.winfo_reqwidth() + 30,
                    max(400, self.winfo_screenwidth() - 100))
        self.canvas.configure(
            width=width, height=self.table.winfo_reqheight() + 10)
        self.source_label.configure(wraplength=width)
        self.update_idletasks()
        self.geometry(
            f"{width + 30}x{max(270, self.table.winfo_reqheight() + 118 + self.source_label.winfo_reqheight())}")

    def source_changed(self):
        self.stop_monitoring()
        if self.creating:
            # Keep offline drafts, but do not carry readbacks across sources.
            for column in self.columns:
                self.update_readback(column, "")
            self.resize_table()
            self.status.set("Source changed. Draft kept; click See current value to refresh.")
        else:
            self.selection.set("")
            self.reload_conditions()
            self.status.set("Source changed. Select a condition.")

    def names_changed(self, *args):
        self.stop_monitoring()
        for column in self.columns:
            self.update_readback(column, "")
        self.status.set(
            "Attribute names changed. Click See current value to start refreshing.")

    def reload_conditions(self):
        try:
            _, self.conditions = self.app.store.load()
        except Exception as exc:
            self.conditions = {}
            self.status.set(f"Cannot load file: {exc}")
        self.combo.configure(values=list(self.conditions))
        if self.selection.get() not in self.conditions:
            self.selection.set("")
        self.select_condition()

    def delete_condition(self):
        name = self.selection.get()
        if self.writing or name not in self.conditions:
            return
        if not messagebox.askyesno(
                "Delete condition?",
                f"Delete condition '{name}'?\n"
                "Attribute columns unused by all remaining conditions will also be removed.",
                parent=self, default=messagebox.NO):
            return
        try:
            self.app.store.delete(name)
        except Exception as exc:
            self.show_error(exc)
            return
        # Clear stale selections in every open Load window after the file is updated.
        self.reload_conditions()
        for window in list(self.app.windows):
            if window is not self and not window.creating:
                window.reload_conditions()
        self.status.set(
            f"Deleted condition '{name}' and removed unused attribute columns.")

    def select_condition(self, event=None):
        self.stop_monitoring()
        for column in self.columns:
            for widget in column["widgets"]:
                widget.destroy()
        self.columns.clear()
        entries = self.conditions.get(self.selection.get(), {})
        for name, value in entries.items():
            self.add_column(name, value)
        self.resize_table()
        self.update_write_buttons()
        if entries:
            self.monitor_names = tuple(entries)
            self.refresh()

    def names(self):
        names = [column["name"].get().strip()
                 for column in self.columns if column["name"].get().strip()]
        if not names:
            raise ValueError("Enter at least one full Tango attribute name.")
        if len(set(names)) != len(names):
            raise ValueError("Each Tango attribute may appear only once.")
        return tuple(names)

    def show_error(self, error):
        messagebox.showerror("Condition setter", str(error), parent=self)

    def start_monitoring(self):
        try:
            names = self.names()
        except ValueError as exc:
            self.show_error(exc)
            return
        self.stop_monitoring()
        self.monitor_names = names
        self.status.set("Reading current values…")
        self.refresh()

    def stop_monitoring(self):
        self.monitor_names = ()
        if self.refresh_id is not None:
            self.after_cancel(self.refresh_id)
            self.refresh_id = None

    def refresh(self):
        self.refresh_id = None
        if not self.monitor_names or self.closed:
            return
        if self.read_pending or self.writing:
            self.refresh_id = self.after(REFRESH_MS, self.refresh)
            return
        names = self.monitor_names
        store = self.app.store
        self.read_pending = True

        def finished(result, error):
            self.read_pending = False
            if store is not self.app.store or names != self.monitor_names:
                return
            if error:
                self.status.set(str(error))
            else:
                self.display_readings(*result)

        self.worker.submit(lambda: read_values(self.client, names), finished)
        self.refresh_id = self.after(REFRESH_MS, self.refresh)

    @staticmethod
    def update_readback(column, value):
        # Decimal detects exact zero without rounding tiny nonzero values to zero.
        try:
            is_zero = Decimal(str(value)).is_zero()
        except InvalidOperation:
            is_zero = False
        column["current"].set(value)
        column["widgets"][1].configure(
            background="red" if is_zero else "lightgreen", foreground="black")

    def display_readings(self, values, errors):
        for column in self.columns:
            name = column["name"].get().strip()
            if name in values or name in errors:
                self.update_readback(column, values.get(name, "Read error"))
        if errors:
            self.status.set(
                "; ".join(f"{name}: {error}" for name, error in errors.items()))
        elif not self.writing:
            self.status.set("Current values updated.")

    def save_requests(self):
        try:
            self.names()
            values = {}
            for column in self.columns:
                name = column["name"].get().strip()
                value = column["request"].get()
                if not name and value != "":
                    raise ValueError(
                        "A request value is missing its attribute name.")
                if name and value != "":
                    values[name] = value
            if not values:
                raise ValueError(
                    "Enter at least one request value. Blank values are omitted.")
            self.save_named(values)
        except Exception as exc:
            self.show_error(exc)

    def save_current(self):
        try:
            names = self.names()
        except ValueError as exc:
            self.show_error(exc)
            return
        self.status.set("Reading a fresh snapshot to save…")
        store = self.app.store

        def finished(result, error):
            if store is not self.app.store:
                return  # A snapshot requested for an old source must not save into the new one.
            if error:
                self.show_error(error)
                return
            values, errors = result
            if errors:
                self.show_error("Nothing saved. Could not read:\n" +
                                "\n".join(f"{n}: {e}" for n, e in errors.items()))
                return
            self.display_readings(values, errors)
            self.save_named(values)

        self.worker.submit(lambda: read_values(self.client, names), finished)

    def save_named(self, values):
        store = self.app.store
        dialog = ConditionNameDialog(self, title="Save condition")
        if dialog.result is None or store is not self.app.store:
            return
        try:
            try:
                self.app.store.save(dialog.result, values)
            except FileExistsError:
                if not messagebox.askyesno("Replace condition?", f"Replace condition '{dialog.result}'?", parent=self):
                    return
                self.app.store.save(dialog.result, values, overwrite=True)
            self.status.set(f"Saved condition '{dialog.result}'.")
        except Exception as exc:
            self.show_error(exc)

    def update_write_buttons(self):
        if self.creating:
            return
        self.delete_button.configure(
            state=tk.DISABLED if self.writing or self.selection.get() not in self.conditions
            else tk.NORMAL)
        state = tk.DISABLED if self.writing or not self.columns else tk.NORMAL
        self.set_all.configure(state=state)
        for column in self.columns:
            column["button"].configure(state=state)

    def set_values(self, entries=None):
        if self.writing:
            return
        if entries is None:
            entries = [(column["name"].get(), column["request"].get())
                       for column in self.columns]
        if not entries:
            return
        self.writing = True
        self.update_write_buttons()
        self.status.set("Writing requested values…")

        def finished(result, error):
            self.writing = False
            self.update_write_buttons()
            if error:
                self.status.set(
                    "Write stopped; some earlier writes may have succeeded.")
                self.show_error(error)
            else:
                self.status.set(
                    f"Issued {len(result)} write(s). Motor completion is not awaited.")

        self.worker.submit(lambda: write_values(
            self.client, entries, self.worker.closed), finished)

    def poll_results(self):
        # Schedule first: a modal dialog in a callback runs a nested Tk event loop.
        self.poll_id = self.after(100, self.poll_results)
        while not self.closed:
            try:
                callback, result, error = self.worker.results.get_nowait()
            except queue.Empty:
                break
            callback(result, error)

    def close(self):
        self.closed = True
        self.stop_monitoring()
        self.after_cancel(self.poll_id)
        self.worker.close()
        self.app.windows.discard(self)
        self.destroy()


class ConditionSetterApp:
    def __init__(self, root, path=DEFAULT_FILE):
        self.root = root
        self.store = ConditionStore(path)
        self.source_text = tk.StringVar(master=root, value=f"Source file: {self.store.path}")
        self.windows = set()
        root.title("Condition setter")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(root, padding=20)
        frame.pack()
        ttk.Button(frame, text="Load conditions", width=24,
                   command=self.open_load).pack(pady=6)
        ttk.Button(frame, text="Save conditions", width=24,
                   command=self.open_save).pack(pady=6)
        ttk.Button(frame, text="Select source file", width=24,
                   command=self.select_source_file).pack(pady=6)

    def select_source_file(self):
        if any(window.writing for window in self.windows):
            messagebox.showwarning(
                "Source file", "Wait for the current writes to finish before changing source files.",
                parent=self.root)
            return
        filename = filedialog.askopenfilename(
            parent=self.root, title="Select source file",
            initialdir=str(DEFAULT_FILE.parent),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filename:
            return
        try:
            store = ConditionStore(filename)
            if not store.path.is_file():
                raise FileNotFoundError(f"Source file not found: {store.path}")
            store.load()  # Reject unreadable or malformed CSV without changing the source.
        except Exception as exc:
            messagebox.showerror("Cannot select source file", str(exc), parent=self.root)
            return
        self.store = store
        self.source_text.set(f"Source file: {store.path}")
        for window in list(self.windows):
            window.source_changed()

    def open_load(self):
        self.windows.add(ConditionWindow(self))

    def open_save(self):
        self.windows.add(ConditionWindow(self, creating=True))

    def close(self):
        for window in list(self.windows):
            window.close()
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help="Comma-separated condition file")
    args = parser.parse_args(argv)
    root = tk.Tk()
    ConditionSetterApp(root, args.file)
    root.mainloop()


if __name__ == "__main__":
    main()
