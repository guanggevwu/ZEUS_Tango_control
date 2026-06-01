from __future__ import annotations

import datetime
import functools
import logging
import os
import platform
import sys
from typing import Any

from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property

from common.logger_adapter import LoggerAdapter

try:
    # Newport official Python wrapper (usually shipped as a standalone file).
    from XPS_C8_drivers import XPS  # type: ignore
except Exception:  # pragma: no cover - runtime dependency check
    XPS = None


class NewPortXPS(Device):
    """Tango device server for Newport XPS motion controller.

    This server intentionally mirrors the public attribute layout of ESP301 where
    practical, while replacing serial commands with XPS API calls.
    """

    ip = device_property(dtype=str, default_value="")
    port = device_property(dtype=int, default_value=5001)
    timeout = device_property(dtype=int, default_value=5)
    username = device_property(dtype=str, default_value="Administrator")
    password = device_property(dtype=str, default_value="Administrator")
    group_name = device_property(dtype=str, default_value="GROUP1")
    axis_property = device_property(dtype=str, default_value="1,2,3,4,5,6,7,8")
    positioner_property = device_property(dtype=str, default_value="")
    axis_unit_property = device_property(dtype=str, default_value="")
    limit_search_distance = device_property(dtype=float, default_value=1000.0)

    @staticmethod
    def clear_error_wrap(func):
        """Clear cached error state before write-like operations."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self._error_message = ""
            return func(self, *args, **kwargs)

        return wrapper

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

        self._xps = None
        self._socket_id = None
        self._message = ""
        self._error_message = ""
        self._raw_command_return = ""
        self._user_defined_locations = []
        self._user_defined_name = "newport_xps"
        self._host_computer = platform.node()
        self._saved_location_source = "client"
        self._position_offset: dict[int, float] = {}
        self._axis_steps: dict[int, float] = {}
        self._axis_status: dict[int, bool] = {}

        try:
            self._setup_axes()
            self._connect_xps()
            self._initialize_internal_state()
            self.set_state(DevState.ON)
            self.set_status("NewPort XPS device is connected.")
        except Exception as exc:
            self.logger.info(f"Could NOT connect to XPS device. Reason: {exc}")
            self.set_state(DevState.OFF)
            self.set_status(f"Failed to connect to XPS: {exc}")

    def delete_device(self):
        try:
            if self._xps is not None and self._socket_id is not None:
                self._xps.TCP_CloseSocket(self._socket_id)
        except Exception:
            pass

    def _setup_axes(self):
        axis_prop = str(getattr(self, "axis_property", "1"))
        if axis_prop:
            self.axis = [int(i.strip())
                         for i in axis_prop.split(",") if i.strip()]
        else:
            self.axis = [1]

        positioner_prop = str(getattr(self, "positioner_property", ""))
        if positioner_prop.strip():
            names = [i.strip()
                     for i in positioner_prop.split(",") if i.strip()]
            if len(names) != len(self.axis):
                raise ValueError(
                    "positioner_property must have the same number of items as axis_property"
                )
            self.positioners = dict(zip(self.axis, names))
        else:
            # Default XPS naming pattern from the controller web interface.
            self.positioners = {}
            for idx, axis in enumerate(self.axis, start=1):
                self.positioners[axis] = f"GROUP{idx}.POSITIONER"

        unit_prop = str(getattr(self, "axis_unit_property", ""))
        if unit_prop.strip():
            units = [u.strip() for u in unit_prop.split(",") if u.strip()]
            if len(units) != len(self.axis):
                raise ValueError(
                    "axis_unit_property must have the same number of items as axis_property"
                )
            self.axis_units = dict(zip(self.axis, units))
        else:
            self.axis_units = {axis: "mm" for axis in self.axis}

    def _connect_xps(self):
        if XPS is None:
            raise RuntimeError(
                "XPS_C8_drivers is not available. Install/copy Newport XPS Python driver first."
            )

        self.logger.info(f"Trying to connect to XPS at {self.ip}:{self.port}")
        self._xps = XPS()
        self._socket_id = self._xps.TCP_ConnectToServer(
            self.ip, self.port, self.timeout)
        if self._socket_id is None or self._socket_id < 0:
            raise RuntimeError(
                "TCP_ConnectToServer returned invalid socket id")

        if hasattr(self._xps, "Login"):
            self._call_xps("Login", self.username, self.password)

    def _initialize_internal_state(self):
        for axis in self.axis:
            self._position_offset[axis] = 0.0
            self._axis_steps[axis] = 0.0
            self._axis_status[axis] = True
            setattr(self, f"_ax{axis}_position",
                    self._read_axis_position(axis))

    def _now(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _extract_error_and_payload(self, result: Any):
        if isinstance(result, tuple):
            if len(result) == 0:
                return 0, None
            if len(result) == 1:
                return int(result[0]), None
            if len(result) == 2:
                return int(result[0]), result[1]
            return int(result[0]), list(result[1:])

        if isinstance(result, list):
            if len(result) == 0:
                return 0, None
            if len(result) == 1:
                return int(result[0]), None
            if len(result) == 2:
                return int(result[0]), result[1]
            return int(result[0]), result[1:]

        if isinstance(result, int):
            return int(result), None

        # Some driver methods may return a string payload directly.
        return 0, result

    def _error_string(self, err_code: int) -> str:
        if self._xps is None or self._socket_id is None:
            return f"XPS error {err_code}"
        if not hasattr(self._xps, "ErrorStringGet"):
            return f"XPS error {err_code}"

        try:
            err, payload = self._extract_error_and_payload(
                self._xps.ErrorStringGet(self._socket_id, err_code)
            )
            if err == 0 and payload is not None:
                return str(payload)
        except Exception:
            pass
        return f"XPS error {err_code}"

    def _call_xps(self, method_name: str, *args):
        if self._xps is None or self._socket_id is None:
            raise RuntimeError("XPS connection is not initialized")
        if not hasattr(self._xps, method_name):
            raise RuntimeError(f"XPS driver method not found: {method_name}")

        method = getattr(self._xps, method_name)
        result = method(self._socket_id, *args)
        err, payload = self._extract_error_and_payload(result)
        if err != 0:
            err_text = self._error_string(err)
            self._error_message = f"{self._now()} {err_text}"
            raise RuntimeError(f"{method_name} failed: {err_text}")
        return payload

    def _read_axis_controller_position(self, axis: int) -> float:
        pos = self._call_xps("GroupPositionCurrentGet",
                             self.positioners[axis], 1)
        if isinstance(pos, list):
            if len(pos) == 0:
                return 0.0
            return float(pos[0])
        if pos is None:
            return 0.0
        return float(pos)

    def _read_axis_position(self, axis: int) -> float:
        controller_pos = self._read_axis_controller_position(axis)
        return controller_pos + self._position_offset[axis]

    def _move_group_absolute_controller(self, controller_targets: list[float]):
        self._call_xps("GroupMoveAbsolute",
                       self.group_name, controller_targets)

    def _move_group_relative_controller(self, controller_delta: list[float]):
        self._call_xps("GroupMoveRelative", self.group_name, controller_delta)

    @clear_error_wrap
    def _write_axis_position(self, axis: int, user_target: float):
        controller_targets = []
        for a in self.axis:
            ctrl = self._read_axis_controller_position(a)
            if a == axis:
                ctrl = float(user_target) - self._position_offset[a]
            controller_targets.append(ctrl)
        self._move_group_absolute_controller(controller_targets)
        setattr(self, f"_ax{axis}_position", float(user_target))

    @clear_error_wrap
    def _set_axis_user_coordinate(self, axis: int, user_value: float):
        controller_pos = self._read_axis_controller_position(axis)
        self._position_offset[axis] = float(user_value) - controller_pos
        setattr(self, f"_ax{axis}_position", float(user_value))

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
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    saved_location_source = attribute(
        label="saved location source",
        dtype="str",
        memorized=True,
        hw_memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Require restart client GUI to take effect in the GUI. If set to "server", use the "...server_locations.txt" on the server computer. If set to "client", use "...client_locations.txt" on the client computer.',
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
        self.logger.info(f"Write user_defined_locations: {value}")
        self._user_defined_locations = value

    current_location = attribute(
        label="current location",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc='Use dev.current_location = "location_name" to move to the predefined location',
    )

    def is_position_close(self, a: list[float], b: list[float], tol=1e-3):
        return all(abs(x - y) < tol for x, y in zip(a, b))

    def read_current_location(self):
        self._current_location = "Undefined"
        try:
            current_positions = [
                getattr(self, f"_ax{axis}_position") for axis in self.axis]
            for loc in self._user_defined_locations:
                name, positions = loc.split(": ")
                p = [float(i) for i in positions.strip("()").split(",")]
                if self.is_position_close(current_positions, p):
                    self._current_location = loc
                    break
        except Exception:
            pass
        return self._current_location

    def write_current_location(self, value):
        target_positions = None
        for loc in self._user_defined_locations:
            name, positions = loc.split(": ")
            if name == value:
                target_positions = [float(i)
                                    for i in positions.strip("()").split(",")]
                break
        if target_positions is None:
            raise ValueError(f"Location not found: {value}")

        for axis, target in zip(self.axis, target_positions):
            self._write_axis_position(axis, target)

    def create_position_attribute(self, axis):
        self.logger.info(f"created axis{axis} position.")
        return attribute(
            name=f"ax{axis}_position",
            label=f"axis {axis} position",
            dtype=float,
            unit=self.axis_units[axis],
            format="6.3f",
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def create_read_position_function(self, axis):
        def read_position(self, attr):
            pos = self._read_axis_position(axis)
            setattr(self, f"_ax{axis}_position", pos)
            return pos

        return read_position

    def create_write_position_function(self, axis):
        @NewPortXPS.clear_error_wrap
        def write_position(self, attr):
            value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
            self._write_axis_position(axis, float(value))

        return write_position

    def create_set_as_attribute(self, axis):
        return attribute(
            name=f"set_ax{axis}_as",
            label=f"set axis {axis} as",
            dtype=str,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def create_read_set_as_function(self, axis):
        def read_set_as(self, attr):
            if not hasattr(self, f"_set_ax{axis}_as"):
                setattr(self, f"_set_ax{axis}_as",
                        "------------N/A-----------")
            return getattr(self, f"_set_ax{axis}_as")

        return read_set_as

    def create_write_set_as_function(self, axis):
        @NewPortXPS.clear_error_wrap
        def write_set_as(self, attr):
            value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
            old_position = getattr(self, f"_ax{axis}_position")
            self._set_axis_user_coordinate(axis, float(value))
            setattr(
                self,
                f"_set_ax{axis}_as",
                f"set {old_position:.3f} to {float(value):.3f}",
            )

        return write_set_as

    def create_ax_step_attribute(self, axis):
        return attribute(
            name=f"ax{axis}_step",
            label=f"axis {axis} step",
            dtype=float,
            unit=self.axis_units[axis],
            format="6.3f",
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def create_read_step_function(self, axis):
        def read_step(self, attr):
            return self._axis_steps.get(axis, 0.0)

        return read_step

    def create_write_step_function(self, axis):
        def write_step(self, attr):
            value = attr.get_write_value() if hasattr(attr, "get_write_value") else attr
            self._axis_steps[axis] = float(value)

        return write_step

    def create_ax_status(self, axis):
        return attribute(
            name=f"ax{axis}_status",
            label=f"axis {axis} status",
            dtype=bool,
            memorized=True,
            access=AttrWriteType.READ_WRITE,
        )

    def create_read_status_function(self, axis):
        def read_status(self, attr):
            status_value = self._axis_status.get(axis, True)
            if hasattr(self._xps, "GroupStatusGet"):
                try:
                    self._call_xps("GroupStatusGet", self.group_name)
                    status_value = True
                except Exception:
                    status_value = False
            self._axis_status[axis] = status_value
            return status_value

        return read_status

    def create_write_status_function(self, axis):
        def write_status(self, attr):
            value = attr.get_write_value() if hasattr(
                attr, "get_write_value") else bool(attr)
            self._axis_status[axis] = bool(value)
            if value:
                if hasattr(self._xps, "GroupInitialize"):
                    self._call_xps("GroupInitialize", self.group_name)
            else:
                if hasattr(self._xps, "GroupKill"):
                    self._call_xps("GroupKill", self.group_name)

        return write_status

    def initialize_dynamic_attributes(self):
        cmd_move_to_negative_limit = command(
            f=self.move_to_negative_limit, dtype_in=int)
        cmd_move_to_positive_limit = command(
            f=self.move_to_positive_limit, dtype_in=int)

        for axis in self.axis:
            try:
                setattr(
                    self,
                    f"read_ax{axis}_position",
                    self.create_read_position_function(axis),
                )
                setattr(
                    self,
                    f"write_ax{axis}_position",
                    self.create_write_position_function(axis),
                )
                self.add_attribute(self.create_position_attribute(axis))

                setattr(
                    self, f"read_set_ax{axis}_as", self.create_read_set_as_function(
                        axis)
                )
                setattr(
                    self,
                    f"write_set_ax{axis}_as",
                    self.create_write_set_as_function(axis),
                )
                self.add_attribute(self.create_set_as_attribute(axis))

                setattr(
                    self,
                    f"read_ax{axis}_step",
                    self.create_read_step_function(axis),
                )
                setattr(
                    self,
                    f"write_ax{axis}_step",
                    self.create_write_step_function(axis),
                )
                self.add_attribute(self.create_ax_step_attribute(axis))

                setattr(
                    self,
                    f"read_ax{axis}_status",
                    self.create_read_status_function(axis),
                )
                setattr(
                    self,
                    f"write_ax{axis}_status",
                    self.create_write_status_function(axis),
                )
                self.add_attribute(self.create_ax_status(axis))
            except Exception as exc:
                self.logger.info(
                    f"Error adding attributes for axis {axis}: {exc}")

        self.add_command(cmd_move_to_negative_limit)
        self.add_command(cmd_move_to_positive_limit)

    error_message = attribute(
        label="error message",
        dtype="str",
        access=AttrWriteType.READ,
        doc="Last XPS command error text.",
    )

    def read_error_message(self):
        if not self._error_message:
            self._error_message = f"{self._now()} NO ERROR"
        return self._error_message

    message = attribute(
        label="message",
        dtype="str",
        access=AttrWriteType.READ,
        polling_period=1000,
    )

    def read_message(self):
        if not self._message:
            self._message = "READY"
        return f"{self._now()} {self._message}"

    raw_command = attribute(
        label="raw command",
        dtype=str,
        memorized=True,
        access=AttrWriteType.READ_WRITE,
        doc="Send raw XPS API command string.",
    )

    def read_raw_command(self):
        return self._raw_command_return

    @clear_error_wrap
    def write_raw_command(self, value):
        if value == "":
            return
        if self._xps is None or self._socket_id is None:
            raise RuntimeError("XPS connection is not initialized")
        if not hasattr(self._xps, "Send"):
            raise RuntimeError("XPS driver does not provide Send()")
        result = self._xps.Send(self._socket_id, value)
        self._raw_command_return = str(result)
        self._message = f"RAW: {value}"

    @command()
    def stop(self):
        if hasattr(self._xps, "GroupMoveAbort"):
            self._call_xps("GroupMoveAbort", self.group_name)
        self._message = "Motion stopped"

    @clear_error_wrap
    def move_to_negative_limit(self, axis):
        if axis not in self.axis:
            raise ValueError(f"Axis {axis} is not configured")
        delta = [0.0 for _ in self.axis]
        idx = self.axis.index(axis)
        search_distance = float(getattr(self, "limit_search_distance", 1000.0))
        delta[idx] = -abs(search_distance)
        self._move_group_relative_controller(delta)

    @clear_error_wrap
    def move_to_positive_limit(self, axis):
        if axis not in self.axis:
            raise ValueError(f"Axis {axis} is not configured")
        delta = [0.0 for _ in self.axis]
        idx = self.axis.index(axis)
        search_distance = float(getattr(self, "limit_search_distance", 1000.0))
        delta[idx] = abs(search_distance)
        self._move_group_relative_controller(delta)

    @command(dtype_in=int)
    def set_as_zero(self, axis):
        if axis not in self.axis:
            raise ValueError(f"Axis {axis} is not configured")
        self._set_axis_user_coordinate(axis, 0.0)

    @command
    def load_server_side_list(self):
        """Load server-side saved user-defined location list."""
        try:
            server_list_path = os.path.join(
                os.path.dirname(
                    __file__), f"{sys.argv[1]}_server_locations.txt"
            )
            if not os.path.isfile(server_list_path):
                with open(server_list_path, "w", newline="") as f:
                    f.write("name positions\n")

            with open(server_list_path, "r") as f:
                tmp = []
                next(f)
                for line in f:
                    if line.strip():
                        name, positions = [
                            e
                            for e in line.replace("\t", " ")
                            .strip()
                            .replace('"', "")
                            .split(" ")
                            if e
                        ]
                        tmp.append(f"{name}: ({positions})")

            if tmp:
                self._user_defined_locations = tmp
                self.logger.info(
                    f"Loaded server side saved user defined locations: {tmp}")
            else:
                self.logger.info(
                    "No server side saved user defined locations found.")
        except Exception as exc:
            self.logger.info(
                f"Server side saved user defined locations file not loaded successfully. Reason: {exc}"
            )


if __name__ == "__main__":
    NewPortXPS.run_server()
