from __future__ import annotations

import datetime
import importlib.util
import logging
import os
import platform
import shutil
import signal
import sys
import ctypes
import threading
from typing import Any

from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property

from common.logger_adapter import LoggerAdapter


class ThorlabsKDC101(Device):
    timeout_ms = device_property(dtype=int, default_value=5000)

    def init_device(self):
        self._base_logger = logging.getLogger(self.__class__.__name__)
        if not hasattr(self, "friendly_name"):
            self.friendly_name = self.__class__.__name__
        self.logger = LoggerAdapter(self.friendly_name, self._base_logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(
            handlers=handlers, format="%(asctime)s %(message)s", level=logging.INFO
        )

        super().init_device()
        self.set_state(DevState.INIT)

        self._device = None
        self._devices = {}
        self._system_manager = None
        self._device_infos = {}
        self._current_device_info = None
        self._active_serial = ""
        self._connected_serials = []
        self._dynamic_attr_names = []
        self._user_defined_locations = []
        self._user_defined_name = "kdc101"
        self._host_computer = platform.node()
        self._saved_location_source = "client"
        self._current_location = "Undefined"
        self._part_number = ""
        self._connected_product = ""
        self._step_by_serial = {}
        self._preferred_unit = None
        self._axis_unit = "mm"
        self._motion_thread = None
        self._motion_lock = threading.Lock()

        try:
            self._connect_kdc101()
            self.initialize_dynamic_attributes()
            self.load_server_side_list()
            self.set_state(DevState.ON)
            self.set_status("Thorlabs KDC101 device is connected.")
        except Exception as exc:
            self.set_state(DevState.OFF)
            self.set_status(f"Failed to connect to KDC101: {exc}")
            raise RuntimeError(
                f"Failed to connect to KDC101: {exc}. Shutdown the device server and wait for 20 seconds before restarting.") from exc

    def delete_device(self):
        try:
            for device in self._devices.values():
                try:
                    device.disconnect()
                    device.close()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if self._system_manager is not None:
                self._system_manager.shutdown()
        except Exception:
            pass

    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _require_device(self):
        if self._device is None:
            raise RuntimeError("KDC101 device is not connected")
        return self._device

    def _get_device(self, serial: str | None = None):
        target_serial = serial or self._active_serial
        if not target_serial:
            raise RuntimeError("No active KDC101 serial is selected")
        try:
            return self._devices[target_serial]
        except KeyError as exc:
            raise RuntimeError(
                f"KDC101 serial '{target_serial}' is not connected"
            ) from exc

    def _get_device_info(self, serial: str | None = None):
        target_serial = serial or self._active_serial
        if not target_serial:
            return None
        return self._device_infos.get(target_serial)

    def _set_active_serial(self, serial: str):
        serial = str(serial).strip()
        if serial not in self._devices:
            raise ValueError(
                f"Unknown serial '{serial}'. Available serials: {', '.join(self._connected_serials)}"
            )
        self._active_serial = serial
        self._device = self._devices[serial]
        self._current_device_info = self._device_infos.get(serial)
        if self._current_device_info is not None:
            self._part_number = self._current_device_info.part_number
        self._connected_product = self._safe_connected_product_name(
            self._device)

    def _require_system_manager(self):
        if self._system_manager is None:
            raise RuntimeError("XA SystemManager is not initialized")
        return self._system_manager

    def _ensure_xa_native_dll(self, script_dir: str):
        """Ensure thorlabs_xa can find tlmc_xa_native.dll after clone/install."""
        dll_name = "tlmc_xa_native.dll"
        repo_root = os.path.dirname(script_dir)
        source_candidates = [
            os.path.join(script_dir, dll_name),
            os.path.join(
                r"C:\Program Files\Thorlabs XA",
                "SDK",
                "Native (C, C++)",
                "Libraries",
                "x64",
                dll_name,
            ),
        ]

        source_dll = next(
            (candidate for candidate in source_candidates if os.path.isfile(candidate)),
            None,
        )
        if source_dll is None:
            return

        spec = importlib.util.find_spec("thorlabs_xa")
        if spec is None or not spec.submodule_search_locations:
            return

        package_dir = next(iter(spec.submodule_search_locations), None)
        if not package_dir:
            return

        target_dll = os.path.join(package_dir, dll_name)
        if os.path.isfile(target_dll):
            return

        try:
            shutil.copy2(source_dll, target_dll)
            self.logger.info(
                f"Copied {dll_name} to thorlabs_xa package directory: {target_dll}"
            )
        except Exception as exc:
            self.logger.info(
                f"Could not copy {dll_name} into thorlabs_xa package directory. Reason: {exc}"
            )

    def _validate_xa_native_dll(self, search_dirs: list[str]):
        """Fail early with actionable info if native XA DLL cannot be loaded."""
        dll_name = "tlmc_xa_native.dll"
        spec = importlib.util.find_spec("thorlabs_xa")
        if spec is None or not spec.submodule_search_locations:
            return

        package_dir = next(iter(spec.submodule_search_locations), None)
        if not package_dir:
            return

        dll_path = os.path.join(package_dir, dll_name)
        if not os.path.isfile(dll_path):
            raise RuntimeError(
                "XA native DLL is missing. Expected at "
                f"'{dll_path}'. Place '{dll_name}' in ZEUS_Tango_control/ThorlabsXA"
            )

        try:
            ctypes.CDLL(dll_path)
        except OSError as exc:
            existing_dirs = [
                candidate for candidate in search_dirs if os.path.isdir(candidate)]
            raise RuntimeError(
                "Failed to load XA native DLL dependencies. "
                f"DLL: '{dll_path}'. "
                f"Registered DLL search directories: {existing_dirs}. "
                "Install/repair Microsoft Visual C++ Redistributable (x64), and confirm "
                "Thorlabs XA SDK native libraries are available. "
                f"Original error: {exc}"
            ) from exc

    def _import_xa_modules(self):
        search_dirs = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        self._ensure_xa_native_dll(script_dir)
        search_dirs.append(script_dir)
        self._dll_dir_handles = []
        if hasattr(os, "add_dll_directory"):
            for candidate in search_dirs:
                try:
                    if candidate and os.path.isdir(candidate):
                        self._dll_dir_handles.append(
                            os.add_dll_directory(candidate))
                except (OSError, ValueError):
                    pass

        self._validate_xa_native_dll(search_dirs)

        from thorlabs_xa.products.kdc101 import Kdc101
        from thorlabs_xa.shared.enums import (
            TLMC_EnableState,
            TLMC_MoveMode,
            TLMC_OperatingMode,
            TLMC_ScaleType,
            TLMC_StopMode,
            TLMC_Unit,
            TLMC_UniversalStatusBit,
            TLMC_Wait,
        )
        from thorlabs_xa.shared.system_manager import SystemManager

        return {
            "Kdc101": Kdc101,
            "SystemManager": SystemManager,
            "TLMC_EnableState": TLMC_EnableState,
            "TLMC_MoveMode": TLMC_MoveMode,
            "TLMC_OperatingMode": TLMC_OperatingMode,
            "TLMC_ScaleType": TLMC_ScaleType,
            "TLMC_StopMode": TLMC_StopMode,
            "TLMC_Unit": TLMC_Unit,
            "TLMC_UniversalStatusBit": TLMC_UniversalStatusBit,
            "TLMC_Wait": TLMC_Wait,
        }

    def _connect_kdc101(self):
        xa = self._import_xa_modules()
        self._xa = xa
        self._system_manager = xa["SystemManager"].instance()
        self._system_manager.startup(None)
        device_infos = self._select_device_info()
        self._device_infos = {info.device: info for info in device_infos}
        self._devices = {}

        for info in device_infos:
            device = self._system_manager.open_device_as(
                info.device,
                info.transport,
                xa["TLMC_OperatingMode"].TLMC_OperatingMode_Default,
                xa["Kdc101"],
            )
            device.set_enable_state(xa["TLMC_EnableState"].TLMC_Enabled)
            self._devices[info.device] = device

        self._connected_serials = sorted(self._devices.keys())
        if not self._connected_serials:
            raise RuntimeError("No KDC101 controller found")

        self._set_active_serial(self._connected_serials[0])

        self._preferred_unit = self._device.get_preferred_physical_unit(
            xa["TLMC_ScaleType"].TLMC_ScaleType_Distance
        )
        self._axis_unit = self._unit_to_string(self._preferred_unit)
        self._connected_product = self._safe_connected_product_name(
            self._device)

    def _select_device_info(self):
        system_manager = self._require_system_manager()
        devices = system_manager.get_device_list()
        matching = [
            device for device in devices if device.part_number == "KDC101"]

        if matching:
            return sorted(matching, key=lambda info: info.device)

        raise RuntimeError("No KDC101 controller found")

    def _safe_connected_product_name(self, device=None):
        if device is None:
            device = self._require_device()
        try:
            return device.get_connected_product_info().product_name
        except Exception:
            return ""

    def _safe_hardware_info_part_number(self):
        device = self._require_device()
        try:
            hardware_info = device.get_hardware_info(
                self._xa["TLMC_Wait"].TLMC_InfiniteWait
            )
            return hardware_info.part_number
        except Exception:
            return self._part_number

    def _unit_to_string(self, unit):
        unit_enum = self._xa["TLMC_Unit"]
        unit_map = {
            unit_enum.TLMC_Unit_Millimetres: "mm",
            unit_enum.TLMC_Unit_Micrometres: "um",
            unit_enum.TLMC_Unit_Degrees: "deg",
            unit_enum.TLMC_Unit_Radians: "rad",
            unit_enum.TLMC_Unit_Volts: "V",
            unit_enum.TLMC_Unit_Steps: "steps",
        }
        return unit_map.get(unit, "arb")

    def _device_to_physical(self, device_value: int, scale_type=None):
        if scale_type is None:
            scale_type = self._xa["TLMC_ScaleType"].TLMC_ScaleType_Distance
        device = self._require_device()
        value, _unit = device.convert_from_device_units_to_physical(
            scale_type, int(device_value)
        )
        return float(value)

    def _device_to_physical_for(self, device, device_value: int, scale_type=None):
        if scale_type is None:
            scale_type = self._xa["TLMC_ScaleType"].TLMC_ScaleType_Distance
        value, _unit = device.convert_from_device_units_to_physical(
            scale_type, int(device_value)
        )
        return float(value)

    def _physical_to_device(self, physical_value: float, scale_type=None):
        if scale_type is None:
            scale_type = self._xa["TLMC_ScaleType"].TLMC_ScaleType_Distance
        device = self._require_device()
        return int(
            device.convert_from_physical_to_device(
                scale_type, self._preferred_unit, float(physical_value)
            )
        )

    def _physical_to_device_for(self, device, physical_value: float, scale_type=None):
        if scale_type is None:
            scale_type = self._xa["TLMC_ScaleType"].TLMC_ScaleType_Distance
        preferred_unit = device.get_preferred_physical_unit(scale_type)
        return int(
            device.convert_from_physical_to_device(
                scale_type, preferred_unit, float(physical_value)
            )
        )

    def _read_position_for_serial(self, serial: str):
        device = self._get_device(serial)
        position_counter = device.get_position_counter(self.timeout_ms)
        return self._device_to_physical_for(device, position_counter)

    def _write_position_for_serial(self, serial: str, value: float):
        device = self._get_device(serial)
        device_position = self._physical_to_device_for(device, float(value))

        def _move():
            device.move(
                self._xa["TLMC_MoveMode"].TLMC_MoveMode_Absolute,
                device_position,
                self.timeout_ms,
            )

        self._start_background_motion(_move, f"absolute-move-{serial}")

    def _read_enabled_for_serial(self, serial: str):
        device = self._get_device(serial)
        return (
            device.get_enable_state(self.timeout_ms)
            == self._xa["TLMC_EnableState"].TLMC_Enabled
        )

    def _write_enabled_for_serial(self, serial: str, value: bool):
        device = self._get_device(serial)
        device.set_enable_state(
            self._xa["TLMC_EnableState"].TLMC_Enabled
            if bool(value)
            else self._xa["TLMC_EnableState"].TLMC_Disabled
        )

    def _read_step_for_serial(self, serial: str):
        return float(self._step_by_serial.get(serial, 0.0))

    def _write_step_for_serial(self, serial: str, value: float):
        self._step_by_serial[serial] = float(value)

    def _make_dynamic_read_position(self, serial: str):
        def _read(*_args, **_kwargs):
            return self._read_position_for_serial(serial)

        return _read

    def _make_dynamic_write_position(self, serial: str):
        def _write(self, *args, **_kwargs):
            value = args[0].get_write_value()
            self._write_position_for_serial(serial, value)

        return _write

    def _make_dynamic_read_status(self, serial: str):
        def _read(*_args, **_kwargs):
            return self._read_enabled_for_serial(serial)

        return _read

    def _make_dynamic_write_status(self, serial: str):
        def _write(self, *args, **_kwargs):
            value = args[0].get_write_value()
            self._write_enabled_for_serial(serial, bool(value))

        return _write

    def _make_dynamic_read_step(self, serial: str):
        def _read(*_args, **_kwargs):
            return self._read_step_for_serial(serial)

        return _read

    def _make_dynamic_write_step(self, serial: str):
        def _write(self, *args, **_kwargs):
            value = args[0].get_write_value()
            self._write_step_for_serial(serial, float(value))

        return _write

    def _make_dynamic_home_command(self, serial: str):
        def _cmd(*_args, **_kwargs):
            device = self._get_device(serial)

            def _home():
                device.home(self.timeout_ms)

            self._start_background_motion(_home, f"home-{serial}")

        return _cmd

    def _make_dynamic_identify_command(self, serial: str):
        def _cmd(*_args, **_kwargs):
            device = self._get_device(serial)
            device.identify()

        return _cmd

    def initialize_dynamic_attributes(self):
        for serial in self._connected_serials:
            position_name = f"sn_{serial}_position"
            step_name = f"sn_{serial}_step"
            status_name = f"sn_{serial}_status"
            home_name = f"sn_{serial}_home"
            identify_name = f"sn_{serial}_identify"

            setattr(
                self,
                f"read_{position_name}",
                self._make_dynamic_read_position(serial),
            )
            setattr(
                self,
                f"write_{position_name}",
                self._make_dynamic_write_position(serial),
            )
            self.add_attribute(
                attribute(
                    name=position_name,
                    label=f"sn {serial} position",
                    dtype=float,
                    unit="mm",
                    format="6.4f",
                    access=AttrWriteType.READ_WRITE,
                )
            )
            self._dynamic_attr_names.append(position_name)

            setattr(
                self,
                f"read_{step_name}",
                self._make_dynamic_read_step(serial),
            )
            setattr(
                self,
                f"write_{step_name}",
                self._make_dynamic_write_step(serial),
            )
            self.add_attribute(
                attribute(
                    name=step_name,
                    label=f"sn {serial} step",
                    dtype=float,
                    unit="mm",
                    format="6.4f",
                    access=AttrWriteType.READ_WRITE,
                )
            )
            self._dynamic_attr_names.append(step_name)

            setattr(
                self,
                f"read_{status_name}",
                self._make_dynamic_read_status(serial),
            )
            setattr(
                self,
                f"write_{status_name}",
                self._make_dynamic_write_status(serial),
            )
            self.add_attribute(
                attribute(
                    name=status_name,
                    label=f"sn {serial} status",
                    dtype=bool,
                    access=AttrWriteType.READ_WRITE,
                )
            )
            self._dynamic_attr_names.append(status_name)

            dynamic_home = self._make_dynamic_home_command(serial)
            dynamic_home.__name__ = home_name
            setattr(self, home_name, dynamic_home)
            self.add_command(command(f=dynamic_home))

            dynamic_identify = self._make_dynamic_identify_command(serial)
            dynamic_identify.__name__ = identify_name
            setattr(self, identify_name, dynamic_identify)
            self.add_command(command(f=dynamic_identify))

    def _start_background_motion(self, worker, action_name: str):
        with self._motion_lock:
            if self._motion_thread is not None and self._motion_thread.is_alive():
                raise RuntimeError("Motion is already in progress")

            def _wrapped_worker():
                try:
                    worker()
                except Exception as exc:
                    self.logger.info(f"{action_name} failed: {exc}")

            self._motion_thread = threading.Thread(
                target=_wrapped_worker,
                daemon=True,
                name=f"kdc101-{action_name}",
            )
            self._motion_thread.start()

    def is_position_close(self, a: list[float], b: list[float], tol=1e-3):
        return all(abs(x - y) < tol for x, y in zip(a, b))

    user_defined_name = attribute(
        label="name",
        dtype=str,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_user_defined_name(self):
        return self._user_defined_name

    def write_user_defined_name(self, value):
        self._user_defined_name = value
        self.logger = LoggerAdapter(value, self._base_logger)

    host_computer = attribute(label="host computer",
                              dtype=str, access=AttrWriteType.READ)

    def read_host_computer(self):
        return self._host_computer

    saved_location_source = attribute(
        label="saved location source",
        dtype=str,
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_saved_location_source(self):
        return self._saved_location_source

    def write_saved_location_source(self, value):
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
        self._user_defined_locations = value

    current_location = attribute(
        label="current location",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
    )

    def read_current_location(self):
        try:
            positions = [self._read_position_for_serial(
                s) for s in self._connected_serials]
            for loc in self._user_defined_locations:
                name, pos_str = loc.split(": ")
                parsed = [float(i) for i in pos_str.strip("()").split(",")]
                if self.is_position_close(positions, parsed):
                    self._current_location = name
                    return self._current_location
        except Exception:
            pass
        self._current_location = "Undefined"
        return self._current_location

    def write_current_location(self, value):
        target_positions = None
        for loc in self._user_defined_locations:
            name, pos_str = loc.split(": ")
            if name == value:
                target_positions = [float(i)
                                    for i in pos_str.strip("()").split(",")]
                break
        if target_positions is None:
            raise ValueError(f"Unknown saved location: {value}")
        for serial, pos in zip(self._connected_serials, target_positions):
            self._write_position_for_serial(serial, pos)

    connected_product = attribute(
        label="connected product",
        dtype=str,
        access=AttrWriteType.READ,
    )

    def read_connected_product(self):
        return self._connected_product

    @command()
    def shutdown(self):
        self.delete_device()
        threading.Timer(0.5, os._exit, args=(0,)).start()

    @command()
    def home(self):
        device = self._require_device()

        def _home():
            device.home(self.timeout_ms)

        self._start_background_motion(_home, "home")

    @command()
    def identify(self):
        device = self._require_device()
        device.identify()

    @command()
    def stop(self):
        device = self._require_device()
        device.stop(
            self._xa["TLMC_StopMode"].TLMC_StopMode_Immediate,
            self.timeout_ms,
        )

    @command()
    def move_to_negative_limit(self):
        device = self._require_device()
        device.move(
            self._xa["TLMC_MoveMode"].TLMC_MoveMode_ContinuousReverse,
            0,
            self.timeout_ms,
        )

    @command()
    def move_to_positive_limit(self):
        device = self._require_device()
        device.move(
            self._xa["TLMC_MoveMode"].TLMC_MoveMode_ContinuousForward,
            0,
            self.timeout_ms,
        )

    @command()
    def load_server_side_list(self):
        try:
            instance_name = sys.argv[1] if len(sys.argv) > 1 else "kdc101"
            server_list_path = os.path.join(
                os.path.dirname(
                    __file__), f"{instance_name}_server_locations.txt"
            )
            if not os.path.isfile(server_list_path):
                with open(server_list_path, "w", newline="") as file_obj:
                    file_obj.write("name positions\n")
            with open(server_list_path, "r") as file_obj:
                loaded_locations = []
                next(file_obj)
                for line in file_obj:
                    if line.strip():
                        name, positions = [
                            entry
                            for entry in line.replace("\t", " ")
                            .strip()
                            .replace('"', "")
                            .split(" ")
                            if entry
                        ]
                        loaded_locations.append(f"{name}: ({positions})")
                if loaded_locations:
                    self._user_defined_locations = loaded_locations
        except Exception as exc:
            self.logger.info(
                f"Server side saved user defined locations file is not loaded successfully. Reason: {exc}"
            )


if __name__ == "__main__":
    ThorlabsKDC101.run_server()
