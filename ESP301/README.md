# Guarded Arrow-Button Moves

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
.\venv\Scripts\python.exe -m unittest tests.test_motor_jog -v
```

These tests extract only the methods under test and use mocked controller I/O
and device proxies. They do not import device modules, connect to Tango, or
start hardware servers. Do not use the full test suite as an offline check:
other tests may require live devices. Physical controller timing and motion
have not been tested by this change.