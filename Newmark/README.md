# Newmark NSC-A1 Tango device

This device server mirrors the single-axis parts of the ESP301 server. It supports the NSC-A1 native USB Type-B connection through `PerformaxCom.dll` and the RS-485 ASCII interface through `pyserial`.

## Tango device properties

| Property           | Default | Description                                                  |
| ------------------ | ------- | ------------------------------------------------------------ |
| `connection_type`  | `usb`   | `usb` for Type-B/PerformaxCom or `serial` for RS-485         |
| `usb_device_index` | `0`     | Zero-based index returned by Performax USB discovery         |
| `dll_path`         | empty   | Optional DLL path; empty uses `Newmark/PerformaxCom.dll`     |
| `com`              | `COM1`  | Serial/USB-to-RS-485 adapter port; ignored in USB mode       |
| `baudrate`         | `9600`  | RS-485 baud rate; ignored in USB mode                        |
| `timeout`          | `2.0`   | USB or serial read/write timeout in seconds                  |
| `device_number`    | `01`    | RS-485 address from `01` through `99`; ignored by native USB |
| `axis_unit`        | `steps` | Engineering unit displayed by Tango/Taurus                   |
| `steps_per_unit`   | `1.0`   | Controller steps per displayed unit                          |

For the controller's USB Type-B port, leave `connection_type=usb`. The server loads the bundled 64-bit `PerformaxCom.dll`, enumerates the connected Performax devices, opens `usb_device_index`, and sends unaddressed 64-byte command/reply buffers as required by the vendor API. The installed Python must also be 64-bit, and the Newmark/Performax USB driver must be installed in Windows.

For RS-485, use `connection_type=serial`. The serial format is 8 data bits, no parity, one stop bit, and no flow control. Commands are sent as `@<device_number><COMMAND>\r`. Both NSC-A1 response modes are accepted.

### USB thread ownership

The supplied SiUSBXp library keeps its handle table in Windows thread-local
storage (`TlsGetValue`/`TlsSetValue`). Its open, read/write, flush, and close
functions look up handles through that table. Tango initialization, attribute
polling, and client requests can run on different threads, so a mutex alone
does not make the handle usable by all callers.

The server dispatches **all USB operations to one dedicated worker thread**,
including initialization and cleanup. Serial transport is unchanged. Failed
commands are not automatically replayed: failure to receive an acknowledgement
does not prove that a motion command was not executed.

After upgrading from the earlier implementation, fully stop the old server
process and start it again (not just Tango `Init`), because it may still own a
USB handle on another thread. No device-property changes are required.

Hardware-free regression tests in [test_usb_threading.py](test_usb_threading.py)
model the thread-local handle table, reproduce the previous cross-thread failure,
and verify same-thread I/O and cleanup. Actual hardware operation still needs
confirmation after restart.

## ESP301-compatible interface

The server exposes `ax1_position`, `ax1_step`, `ax1_status`, `set_ax1_as`, saved locations, raw commands, motor messages, limit moves, stop, and zeroing. The main command mapping is:

| Action                       | NSC-A1 ASCII command   |
| ---------------------------- | ---------------------- |
| Read/set position            | `PX`, `PX=<steps>`     |
| Absolute move                | `ABS`, then `X<steps>` |
| Enable/disable motor power   | `EO=1`, `EO=0`         |
| Read motor power             | `EO`                   |
| Read motor status            | `MST`                  |
| Stop with deceleration       | `STOP`                 |
| Negative/positive limit home | `L-`, `L+`             |
| Clear controller error       | `CLR`                  |

`steps_per_unit` performs the conversion between Tango positions and integer controller steps. Leave it at `1.0` to expose raw motor steps.

## Running

Register a Tango server instance whose class is `Newmark`, configure its properties in the Tango database, then start the server with the instance name. For the direct USB Type-B connection, the defaults `connection_type=usb`, `usb_device_index=0`, and an empty `dll_path` use the included DLL. The launcher and GUI mirror the ESP301 workflow:

- `python Newmark/menu.py`
- `python Newmark/server.py <instance>`
- `python Newmark/GUI.py <device-name>`

The native USB connection does not create a COM port and therefore does not use `pyserial`. The alternative RS-485 interface generally requires a suitable USB-to-RS-485 adapter. Ethernet transport is not used.
