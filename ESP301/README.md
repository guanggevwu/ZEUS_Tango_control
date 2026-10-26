# ESP301 / ESP302

## GUI panels

Each device has one combined control panel named by its Tango device name,
replacing the former `_less` and `_more` panels. It includes axis controls,
diagnostics, raw commands, Init/stop, and per-axis limit/coordinate commands.
Turning-box reset controls remain available. Grating devices also retain their
separate `_minimum` panel. Restart the GUI to use the new layout.

Combination windows start with different devices tiled side by side (a grid
for larger combinations). Panels belonging to the same device remain tabbed
together, with the main controls selected. Single-device layouts are unchanged.

Both forms preserve their font-sized row minimum heights (including composite
motor editors). Reducing panel height scrolls the form contents rather than
compressing large-font text. The outer panel remains resizable.

## Presets use ConditionSetter

Generic saved locations are managed by [ConditionSetter](../ConditionSetter/README.md),
not by the ESP301 device server or GUI. Use full Tango axis attribute names
(for example, `TA2/esp301/esp302_ta2_1/ax1_position`) in condition files.
The server no longer exposes `current_location`, `saved_location_source`,
`user_defined_locations`, or `load_server_side_list`. It no longer reports a
matching generic preset name. The GUI neither reads/creates location files nor
uploads preset lists to the server.

The removed location files' saved data is preserved in
[the legacy preset archive](legacy_presets.md). Before migrating any other
server/client copies, verify the device name and map each tuple using the
server's configured `axis` order, **not** the GUI's `axis_order` display order.
The archived values have not been applied to hardware or automatically imported
into a live ConditionSetter file.

### Turning box and ordinary motion

Turning-box `customized_location`, TA1/TA2/TA3 transition sequences, intermediate
positions, waits, and `reset_to_TA1` remain unchanged. These ordered motion
routines are not generic presets. Do not replace them with a ConditionSetter
row of independent axis targets: **Set all does not wait for motion completion**.

Axis positioning, guarded jogging, stop, limit moves, coordinate setting, and
grating controls also remain unchanged. ConditionSetter's direct axis writes
do not inherit the arrow buttons' busy guards.

### Deployment

- Update the ESP301 server and GUI together, and restart when the hardware is
  safe. The old GUI requires the removed preset API.
- Update external scripts, saved Taurus panels, and condition files that use
  the removed attributes/command. Archive useful location files on other
  computers before deleting them.
- Review the Tango database for obsolete memorized values, attribute settings,
  and polling entries for the removed ESP301 attributes. Remove only those
  obsolete entries; preserve axis configuration and turning-box settings.
  Repository changes do not modify the live Tango database.
- Other motion-device servers and shared GUI widgets are unaffected.

## Guarded Arrow-Button Moves

The shared motor widgets use `jog_axis([axis, signed_step])` and
`jog_grating(signed_step)` for the `ESP301` Tango class, which also serves ESP302
controllers. Newmark also uses guarded jogs; see
[Newmark's documentation](../Newmark/README.md). Owis and Newport XPS retain
their previous shared-widget path: read position in the GUI, add the signed
step, and write an absolute target. Owis's position-write path has no explicit
busy guard. XPS rejects another move while its per-axis motion worker is alive;
this is a server-thread check, not a live controller-status check.

Both Newport manuals describe `PR` as a displacement from the current position
and permit it while motion is in progress. It is not a queue of completed
increments, so switching from read-position-plus-`PA` to `PR` would not guarantee
that two rapid 0.1 mm clicks produce 0.2 mm of travel.

- [ESP301 User Manual](https://www.newport.com/medias/sys_master/images/images/hda/h3e/9117547069470/ESP301-User-s-Manual.pdf): `PR`, printed page 3-110; `MD?`, page 3-94.
- [ESP302 Programmer's Manual](https://www.newport.com/medias/sys_master/npresources/h84/hd0/9965815103518/ESP302%20-%20Programmer%27s%20Manual/ESP302-Programmer-s-Manual.pdf): `PR`, printed page 104; `MD?`, page 90.

The jog commands query `MD?` directly before reading positions. A busy axis
returns `False` without issuing a move; the grating command rejects the entire
request if either axis is busy. Invalid status or position replies raise an
error before any move is sent. Accepted requests read fresh positions and send
absolute targets. A grating request sends both targets in one command line.
Ignored clicks are discarded, not deferred or accumulated.

This protects the arrow-button workflow against repeated clicks during motion.
It does not interlock direct absolute writes, raw commands, other control
connections, or background motion routines. Sending both targets together is
not a synchronized trajectory: equal final increments do not guarantee constant
spacing throughout travel, or if a controller rejects one target or an axis
faults. This is not collision protection.

Deploy the server and GUI changes together, restarting them only when the
hardware is safe. An older server without these commands causes the updated
ESP301 arrow buttons to log an error; they do not fall back to unguarded moves.

## Offline Tests

From the repository root:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_motor_jog tests.test_newport_axis_order tests.test_esp301_presets_removed tests.test_esp301_form_layout -v
```

These tests extract only the code under test and use mocked controller I/O,
GUI components, and device proxies. Preset-removal tests cover startup without
preset attributes or files and preservation of turning-box sequencing.
Layout tests use real Qt/Taurus widgets with local `eval:` models to check
scrollbars and row heights at small and large viewport sizes, without hardware.
They do not import device modules, connect to Tango, or
start hardware servers. Do not use the full test suite as an offline check:
other tests may require live devices. Physical controller timing and motion
have not been tested by this change.
