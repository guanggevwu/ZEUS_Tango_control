"""Regression tests; never load a real DLL or connect to a motor."""

import ctypes
import logging
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from Newmark.server import Newmark


class ThreadLocalDLL:
    """Model the handle lookup via TlsGetValue in the supplied SiUSBXp DLL."""

    def __init__(self):
        self.local = threading.local()
        self.calls = []
        self.fail_send = False
        self.fail_flush = False
        self.serials = [b"SERIAL-A", b"SERIAL-B"]
        self.fail_serial = False
        self.opened_index = None
        self.fnPerformaxComGetNumDevices = Mock(side_effect=self.enumerate)
        self.fnPerformaxComGetProductString = Mock(side_effect=self.product)
        self.fnPerformaxComSetTimeouts = Mock(side_effect=self.timeouts)
        self.fnPerformaxComOpen = Mock(side_effect=self.open)
        self.fnPerformaxComFlush = Mock(side_effect=self.flush)
        self.fnPerformaxComSendRecv = Mock(side_effect=self.send)
        self.fnPerformaxComClose = Mock(side_effect=self.close)

    def record(self, name):
        self.calls.append((name, threading.get_ident()))

    def enumerate(self, count):
        self.record("enumerate")
        ctypes.cast(count, ctypes.POINTER(ctypes.c_ulong))[0] = len(self.serials)
        return 1

    def product(self, index, buffer, option):
        self.record("product")
        assert len(buffer) == 256
        assert option == 0
        if self.fail_serial:
            return 0
        buffer.value = self.serials[index]
        return 1

    def timeouts(self, read, write):
        self.record("timeouts")
        assert read == write == 2000
        return 1

    def open(self, index, handle):
        self.record("open")
        self.opened_index = index
        self.local.handle = 123
        ctypes.cast(handle, ctypes.POINTER(ctypes.c_void_p))[0] = 123
        return 1

    def valid(self, handle):
        return getattr(self.local, "handle", None) == handle.value

    def flush(self, handle):
        self.record("flush")
        return int(self.valid(handle) and not self.fail_flush)

    def send(self, handle, output, write_size, read_size, reply):
        self.record("send")
        assert write_size == read_size == 64
        if not self.valid(handle) or self.fail_send:
            return 0
        assert not output.value.startswith(b"@")
        reply.value = b"0\r"
        return 1

    def close(self, handle):
        self.record("close")
        if not self.valid(handle):
            return 0
        self.local.handle = None
        return 1


class USBThreadTests(unittest.TestCase):
    def setUp(self):
        self.dll = ThreadLocalDLL()
        self.device = Newmark.__new__(Newmark)
        self.device.logger = logging.getLogger("newmark-test")
        self.device._serial_lock = threading.RLock()
        self.device._performax = None
        self.device._usb_handle = ctypes.c_void_p()
        self.device._device_address = "01"
        self.device._error_message = ""
        self.device._message = ""
        self.addCleanup(self.device._close_connection)

    def open(self, index=0, serial=""):
        with patch("Newmark.server.ctypes.WinDLL", return_value=self.dll):
            return self.device._open_usb_connection(index, 2.0, "", serial)

    def test_serial_selects_matching_controller_on_worker(self):
        self.assertEqual(self.open(index=99, serial="SERIAL-B"), 1)
        self.assertEqual(self.dll.opened_index, 1)
        self.assertEqual(self.device._usb_serial_number, "SERIAL-B")
        self.assertEqual(len({tid for _, tid in self.dll.calls}), 1)
        self.assertNotEqual(self.dll.calls[0][1], threading.get_ident())

    def test_empty_serial_uses_index(self):
        self.assertEqual(self.open(index=1), 1)
        self.assertEqual(self.dll.opened_index, 1)
        self.assertEqual(self.device._usb_serial_number, "SERIAL-B")

    def test_missing_serial_does_not_open_another_controller(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.open(serial="MISSING")
        self.assertIsNone(self.dll.opened_index)

    def test_duplicate_serial_is_rejected(self):
        self.dll.serials = [b"SAME", b"SAME"]
        with self.assertRaisesRegex(ValueError, "not unique"):
            self.open(serial="SAME")
        self.assertIsNone(self.dll.opened_index)

    def test_serial_read_failure_does_not_fall_back(self):
        self.dll.fail_serial = True
        with self.assertRaisesRegex(RuntimeError, "serial number"):
            self.open(serial="SERIAL-B")
        self.assertIsNone(self.dll.opened_index)

    def test_invalid_index_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid"):
            self.open(index=99)
        self.assertIsNone(self.dll.opened_index)

    def test_old_cross_thread_call_reproduces_failure(self):
        self.open()
        # Bypass dispatch as the previous implementation did: this thread
        # does not own the handle, despite having the same pointer value.
        with self.assertRaisesRegex(RuntimeError, "transaction failed"):
            self.device._send_usb_on_worker("MST")
        self.assertEqual(self.device._send_command("MST"), "0")

    def test_all_dll_calls_share_owner_thread(self):
        self.open()
        with ThreadPoolExecutor(max_workers=4) as callers:
            results = list(callers.map(
                self.device._send_command, ["MST", "PX", "EO", "@01MST"]
            ))
        self.assertEqual(results, ["0"] * 4)
        self.device._close_connection()
        owners = {tid for _, tid in self.dll.calls}
        self.assertEqual(len(owners), 1)
        self.assertNotIn(threading.get_ident(), owners)
        self.assertEqual(self.dll.calls[-1][0], "close")
        self.assertIsNone(self.device._usb_executor)

    def test_failed_write_is_not_replayed(self):
        self.open()
        self.dll.fail_send = True
        with self.assertRaisesRegex(RuntimeError, "transaction failed"):
            self.device._send_command("X100")
        self.assertEqual(self.dll.fnPerformaxComSendRecv.call_count, 1)
        self.assertEqual(self.dll.fnPerformaxComOpen.call_count, 1)
        self.assertEqual(self.dll.fnPerformaxComFlush.call_count, 1)

    def test_partial_initialization_closes_on_owner_thread(self):
        self.dll.fail_flush = True
        with self.assertRaisesRegex(RuntimeError, "could not flush"):
            self.open()
        self.assertEqual(self.dll.fnPerformaxComClose.call_count, 1)
        self.assertEqual(len({tid for _, tid in self.dll.calls}), 1)
        self.assertIsNone(self.device._usb_executor)

    def test_poll_error_is_reported_without_reopen(self):
        self.open()
        self.dll.fail_send = True
        with self.assertLogs("newmark-test", level="WARNING"):
            message = self.device.read_message()
        self.assertIn("MST communication error", message)
        self.assertIn("transaction failed", self.device._error_message)
        self.assertEqual(self.dll.fnPerformaxComOpen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
