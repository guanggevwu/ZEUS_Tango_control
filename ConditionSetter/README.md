# Condition setter

Run `python -m ConditionSetter.condition_setter` from the repository root, or run
`condition_setter.py` directly. Python's Tkinter and the project's existing
PyTango dependency are sufficient. `--file PATH` selects a different file for
local testing; the default is `Z:\software\Condition_setter\condition_list.txt`.

## Condition file

The file is UTF-8, comma-separated text (CSV), despite the `.txt` extension:

```csv
name_of_condition,domain/family/member/position,domain/family/member/enabled,domain/family/member/label
example1,1.0,true,"alignment, first pass"
example2,3.6,false,
```

- Headers after `name_of_condition` are full Tango attribute names. Condition
  names and attribute headers must be unique.
- Edit the file in a text editor or spreadsheet. Quote values containing commas,
  quotes, or newlines using standard CSV quoting. String whitespace is preserved.
- Blank cells mean **unused attributes** and are hidden in the Load window.
  Empty-string attribute values cannot be represented with this convention.
- Load request values are read-only. After an external edit, click **Reload file**
  or open the condition dropdown to reload its contents.
- Saves re-read the file, preserve other conditions, and append new attribute
  columns. Replacing an existing condition requires confirmation and replaces
  the whole condition, not just its populated cells. The file and parent folder
  are created on the first save if needed.
- Saves replace the file through a temporary file in the same directory. Avoid
  simultaneous editing/saving by multiple applications; there is no shared-file
  locking across computers.

## Using the windows

The root window has **Load conditions**, **Save conditions**, and **Select source
file** buttons. The file picker opens at `Z:\software\Condition_setter\` and lets
you choose a `.txt` source. Without a selection (or `--file` override), the source
is `condition_list.txt` in that folder. The full source path appears at the top
of both Load and Save windows.

Selecting a valid source updates all open windows and redirects subsequent loads,
saves, and deletions to that file. Load selections are cleared; Save-window drafts
are kept, but readback refresh stops until **See current value** is clicked again.
Pending snapshots from the previous source are discarded. Cancelling the picker
or choosing an invalid file leaves the current source unchanged. Source changes
are blocked while device writes are in progress and are not remembered on restart.

**Load conditions:** select a condition to start one-second readback refresh.
**Set** writes one value; **Set all** writes left to right, stopping on the first
failure. Earlier writes are not rolled back. Motor completion is not awaited.
Selecting a condition never writes to a device.

**Delete this condition**, beside **Reload file**, asks for confirmation before
removing the selected condition. It also removes attribute columns that have no
value in any remaining condition, preserving the order and values of columns
still in use. Deleting the last condition leaves only the `name_of_condition`
header. Open Load windows refresh automatically. Deleting does not write to devices.

**Save conditions:** starts with three attribute columns; **Add an attribute
column** adds more. Enter full attribute names and request values, then use
**Save request value as** to create a condition without contacting any devices.
Blank request values are omitted. **See current value** starts readback refresh;
editing an attribute name stops it until that button is clicked again.

In either window, **Save current as** reads a fresh snapshot of the listed
attributes and asks for a condition name. No condition is saved if any read fails.

Numeric, string, and boolean scalar writes are supported. Boolean text accepts
`true`, `false`, `1`, or `0` (case-insensitive). Integer attributes require integer
text. Types are checked against Tango metadata when writing, so offline request
values can be prepared even when devices are unavailable. Arrays, images, and
other Tango types such as enums/states are not supported for writing.

Tango calls run outside the Tk event loop. Read errors are displayed and retried;
slow reads never accumulate overlapping refresh jobs. Closing a window cancels
queued work and stops subsequent writes, but cannot undo an already issued write.
