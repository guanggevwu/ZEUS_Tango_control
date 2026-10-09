# Clock

- [clock.py](clock.py): Tango Clock server (moved from the common folder).
- [clock_GUI.py](clock_GUI.py): Taurus GUI with a large live time display, host computer, state, and status.

From the repository root, with the project dependencies installed and `TANGO_HOST` configured:

```powershell
python -m Clock.clock clock
python -m Clock.clock_GUI
```

Run the server and GUI in separate terminals. The GUI defaults to the registered
device `other/Clock/clock` and a 100 ms polling period. To select another device
or polling period:

```powershell
python -m Clock.clock_GUI other/Clock/clock --polling 500
```

Multiple device names can be supplied to create a panel for each clock.
The time is read from the server, not generated on the GUI computer, and retains
the format `YYYY/MM/DD HH:MM:SS.ffffff`.

Update any external launchers that used the old common-folder server path to
use [clock.py](clock.py). The Tango class, instance, and device name are unchanged;
existing registrations do not need to be recreated.