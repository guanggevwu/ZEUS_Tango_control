"""Condition-setter tests using temporary files and mocked Tango (no hardware)."""

import csv
import gc
from pathlib import Path
import tempfile
import threading
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import tango

from ConditionSetter import condition_setter as cs


A = "test/device/1/position"
B = "test/device/1/enabled"
C = "test/device/1/label"


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "nested" / "conditions.txt"
        self.store = cs.ConditionStore(self.path)

    def test_missing_file_is_empty_until_saved(self):
        self.assertEqual(self.store.load(), ([], {}))
        self.assertFalse(self.path.exists())
        self.store.save("first", {A: "1.0"})
        self.assertEqual(self.store.load(), ([A], {"first": {A: "1.0"}}))

    def test_new_columns_preserve_existing_rows_and_blanks(self):
        self.store.save("first", {A: "1.0", B: "True"})
        self.store.save("second", {A: "2.0", C: ' hello, "world"\nnext line '})
        attributes, conditions = self.store.load()
        self.assertEqual(attributes, [A, B, C])
        self.assertNotIn(C, conditions["first"])
        self.assertNotIn(B, conditions["second"])
        self.assertEqual(conditions["second"][C],
                         ' hello, "world"\nnext line ')
        with self.path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[1], ["first", "1.0", "True", ""])

    def test_overwrite_requires_permission_and_replaces_whole_condition(self):
        self.store.save("first", {A: "1", B: "true"})
        with self.assertRaises(FileExistsError):
            self.store.save("first", {A: "2"})
        self.assertEqual(self.store.load()[1]["first"][A], "1")
        self.store.save("first", {A: "2"}, overwrite=True)
        self.assertEqual(self.store.load(), ([A, B], {"first": {A: "2"}}))

    def test_manual_edits_are_reloaded_before_save(self):
        self.store.save("first", {A: "1"})
        self.path.write_text(
            f"\ufeffname_of_condition,{A},{B}\nmanual,5,false\n", encoding="utf-8")
        self.store.save("next", {C: "offline text"})
        self.assertEqual(self.store.load()[1]["manual"], {A: "5", B: "false"})

    def test_short_rows_and_blank_lines(self):
        self.store.save("first", {A: "1", B: "true"})
        self.path.write_text(
            f"name_of_condition,{A},{B}\nfirst,1\n\n", encoding="utf-8")
        self.assertEqual(self.store.load()[1], {"first": {A: "1"}})

    def test_malformed_files_are_not_overwritten(self):
        self.path.parent.mkdir()
        for content in (
            "\n",
            "wrong,attribute\nfirst,1\n",
            f"name_of_condition,{A},{A}\nfirst,1,2\n",
            f"name_of_condition,{A},\nfirst,1,2\n",
            f"name_of_condition,{A}\nfirst,1\nfirst,2\n",
            f"name_of_condition,{A}\nfirst,1,extra\n",
            f"name_of_condition,{A}\n,1\n",
        ):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.store.save("next", {A: "2"})
                self.assertEqual(self.path.read_text(
                    encoding="utf-8"), content)

    def test_unterminated_csv_quote_is_not_silently_saved(self):
        self.path.parent.mkdir()
        content = f'name_of_condition,{A}\nfirst,"unterminated\n'
        self.path.write_text(content, encoding="utf-8")
        with self.assertRaises(csv.Error):
            self.store.save("next", {A: "2"})
        self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_failed_replace_preserves_original_and_cleans_temporary_file(self):
        self.store.save("first", {A: "1"})
        with patch.object(cs.os, "replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                self.store.save("second", {B: "true"})
        self.assertEqual(self.store.load()[1], {"first": {A: "1"}})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_delete_prunes_unused_columns_and_preserves_order_and_values(self):
        self.store.save("remove", {A: "1", B: "true", C: "old"})
        self.store.save("keep", {A: "0", C: ' text, "quoted"\nnext '})
        self.store.delete("remove")
        self.assertEqual(self.store.load(), (
            [A, C], {"keep": {A: "0", C: ' text, "quoted"\nnext '}}))

    def test_delete_last_condition_leaves_header_and_allows_new_save(self):
        self.store.save("last", {A: "1"})
        self.store.delete("last")
        self.assertEqual(self.store.load(), ([], {}))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "name_of_condition\n")
        self.store.save("new", {B: "false"})
        self.assertEqual(self.store.load(), ([B], {"new": {B: "false"}}))

    def test_delete_reloads_manual_edits_and_removes_preexisting_unused_headers(self):
        self.store.save("remove", {A: "1", B: "true"})
        self.path.write_text(
            f"name_of_condition,{A},{B},{C}\nremove,1,true,\nmanual,,false,\n",
            encoding="utf-8")
        self.store.delete("remove")
        self.assertEqual(self.store.load(), ([B], {"manual": {B: "false"}}))

    def test_delete_missing_condition_does_not_modify_file(self):
        with self.assertRaises(ValueError):
            self.store.delete("missing")
        self.assertFalse(self.path.exists())
        self.store.save("keep", {A: "1"})
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.delete("missing")
        self.assertEqual(self.path.read_bytes(), original)

    def test_failed_delete_preserves_original_and_cleans_temporary_file(self):
        self.store.save("keep", {A: "1"})
        original = self.path.read_bytes()
        with patch.object(cs.os, "replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                self.store.delete("keep")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_delete_rejects_malformed_file_without_modifying_it(self):
        self.store.save("keep", {A: "1"})
        self.path.write_text("wrong,header\nkeep,1\n", encoding="utf-8")
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.delete("keep")
        self.assertEqual(self.path.read_bytes(), original)

    def test_empty_inputs_rejected(self):
        for name, values in (("", {A: "1"}), ("first", {}), ("first", {A: ""})):
            with self.subTest(name=name, values=values), self.assertRaises(ValueError):
                self.store.save(name, values)


class TangoTests(unittest.TestCase):
    def config(self, kind, scalar=True):
        return SimpleNamespace(data_type=kind, data_format=(
            tango.AttrDataFormat.SCALAR if scalar else tango.AttrDataFormat.SPECTRUM))

    def test_supported_types(self):
        for kind, text, expected in (
            (tango.DevString, "  a,b  ", "  a,b  "),
            (tango.DevBoolean, "TRUE", True),
            (tango.DevBoolean, " false ", False),
            (tango.DevBoolean, "1", True),
            (tango.DevBoolean, "0", False),
            (tango.DevDouble, "1.2e3", 1200.0),
            (tango.DevFloat, "-1.5", -1.5),
            (tango.DevLong64, "9007199254740993", 9007199254740993),
            (tango.DevULong, "12", 12),
        ):
            with self.subTest(kind=kind, text=text):
                actual = cs.convert_value(text, self.config(kind), tango)
                self.assertEqual(actual, expected)
                self.assertIs(type(actual), type(expected))

    def test_invalid_values_and_arrays_rejected(self):
        for kind, text, scalar in (
            (tango.DevBoolean, "yes", True),
            (tango.DevLong, "1.2", True),
            (tango.DevDouble, "text", True),
            (tango.DevString, "array", False),
            (tango.DevState, "ON", True),
        ):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                cs.convert_value(text, self.config(kind, scalar), tango)

    def test_client_uses_metadata_and_caches_proxy(self):
        with patch.object(tango, "AttributeProxy") as factory:
            proxy = factory.return_value
            proxy.get_config.return_value = self.config(tango.DevBoolean)
            proxy.read.return_value.value = True
            client = cs.TangoClient()
            self.assertEqual(client.read(B), "True")
            client.write(B, "false")
            factory.assert_called_once_with(B)
            proxy.get_device_proxy.return_value.set_timeout_millis.assert_called_once_with(
                3000)
            proxy.write.assert_called_once_with(False)

    def test_read_errors_do_not_prevent_other_readbacks(self):
        client = Mock()
        client.read.side_effect = ["1", RuntimeError("offline"), "text"]
        self.assertEqual(cs.read_values(client, [A, B, C]), ({
                         A: "1", C: "text"}, {B: "offline"}))

    def test_writes_are_ordered_and_stop_at_failure(self):
        client = Mock()
        client.write.side_effect = [None, RuntimeError("failed"), None]
        with self.assertRaisesRegex(RuntimeError, "1 earlier write"):
            cs.write_values(client, [(A, "1"), (B, "true"), (C, "text")])
        self.assertEqual(client.write.call_args_list, [
                         call(A, "1"), call(B, "true")])

    def test_writes_do_not_read_or_wait_for_motion(self):
        client = Mock()
        self.assertEqual(cs.write_values(
            client, [(A, "1"), (B, "false")]), [A, B])
        client.read.assert_not_called()
        self.assertEqual(client.write.call_args_list, [
                         call(A, "1"), call(B, "false")])

    def test_close_cancels_remaining_writes(self):
        event = threading.Event()
        client = Mock()
        client.write.side_effect = lambda *args: event.set()
        self.assertEqual(cs.write_values(
            client, [(A, "1"), (B, "true")], event), [A])
        client.write.assert_called_once_with(A, "1")

    def test_empty_readback_cannot_be_saved_as_unused_attribute(self):
        for value in (None, ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cs.scalar_text(value)

    def test_worker_queues_results_and_survives_errors(self):
        worker = cs.Worker()
        self.addCleanup(worker.close)
        callback = Mock()
        worker.submit(lambda: 1 / 0, callback)
        received, result, error = worker.results.get(timeout=3)
        self.assertIs(received, callback)
        self.assertIsNone(result)
        self.assertIsInstance(error, ZeroDivisionError)
        callback.assert_not_called()
        worker.submit(lambda: 42, callback)
        self.assertEqual(worker.results.get(timeout=3), (callback, 42, None))


class GuiTests(unittest.TestCase):
    """Real Tk widgets; all attribute access stays mocked."""

    def setUp(self):
        gc.collect()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.root.withdraw()
        self.app = cs.ConditionSetterApp(self.root, Path(
            self.temporary.name) / "conditions.txt")
        # Drain initial ttk theme events even in tests that never open a child window.
        self.root.update_idletasks()
        self.addCleanup(self.close_app)
        self.client = Mock()
        self.client.read.return_value = "12"
        patcher = patch.object(cs, "TangoClient", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def close_app(self):
        workers = [window.worker for window in self.app.windows]
        self.app.close()
        for worker in workers:
            worker.thread.join(timeout=3)
        # Collect Tk reference cycles on the main thread, not a later test's worker.
        gc.collect()

    def window(self, creating=False):
        window = cs.ConditionWindow(self.app, creating=creating)
        self.app.windows.add(window)
        window.withdraw()
        return window

    def finish_task(self, window):
        callback, result, error = window.worker.results.get(timeout=3)
        callback(result, error)

    def test_default_source_and_root_buttons(self):
        frame = self.root.winfo_children()[0]
        self.assertEqual([widget.cget("text") for widget in frame.winfo_children()],
                         ["Load conditions", "Save conditions", "Select source file"])
        with patch.object(cs.tk, "Tk") as root, patch.object(cs, "ConditionSetterApp") as app:
            cs.main([])
        app.assert_called_once_with(root.return_value, cs.DEFAULT_FILE)
        self.assertEqual(str(cs.DEFAULT_FILE), r"Z:\software\Condition_setter\condition_list.txt")

    def test_source_picker_cancel_keeps_current_source_and_uses_default_directory(self):
        original = self.app.store
        with patch.object(cs.filedialog, "askopenfilename", return_value="") as picker:
            self.app.select_source_file()
        self.assertIs(self.app.store, original)
        self.assertEqual(picker.call_args.kwargs["initialdir"], str(cs.DEFAULT_FILE.parent))
        self.assertIn(("Text files", "*.txt"), picker.call_args.kwargs["filetypes"])

    def test_switch_source_updates_windows_and_routes_saves_and_deletes(self):
        original = self.app.store
        original.save("same", {A: "1"})
        original_bytes = original.path.read_bytes()
        selected = cs.ConditionStore(Path(self.temporary.name) / "selected.txt")
        selected.save("same", {B: "false"})
        load = self.window()
        save = self.window(creating=True)
        load.selection.set("same")
        load.select_condition()
        self.finish_task(load)
        save.columns[0]["name"].set(C)
        save.columns[0]["request"].set("draft text")
        save.start_monitoring()
        self.finish_task(save)
        with patch.object(cs.filedialog, "askopenfilename", return_value=str(selected.path)):
            self.app.select_source_file()
        self.assertEqual(self.app.store.path, selected.path)
        for window in (load, save, self.window(), self.window(creating=True)):
            self.assertEqual(window.source_label.cget("text"), f"Source file: {selected.path}")
        self.assertEqual(load.selection.get(), "")
        self.assertEqual(load.columns, [])
        self.assertEqual(load.conditions, {"same": {B: "false"}})
        self.assertEqual(save.columns[0]["request"].get(), "draft text")
        self.assertEqual(save.columns[0]["current"].get(), "")
        self.assertEqual(save.monitor_names, ())
        with patch.object(cs, "ConditionNameDialog", return_value=SimpleNamespace(result="draft")):
            save.save_requests()
        self.assertEqual(selected.load()[1]["draft"], {C: "draft text"})
        load.selection.set("same")
        load.select_condition()
        self.finish_task(load)
        with patch.object(cs.messagebox, "askyesno", return_value=True):
            load.delete_condition()
        self.assertEqual(selected.load(), ([C], {"draft": {C: "draft text"}}))
        self.assertEqual(original.path.read_bytes(), original_bytes)
        self.client.write.assert_not_called()

    def test_invalid_source_keeps_existing_source_and_labels(self):
        window = self.window(creating=True)
        original = self.app.store
        bad_file = Path(self.temporary.name) / "bad.txt"
        bad_file.write_text("wrong,header\n", encoding="utf-8")
        for path in (bad_file, bad_file.with_name("missing.txt")):
            with self.subTest(path=path), \
                    patch.object(cs.filedialog, "askopenfilename", return_value=str(path)), \
                    patch.object(cs.messagebox, "showerror") as error:
                self.app.select_source_file()
            error.assert_called_once()
            self.assertIs(self.app.store, original)
            self.assertEqual(window.source_label.cget("text"), f"Source file: {original.path}")

    def test_pending_snapshot_does_not_save_to_new_source(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        window.save_current()
        selected = cs.ConditionStore(Path(self.temporary.name) / "selected.txt")
        selected.save("existing", {B: "false"})
        with patch.object(cs.filedialog, "askopenfilename", return_value=str(selected.path)):
            self.app.select_source_file()
        with patch.object(cs, "ConditionNameDialog") as dialog:
            self.finish_task(window)
        dialog.assert_not_called()
        self.assertEqual(selected.load()[1], {"existing": {B: "false"}})

    def test_pending_readback_from_previous_source_is_discarded(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        window.start_monitoring()
        selected = Path(self.temporary.name) / "empty.txt"
        selected.write_text("name_of_condition\n", encoding="utf-8")
        with patch.object(cs.filedialog, "askopenfilename", return_value=str(selected)):
            self.app.select_source_file()
        window.start_monitoring()  # Same attribute, but a different source generation.
        self.finish_task(window)
        self.assertEqual(window.columns[0]["current"].get(), "")
        self.assertFalse(window.read_pending)

    def test_source_change_is_blocked_during_writes(self):
        window = self.window()
        window.writing = True
        with patch.object(cs.filedialog, "askopenfilename") as picker, \
                patch.object(cs.messagebox, "showwarning") as warning:
            self.app.select_source_file()
        picker.assert_not_called()
        warning.assert_called_once()

    def test_load_starts_empty_and_hides_unused_attributes(self):
        self.app.store.save("first", {A: "1", B: "true"})
        self.app.store.save("second", {C: "text"})
        window = self.window()
        self.assertEqual(window.columns, [])
        self.assertEqual(window.monitor_names, ())
        self.client.read.assert_not_called()
        window.selection.set("second")
        window.select_condition()
        self.assertEqual([column["name"].get()
                         for column in window.columns], [C])
        self.finish_task(window)
        self.assertEqual(window.columns[0]["current"].get(), "12")
        self.assertEqual(window.columns[0]["request"].get(), "text")
        self.client.write.assert_not_called()

    def test_action_buttons_align_with_attribute_rows(self):
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        for creating in (False, True):
            with self.subTest(creating=creating):
                window = self.window(creating=creating)
                if not creating:
                    window.add_column(A, "1")
                rows = {"Save current as": 1}
                rows.update({"See current value": 0, "Save request value as": 2}
                            if creating else {"Set all": 3})
                for extra_column in (False, True):
                    if extra_column:
                        window.add_column(B, "2")
                    window.update_idletasks()
                    buttons = {widget.cget("text"): widget for widget in descendants(window.table)
                               if widget.winfo_class() == "TButton"}
                    for text, row in rows.items():
                        button = buttons[text]
                        for column in window.columns:
                            widget = column["widgets"][row]
                            button_center = button.winfo_rooty() + button.winfo_height() / 2
                            widget_center = widget.winfo_rooty() + widget.winfo_height() / 2
                            self.assertAlmostEqual(button_center, widget_center, delta=1,
                                                   msg=f"{text}, extra column: {extra_column}")
                window.close()

    def test_delete_button_is_beside_reload_and_requires_selection(self):
        window = self.window()
        button = window.delete_button
        self.assertEqual(button.cget("text"), "Delete this condition")
        reload_button = next(widget for widget in button.master.winfo_children()
                             if widget.cget("text") == "Reload file")
        window.update_idletasks()
        self.assertGreater(button.winfo_x(), reload_button.winfo_x())
        self.assertEqual(button.winfo_y(), reload_button.winfo_y())
        self.assertTrue(button.instate(["disabled"]))
        with patch.object(cs.messagebox, "askyesno") as confirm:
            window.delete_condition()
        confirm.assert_not_called()

    def test_delete_confirmation_cancel_preserves_file_and_selection(self):
        self.app.store.save("keep", {A: "1"})
        window = self.window()
        window.selection.set("keep")
        window.select_condition()
        self.finish_task(window)
        self.assertFalse(window.delete_button.instate(["disabled"]))
        original = self.app.store.path.read_bytes()
        with patch.object(cs.messagebox, "askyesno", return_value=False) as confirm:
            window.delete_button.invoke()
        confirm.assert_called_once()
        self.assertEqual(self.app.store.path.read_bytes(), original)
        self.assertEqual(window.selection.get(), "keep")
        self.assertEqual(window.monitor_names, (A,))

    def test_delete_refreshes_load_windows_and_ignores_pending_readbacks(self):
        self.app.store.save("remove", {A: "1", B: "true"})
        self.app.store.save("keep", {B: "false"})
        windows = [self.window(), self.window()]
        for window in windows:
            window.selection.set("remove")
            window.select_condition()
        with patch.object(cs.messagebox, "askyesno", return_value=True):
            windows[0].delete_button.invoke()
        self.assertEqual(self.app.store.load(), ([B], {"keep": {B: "false"}}))
        for window in windows:
            self.finish_task(window)
            self.assertEqual(window.selection.get(), "")
            self.assertEqual(tuple(window.combo.cget("values")), ("keep",))
            self.assertEqual(window.columns, [])
            self.assertEqual(window.monitor_names, ())
            self.assertIsNone(window.refresh_id)
            self.assertTrue(window.delete_button.instate(["disabled"]))
        self.client.write.assert_not_called()

    def test_failed_delete_keeps_selection_and_shows_error(self):
        self.app.store.save("keep", {A: "1"})
        window = self.window()
        window.selection.set("keep")
        window.select_condition()
        self.finish_task(window)
        with patch.object(cs.messagebox, "askyesno", return_value=True), \
                patch.object(self.app.store, "delete", side_effect=PermissionError("locked")), \
                patch.object(cs.messagebox, "showerror") as error:
            window.delete_condition()
        error.assert_called_once()
        self.assertEqual(window.selection.get(), "keep")
        self.assertEqual(self.app.store.load(), ([A], {"keep": {A: "1"}}))

    def test_delete_is_disabled_while_writing(self):
        self.app.store.save("keep", {A: "1"})
        window = self.window()
        window.selection.set("keep")
        window.select_condition()
        self.finish_task(window)
        window.set_values()
        self.assertTrue(window.delete_button.instate(["disabled"]))
        with patch.object(cs.messagebox, "askyesno") as confirm:
            window.delete_condition()
        confirm.assert_not_called()
        self.finish_task(window)
        self.assertFalse(window.delete_button.instate(["disabled"]))

    def test_zero_readbacks_are_red_in_both_windows(self):
        for creating in (False, True):
            with self.subTest(creating=creating):
                window = self.window(creating=creating)
                if creating:
                    window.columns[0]["name"].set(A)
                else:
                    window.add_column(A, "1")
                column = window.columns[0]
                label = column["widgets"][1]
                for value in ("0", "0.0", "-0.0", "0e10", " 0 "):
                    window.display_readings({A: value}, {})
                    self.assertEqual(str(label.cget("background")), "red")
                    self.assertEqual(column["current"].get(), value)
                for value in ("1", "-0.01", "1e-999", "False", "text", "NaN", ""):
                    window.display_readings({A: "0"}, {})
                    window.display_readings({A: value}, {})
                    self.assertEqual(
                        str(label.cget("background")), "lightgreen")
                window.display_readings({A: "0"}, {})
                window.display_readings({}, {A: "offline"})
                self.assertEqual(column["current"].get(), "Read error")
                self.assertEqual(str(label.cget("background")), "lightgreen")

    def test_editing_attribute_name_clears_zero_highlight(self):
        window = self.window(creating=True)
        column = window.columns[0]
        column["name"].set(A)
        window.display_readings({A: "0"}, {})
        column["name"].set(B)
        self.assertEqual(column["current"].get(), "")
        self.assertEqual(
            str(column["widgets"][1].cget("background")), "lightgreen")

    def test_save_requests_works_offline_and_adds_columns(self):
        window = self.window(creating=True)
        self.assertEqual(len(window.columns), 3)
        window.add_column()
        self.assertEqual(len(window.columns), 4)
        window.columns[0]["name"].set(A)
        window.columns[0]["request"].set("2.5")
        window.columns[1]["name"].set(B)
        window.columns[1]["request"].set("false")
        with patch.object(cs, "ConditionNameDialog", return_value=SimpleNamespace(result="offline")):
            window.save_requests()
        self.assertEqual(self.app.store.load()[1], {
                         "offline": {A: "2.5", B: "false"}})
        self.assertEqual(self.client.mock_calls, [])

    def test_monitor_starts_on_button_and_stops_on_name_edit(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        self.assertEqual(window.monitor_names, ())
        self.client.read.assert_not_called()
        window.start_monitoring()
        self.finish_task(window)
        self.assertEqual(window.columns[0]["current"].get(), "12")
        self.assertEqual(window.monitor_names, (A,))
        self.assertIsNotNone(window.refresh_id)
        window.columns[0]["name"].set(B)
        self.assertEqual(window.monitor_names, ())
        self.assertIsNone(window.refresh_id)
        self.assertEqual(window.columns[0]["current"].get(), "")

    def test_save_current_uses_fresh_values(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        window.columns[0]["current"].set("stale")
        with patch.object(cs, "ConditionNameDialog", return_value=SimpleNamespace(result="snapshot")):
            window.save_current()
            self.finish_task(window)
        self.assertEqual(self.app.store.load()[1], {"snapshot": {A: "12"}})
        self.assertEqual(window.monitor_names, ())

    def test_failed_snapshot_does_not_save_partial_condition(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        window.columns[1]["name"].set(B)
        self.client.read.side_effect = ["12", RuntimeError("offline")]
        with patch.object(cs.messagebox, "showerror") as error:
            window.save_current()
            self.finish_task(window)
        error.assert_called_once()
        self.assertEqual(self.app.store.load(), ([], {}))

    def test_overwrite_confirmation(self):
        self.app.store.save("existing", {A: "1"})
        window = self.window(creating=True)
        with patch.object(cs, "ConditionNameDialog", return_value=SimpleNamespace(result="existing")):
            with patch.object(cs.messagebox, "askyesno", return_value=False):
                window.save_named({B: "false"})
            self.assertEqual(self.app.store.load()[1]["existing"], {A: "1"})
            with patch.object(cs.messagebox, "askyesno", return_value=True):
                window.save_named({B: "false"})
        self.assertEqual(self.app.store.load()[1]["existing"], {B: "false"})

    def test_reload_updates_selected_request_values(self):
        self.app.store.save("first", {A: "1"})
        window = self.window()
        window.selection.set("first")
        window.select_condition()
        self.finish_task(window)
        self.app.store.save("first", {B: "false"}, overwrite=True)
        window.reload_conditions()
        self.assertEqual(window.columns[0]["name"].get(), B)
        self.assertEqual(window.columns[0]["request"].get(), "false")
        self.finish_task(window)

    def test_set_all_disables_buttons_and_reports_failure(self):
        self.app.store.save("first", {A: "1", B: "true", C: "text"})
        window = self.window()
        window.selection.set("first")
        window.select_condition()
        self.finish_task(window)
        self.client.write.side_effect = [None, RuntimeError("failed")]
        window.set_values()
        self.assertTrue(window.writing)
        self.assertTrue(window.set_all.instate(["disabled"]))
        with patch.object(cs.messagebox, "showerror") as error:
            self.finish_task(window)
        error.assert_called_once()
        self.assertFalse(window.writing)
        self.assertFalse(window.set_all.instate(["disabled"]))
        self.assertEqual(self.client.write.call_args_list,
                         [call(A, "1"), call(B, "true")])

    def test_close_cancels_timers_and_worker(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        window.start_monitoring()
        window.close()
        self.assertTrue(window.worker.closed.is_set())
        self.assertIsNone(window.refresh_id)
        self.assertNotIn(window, self.app.windows)

    def test_tk_event_loop_polls_and_refreshes_again(self):
        window = self.window(creating=True)
        window.columns[0]["name"].set(A)
        self.client.read.side_effect = ["first", "second", "third"]
        window.start_monitoring()
        # Exercise actual Tk timers and result dispatch without contacting devices.
        self.root.after(1600, self.root.quit)
        self.root.mainloop()
        self.assertGreaterEqual(self.client.read.call_count, 2)
        self.assertEqual(window.columns[0]["current"].get(), "second")


if __name__ == "__main__":
    unittest.main()
