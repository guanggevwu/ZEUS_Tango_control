from __future__ import annotations

import datetime
import ctypes
import functools
import logging
import os
import platform
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import serial
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property

from common.logger_adapter import LoggerAdapter


class Newmark(Device):
    """Tango server for a Newmark NSC-A1 single-axis stepper controller."""

    connection_type = device_property(dtype=str, default_value="usb")
    com = device_property(dtype=str, default_value="COM1")
    baudrate = device_property(dtype=int, default_value=9600)
    timeout = device_property(dtype=float, default_value=2.0)
    device_number = device_property(dtype=str, default_value="01")
    usb_device_index = device_property(dtype=int, default_value=0)
    dll_path = device_property(dtype=str, default_value="")
    axis_unit = device_property(dtype=str, default_value="steps")
    steps_per_unit = device_property(dtype=float, default_value=1.0)

    MOTOR_STATUS_BITS = {
        0: "moving at constant speed",
        1: "accelerating",
        2: "decelerating",
        3: "home input active",
        4: "negative limit active",
        5: "positive limit active",
        6: "negative limit error",
        7: "positive limit error",
        8: "latch input active",
        9: "encoder Z-index active",
        10: "communication timeout",
    }

    @staticmethod
    def clear_error_wrap(func):
        """Clear the cached error before a write-like operation."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self._error_message = ""
            return func(self, *args, **kwargs)

        return wrapper

    def init_device(self):
        self._base_logger = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter("Newmark", self._base_logger)
        logging.basicConfig(
            handlers=[logging.StreamHandler()],
            format="%(asctime)s %(message)s",
            level=logging.INFO,
        )

        super().init_device()
        self.set_state(DevState.INIT)
        self._close_connection()

        self.axis = [1]
        self._serial_lock = threading.RLock()
        self._error_message = ""
        self._message = ""
        self._raw_command_return = ""
        self._user_defined_locations = []
        self._user_defined_name = "newmark_nsc_a1"
        self._host_computer = platform.node()
        self._saved_location_source = "client"
        self._ax1_position = 0.0
        self._ax1_step = 0.0
        self._ax1_status = False
        self._set_ax1_as = "------------N/A-----------"
        self._steps_per_unit = 1.0
        self._axis_unit = "steps"
        self._connection_type = "usb"
        self._performax = None
        self._usb_handle = ctypes.c_void_p()

        try:
            connection_type = str(
                cast(Any, self.connection_type)).strip().lower()
            com = str(cast(Any, self.com))
            baudrate = int(cast(Any, self.baudrate))
            timeout = float(cast(Any, self.timeout))
            usb_device_index = int(cast(Any, self.usb_device_index))
            dll_path = str(cast(Any, self.dll_path)).strip()
            self._steps_per_unit = float(cast(Any, self.steps_per_unit))
            self._axis_unit = str(cast(Any, self.axis_unit))
            self._device_address = self._normalize_device_number(
                self.device_number)
            if self._steps_per_unit <= 0:
                raise ValueError("steps_per_unit must be greater than zero")

            if connection_type == "usb":
                self._open_usb_connection(
                    usb_device_index, timeout, dll_path)
                connection_description = (
                    f"USB device index {usb_device_index}"
                )
            elif connection_type == "serial":
                self._open_serial_connection(com, baudrate, timeout)
                connection_description = f"{com} at {baudrate} baud"
            else:
                raise ValueError(
                    'connection_type must be either "usb" or "serial"'
                )

            product_id = self._send_command("ID")
            self._send_command("ABS")
            self._ax1_position = self._steps_to_position(
                int(self._send_command("PX"))
            )
            self._ax1_status = self._send_command("EO") == "1"

            self.set_state(DevState.ON)
            self.set_status(
                f"Newmark NSC-A1 ({product_id}) is connected through "
                f"{connection_description}."
            )
            self.logger.info(self.get_status())
        except Exception as exc:
            self._record_error(str(exc))
            self._close_connection()
            self.set_state(DevState.OFF)
            self.set_status(f"Could not connect to Newmark NSC-A1: {exc}")
            self.logger.error(self.get_status())

    def _open_serial_connection(
        self, com: str, baudrate: int, timeout: float
    ):
        self.logger.info(
            f"Trying to connect to NSC-A1 on {com} at {baudrate} baud"
        )
        self.dev = serial.Serial(
            port=com,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=timeout,
        )
        self.dev.reset_input_buffer()
        self.dev.reset_output_buffer()
        self._connection_type = "serial"

    def _open_usb_connection(
        self, device_index: int, timeout: float, configured_dll_path: str
    ):
        # USBXpress keeps its handle table in Windows TLS. A lock alone is
        # insufficient: open, I/O, flush and close must share one OS thread.
        self._usb_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="newmark-usb"
        )
        try:
            self._usb_executor.submit(
                self._open_usb_on_worker, device_index, timeout,
                configured_dll_path,
            ).result()
        except Exception:
            self._close_connection()
            raise

    def _open_usb_on_worker(
        self, device_index: int, timeout: float, configured_dll_path: str
    ):
        if platform.system() != "Windows":
            raise RuntimeError(
                "PerformaxCom.dll USB control is supported only on Windows"
            )

        dll_path = configured_dll_path or os.path.join(
            os.path.dirname(__file__), "PerformaxCom.dll"
        )
        dll_path = os.path.abspath(os.path.expandvars(dll_path))
        if not os.path.isfile(dll_path):
            raise FileNotFoundError(f"PerformaxCom.dll not found: {dll_path}")

        dll_directory = None
        try:
            if hasattr(os, "add_dll_directory"):
                dll_directory = os.add_dll_directory(
                    os.path.dirname(dll_path)
                )
            performax = ctypes.WinDLL(dll_path)
        except OSError as exc:
            raise RuntimeError(
                f"Could not load {dll_path}. Ensure the DLL architecture "
                f"matches {ctypes.sizeof(ctypes.c_void_p) * 8}-bit Python "
                "and the same-architecture Silicon Labs SiUSBXp.dll from "
                f"the Newmark USB driver is installed: {exc}"
            ) from exc
        finally:
            if dll_directory is not None:
                dll_directory.close()

        dword = ctypes.c_ulong
        handle_pointer = ctypes.POINTER(ctypes.c_void_p)
        performax.fnPerformaxComGetNumDevices.argtypes = [
            ctypes.POINTER(dword)
        ]
        performax.fnPerformaxComGetNumDevices.restype = ctypes.c_int
        performax.fnPerformaxComGetProductString.argtypes = [
            dword,
            ctypes.c_void_p,
            dword,
        ]
        performax.fnPerformaxComGetProductString.restype = ctypes.c_int
        performax.fnPerformaxComOpen.argtypes = [dword, handle_pointer]
        performax.fnPerformaxComOpen.restype = ctypes.c_int
        performax.fnPerformaxComClose.argtypes = [ctypes.c_void_p]
        performax.fnPerformaxComClose.restype = ctypes.c_int
        performax.fnPerformaxComSetTimeouts.argtypes = [dword, dword]
        performax.fnPerformaxComSetTimeouts.restype = ctypes.c_int
        performax.fnPerformaxComSendRecv.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            dword,
            dword,
            ctypes.c_void_p,
        ]
        performax.fnPerformaxComSendRecv.restype = ctypes.c_int
        performax.fnPerformaxComFlush.argtypes = [ctypes.c_void_p]
        performax.fnPerformaxComFlush.restype = ctypes.c_int

        number_of_devices = dword()
        if not performax.fnPerformaxComGetNumDevices(
            ctypes.byref(number_of_devices)
        ):
            raise RuntimeError("PerformaxCom could not enumerate USB devices")
        if number_of_devices.value == 0:
            raise RuntimeError(
                "No Performax USB controller was found. Check the NSC-A1 "
                "USB driver and cable."
            )
        if device_index < 0 or device_index >= number_of_devices.value:
            raise ValueError(
                f"usb_device_index {device_index} is invalid; "
                f"{number_of_devices.value} device(s) were found"
            )

        timeout_ms = max(1, round(timeout * 1000))
        if not performax.fnPerformaxComSetTimeouts(
            timeout_ms, timeout_ms
        ):
            raise RuntimeError("PerformaxCom could not set USB timeouts")

        handle = ctypes.c_void_p()
        if not performax.fnPerformaxComOpen(
            device_index, ctypes.byref(handle)
        ) or not handle.value:
            raise RuntimeError(
                f"PerformaxCom could not open USB device index {device_index}"
            )

        self._performax = performax
        self._usb_handle = handle
        self._connection_type = "usb"
        if not performax.fnPerformaxComFlush(handle):
            raise RuntimeError("PerformaxCom could not flush the USB device")

        # The vendor sample defines PERFORMAX_MAX_DEVICE_STRLEN as 256;
        # this is separate from the 64-byte command/response packet size.
        product_buffer = ctypes.create_string_buffer(256)
        if performax.fnPerformaxComGetProductString(
            device_index, product_buffer, 0
        ):
            product_name = product_buffer.value.decode(
                "ascii", errors="replace"
            )
            self.logger.info(
                f"Opened Performax USB device {device_index}: {product_name}"
            )

    @staticmethod
    def _normalize_device_number(value: Any) -> str:
        text = str(value).strip().upper()
        if text.startswith("SDE"):
            text = text[3:]
        if not text.isdigit() or not 1 <= int(text) <= 99:
            raise ValueError("device_number must be between 01 and 99")
        return f"{int(text):02d}"

    def _now(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _record_error(self, message: str):
        self._error_message = f"{self._now()} {message}"
        self._message = message

    def _strip_response_prefix(self, response: str) -> str:
        prefix = f"#{self._device_address}"
        if response.startswith(prefix):
            return response[len(prefix):]
        return response

    def _send_command(self, ascii_command: str) -> str:
        """Send one NSC-A1 ASCII command over USB or addressed RS-485."""
        command_text = str(ascii_command).strip().rstrip("\r")
        if not command_text:
            raise ValueError("NSC-A1 command cannot be empty")

        if self._connection_type == "usb":
            response = self._send_usb_command(command_text)
        elif self._connection_type == "serial":
            response = self._send_serial_command(command_text)
        else:
            raise RuntimeError("NSC-A1 connection is not open")

        response = self._strip_response_prefix(response)
        if response.startswith("?"):
            self._record_error(response)
            raise RuntimeError(f"NSC-A1 rejected {command_text!r}: {response}")
        return response

    def _send_serial_command(self, command_text: str) -> str:
        if not hasattr(self, "dev") or not self.dev.is_open:
            raise RuntimeError("NSC-A1 serial connection is not open")

        wire_command = command_text if command_text.startswith("@") else (
            f"@{self._device_address}{command_text}"
        )

        with self._serial_lock:
            self.dev.write(f"{wire_command}\r".encode("ascii"))
            self.dev.flush()
            raw_response = self.dev.read_until(b"\r")

        if not raw_response:
            raise TimeoutError(
                f"No response from NSC-A1 for command {command_text!r}"
            )

        return raw_response.decode("ascii", errors="replace").strip()

    def _send_usb_command(self, command_text: str) -> str:
        with self._serial_lock:
            executor = getattr(self, "_usb_executor", None)
            if executor is None:
                raise RuntimeError("NSC-A1 USB connection is not open")
            return executor.submit(
                self._send_usb_on_worker, command_text
            ).result()

    def _send_usb_on_worker(self, command_text: str) -> str:
        if self._performax is None or not self._usb_handle.value:
            raise RuntimeError("NSC-A1 USB connection is not open")

        # USB commands are unaddressed. Accept an addressed raw command for
        # convenience, but remove its @NN prefix before passing it to the DLL.
        if (
            command_text.startswith("@")
            and len(command_text) >= 3
            and command_text[1:3].isdigit()
        ):
            command_text = command_text[3:]
        encoded_command = command_text.encode("ascii")
        if len(encoded_command) >= 64:
            raise ValueError(
                "NSC-A1 USB commands must be shorter than 64 bytes")

        write_buffer = ctypes.create_string_buffer(64)
        write_buffer.value = encoded_command
        read_buffer = ctypes.create_string_buffer(64)
        success = self._performax.fnPerformaxComSendRecv(
            self._usb_handle, write_buffer, 64, 64, read_buffer
        )
        if not success:
            # Do not replay commands: a failed reply does not prove that a
            # move or coordinate change was not already executed.
            raise RuntimeError(
                f"PerformaxCom USB transaction failed for {command_text!r}"
            )

        response = read_buffer.value.decode(
            "ascii", errors="replace"
        ).strip("\x00\r\n ")
        if not response:
            raise TimeoutError(
                f"No response from NSC-A1 for command {command_text!r}"
            )
        return response

    def _position_to_steps(self, value: float) -> int:
        return round(float(value) * self._steps_per_unit)

    def _steps_to_position(self, value: int) -> float:
        return float(value) / self._steps_per_unit

    def _validate_axis(self, axis: int):
        if int(axis) != 1:
            raise ValueError(
                "NSC-A1 is a single-axis controller; axis must be 1")

    def _close_usb_on_worker(self):
        performax = getattr(self, "_performax", None)
        usb_handle = getattr(self, "_usb_handle", ctypes.c_void_p())
        if (
            performax is not None
            and usb_handle.value
        ):
            try:
                if not performax.fnPerformaxComClose(usb_handle):
                    raise RuntimeError("fnPerformaxComClose returned FALSE")
            except Exception as exc:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        f"Unable to close NSC-A1 USB connection cleanly: {exc}"
                    )
            self._usb_handle = ctypes.c_void_p()
            self._performax = None

    def _close_connection(self):
        with getattr(self, "_serial_lock", threading.RLock()):
            executor = getattr(self, "_usb_executor", None)
            if executor is not None:
                try:
                    executor.submit(self._close_usb_on_worker).result()
                finally:
                    executor.shutdown(wait=True)
                    self._usb_executor = None
        if hasattr(self, "dev"):
            try:
                if self.dev.is_open:
                    self.dev.close()
            except Exception as exc:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        f"Unable to close NSC-A1 serial connection cleanly: {exc}"
                    )
            del self.dev

    def delete_device(self):
        self._close_connection()
        self.logger.info("Newmark NSC-A1 is disconnected.")
        super().delete_device()

    user_defined_name = attribute(
        label="name",
        dtype=str,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_user_defined_name(self):
        return self._user_defined_name

    @clear_error_wrap
    def write_user_defined_name(self, value):
        self._user_defined_name = value
        self.logger = LoggerAdapter(value, self._base_logger)

    host_computer = attribute(
        label="host computer",
        dtype=str,
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    saved_location_source = attribute(
        label="saved location source",
        dtype=str,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Use "server" for the server-side location file or "client" for the GUI-side file.',
    )

    def read_saved_location_source(self):
        return self._saved_location_source

    def write_saved_location_source(self, value):
        if value not in ("server", "client"):
            raise ValueError(
                'saved_location_source must be "server" or "client"')
        if value == "server":
            self.load_server_side_list()
        self._saved_location_source = value

    user_defined_locations = attribute(
        label="user defined locations",
        dtype=(str,),
        max_dim_x=1000,
        access=AttrWriteType.READ_WRITE,
    )

    def read_user_defined_locations(self):
        return self._user_defined_locations

    def write_user_defined_locations(self, value):
        self.logger.info(f"Write user_defined_locations: {value}")
        self._user_defined_locations = list(value)

    current_location = attribute(
        label="current location",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Write a saved location name to move there.',
    )

    def read_current_location(self):
        current_location = "Undefined"
        tolerance = max(1e-3, 0.5 / self._steps_per_unit)
        try:
            for location in self._user_defined_locations:
                name, positions = location.split(": ", 1)
                target = float(positions.strip("()").split(",")[0])
                if abs(self._ax1_position - target) <= tolerance:
                    current_location = f"{name}: ({positions.strip('()')})"
                    break
        except (ValueError, IndexError):
            pass
        return current_location

    @clear_error_wrap
    def write_current_location(self, value):
        for location in self._user_defined_locations:
            name, positions = location.split(": ", 1)
            if name == value:
                target = float(positions.strip("()").split(",")[0])
                self._write_axis_position(target)
                return
        raise ValueError(f"Location not found: {value}")

    def _read_axis_position(self) -> float:
        self._ax1_position = self._steps_to_position(
            int(self._send_command("PX"))
        )
        return self._ax1_position

    @clear_error_wrap
    def _write_axis_position(self, value: float):
        target_steps = self._position_to_steps(value)
        self._send_command("ABS")
        self._send_command(f"X{target_steps}")

    def create_position_attribute(self):
        return attribute(
            name="ax1_position",
            label="axis 1 position",
            dtype=float,
            unit=self._axis_unit,
            format="6.3f",
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def read_ax1_position(self, _attr=None):
        return self._read_axis_position()

    def write_ax1_position(self, attr):
        value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
        self._write_axis_position(float(value))

    def create_set_as_attribute(self):
        return attribute(
            name="set_ax1_as",
            label="set axis 1 as",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def read_set_ax1_as(self, _attr=None):
        return self._set_ax1_as

    @clear_error_wrap
    def write_set_ax1_as(self, attr):
        value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
        old_position = self._read_axis_position()
        new_position = float(value)
        self._send_command(f"PX={self._position_to_steps(new_position)}")
        self._ax1_position = new_position
        self._set_ax1_as = f"set {old_position:.3f} to {new_position:.3f}"

    def create_ax_step_attribute(self):
        return attribute(
            name="ax1_step",
            label="axis 1 step",
            dtype=float,
            unit=self._axis_unit,
            format="6.3f",
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def read_ax1_step(self, _attr=None):
        return self._ax1_step

    def write_ax1_step(self, attr):
        value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
        self._ax1_step = float(value)

    def create_ax_status_attribute(self):
        return attribute(
            name="ax1_status",
            label="axis 1 motor power",
            dtype=bool,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def read_ax1_status(self, _attr=None):
        self._ax1_status = self._send_command("EO") == "1"
        return self._ax1_status

    def write_ax1_status(self, attr):
        value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
        self._send_command(f"EO={int(bool(value))}")
        self._ax1_status = bool(value)

    def initialize_dynamic_attributes(self):
        self.add_attribute(self.create_position_attribute())
        self.add_attribute(self.create_set_as_attribute())
        self.add_attribute(self.create_ax_step_attribute())
        self.add_attribute(self.create_ax_status_attribute())

        self.add_command(
            command(f=self.move_to_negative_limit, dtype_in=int)
        )
        self.add_command(
            command(f=self.move_to_positive_limit, dtype_in=int)
        )

    error_message = attribute(
        label="error message",
        dtype=str,
        access=AttrWriteType.READ,
        doc="Last NSC-A1 communication or command error.",
    )

    def read_error_message(self):
        if not self._error_message:
            return f"{self._now()} NO ERROR"
        return self._error_message

    message = attribute(
        label="message",
        dtype=str,
        access=AttrWriteType.READ,
        polling_period=1000,
    )

    def read_message(self):
        try:
            status = int(self._send_command("MST"))
        except Exception as exc:
            message = f"MST communication error: {exc}"
            self._record_error(message)
            self.logger.warning(message)
            return f"{self._now()} {message}"

        descriptions = [
            description
            for bit, description in self.MOTOR_STATUS_BITS.items()
            if status & (1 << bit)
        ]
        state_text = ", ".join(descriptions) if descriptions else "IDLE"
        self._message = f"MST={status}: {state_text}"
        if status & ((1 << 6) | (1 << 7) | (1 << 10)):
            self._record_error(self._message)
        return f"{self._now()} {self._message}"

    raw_command = attribute(
        label="raw command",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc="NSC-A1 ASCII command. USB uses an unaddressed command; serial adds the device address and carriage return.",
    )

    def read_raw_command(self):
        return self._raw_command_return

    @clear_error_wrap
    def write_raw_command(self, value):
        if value:
            self._raw_command_return = self._send_command(value)

    @command()
    def stop(self):
        self._send_command("STOP")

    @clear_error_wrap
    def move_to_negative_limit(self, axis):
        self._validate_axis(axis)
        self._send_command("L-")

    @clear_error_wrap
    def move_to_positive_limit(self, axis):
        self._validate_axis(axis)
        self._send_command("L+")

    @command(dtype_in=int)
    @clear_error_wrap
    def set_as_zero(self, axis):
        self._validate_axis(axis)
        self._send_command("PX=0")
        self._ax1_position = 0.0

    @command()
    def clear_controller_error(self):
        self._send_command("CLR")
        self._error_message = ""

    @command
    def load_server_side_list(self):
        """Load server-side saved user-defined locations."""
        try:
            instance_name = sys.argv[1] if len(sys.argv) > 1 else "default"
            server_list_path = os.path.join(
                os.path.dirname(__file__),
                f"{instance_name}_server_locations.txt",
            )
            if not os.path.isfile(server_list_path):
                with open(server_list_path, "w", newline="") as file:
                    file.write("name positions\n")

            locations = []
            with open(server_list_path, "r") as file:
                next(file, None)
                for line in file:
                    fields = [
                        item
                        for item in line.replace("\t", " ")
                        .strip()
                        .replace('"', "")
                        .split(" ")
                        if item
                    ]
                    if len(fields) == 2:
                        name, positions = fields
                        locations.append(f"{name}: ({positions})")

            if locations:
                self._user_defined_locations = locations
                self.logger.info(
                    f"Loaded server-side saved locations: {locations}"
                )
            else:
                self.logger.info("No server-side saved locations found.")
        except Exception as exc:
            self.logger.info(
                f"Server-side saved locations were not loaded. Reason: {exc}"
            )


if __name__ == "__main__":
    Newmark.run_server()
