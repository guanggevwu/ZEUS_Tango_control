# Newmark NSC-A1 Tango device

This device server mirrors the single-axis parts of the ESP301 server. It supports the NSC-A1 native USB Type-B connection through `PerformaxCom.dll` and the RS-485 ASCII interface through `pyserial`.

## Tango device properties

| Property           | Default | Description                                                  |
| ------------------ | ------- | ------------------------------------------------------------ |
| `connection_type`  | `usb`   | `usb` for Type-B/PerformaxCom or `serial` for RS-485         |
| `usb_device_index` | `0`     | Zero-based index used when `usb_serial_number` is empty      |
| `usb_serial_number` | empty | Exact USB serial string; takes priority over the index      |
| `dll_path`         | empty   | Optional DLL path; empty uses `Newmark/PerformaxCom.dll`     |
| `com`              | `COM1`  | Serial/USB-to-RS-485 adapter port; ignored in USB mode       |
| `baudrate`         | `9600`  | RS-485 baud rate; ignored in USB mode                        |
| `timeout`          | `2.0`   | USB or serial read/write timeout in seconds                  |
| `device_number`    | `01`    | RS-485 address from `01` through `99`; ignored by native USB |
| `axis_unit`        | `steps` | Engineering unit displayed by Tango/Taurus                   |
| `steps_per_unit`   | `1.0`   | Controller steps per displayed unit                          |

For the controller's USB Type-B port, leave `connection_type=usb`. The server loads the bundled 64-bit `PerformaxCom.dll`, enumerates the connected Performax devices, selects the exact `usb_serial_number` when configured (otherwise `usb_device_index`), and sends unaddressed 64-byte command/reply buffers as required by the vendor API. The installed Python must also be 64-bit, and the Newmark/Performax USB driver must be installed in Windows.

Serial lookup uses `fnPerformaxComGetProductString(index, buffer, 0)` on the
same worker thread as USB open and I/O. A configured serial that is missing,
duplicated, or cannot be read causes initialization to fail; it never silently
opens a different controller. The actual selected serial is logged at startup.
Set the Tango device property `usb_serial_number` to the exact string reported
by discovery, then restart the server. Leave it empty to retain index selection.

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

### Combined PW grating GUI

Launching the GUI for either `laser/newmark/PW_grating_1` or
`laser/newmark/PW_grating_2` automatically includes both, always in that order.
Start both Tango devices before opening the GUI; the GUI does not start servers.
Other Newmark devices keep their existing individual panels.

The shared panels are `laser/newmark/PW_grating_less`,
`laser/newmark/PW_grating_more`, and `laser/newmark/PW_grating_minimum`.
Both controllers retain their own `ax1_position` attribute, saved locations,
status and command buttons. Device-name headings distinguish the sections.
The minimum panel uses one compact form containing only the two names,
read-only motor positions (including motor-power controls), and MOVE (BOTH).
It excludes `set_ax1_as`, `error_message`, `message`, and `current_location`.

Both less and minimum panels include a **MOVE (BOTH)** row with distance readback:
controller 1 `ax1_position` minus controller 2 `ax1_position`, displayed in mm
to three decimal places. This is a Taurus `eval:` model subscribed to the two
positions, not a new Tango attribute. Its updates follow the source readings;
they are not simultaneous hardware samples. Both source attributes must have
correct length units and calibration (normally `axis_unit=mm` with this stage's
`steps_per_unit=12500`). The arrows send the same signed relative step in mm
to both controllers, reading both current positions before writing either
target. Commands are sent back-to-back with no synchronization or wait for
arrival. When both axes reach their targets, separation is preserved within
positioning resolution; it may vary during motion. Wait for both axes to stop
before the next click. The step is shared between panels and starts at 0.100 mm.
A failed write reports that separation may have changed; moves are not retried
or rolled back automatically. Verify positions after a fault or limit stop.

Hardware-free tests in [test_grating_gui.py](test_grating_gui.py) cover device
pairing, signed distance/unit conversion, and the real Taurus/Qt display widgets.

### Launchers

On this Windows PC, [auto_start_Newmark_gratings.bat](../shortcut/Windows/auto_start_Newmark_gratings.bat)
starts the `PW_grating_1` and `PW_grating_2` server instances in minimized console
windows, then calls [start_Newmark_GUI.bat](../shortcut/Windows/start_Newmark_GUI.bat).
The GUI launcher waits 15 seconds and opens the combined GUI. It can also be
double-clicked separately when the servers are already running.

Both scripts use the repository's virtual environment and working directory.
They preserve `TANGO_HOST` if defined; otherwise they use this installation's
database, `192.168.131.39:10000`. They do not update code or activate a shell
environment. The delay is not a readiness check: the database/network and both
controllers must be available. Do not run the server launcher again while the
servers are already running (including servers started from the menu).

A shortcut named **Newmark gratings startup** in the current user's Windows
Startup folder runs the server launcher at sign-in, not before login. Only this
one shortcut is needed; it also launches the delayed GUI. To disable automatic
startup, remove that shortcut. To change the delay, edit the `timeout /t 15`
value in the GUI launcher. If the repository moves, update the shortcut target.

Register a Tango server instance whose class is `Newmark`, configure its properties in the Tango database, then start the server with the instance name. For the direct USB Type-B connection, the defaults `connection_type=usb`, `usb_device_index=0`, and an empty `dll_path` use the included DLL. The launcher and GUI mirror the ESP301 workflow:

- `python Newmark/menu.py`
- `python Newmark/server.py <instance>`
- `python Newmark/GUI.py <device-name>`

The native USB connection does not create a COM port and therefore does not use `pyserial`. The alternative RS-485 interface generally requires a suitable USB-to-RS-485 adapter. Ethernet transport is not used.
