# Archived ESP301 generic presets

This is a historical data archive, not a runtime input file. ESP301 no longer
loads generic location files. Use [ConditionSetter](../ConditionSetter/README.md)
for future presets, after verifying device names and axis mapping.

## Nonempty preset data

Original file: `TA2_esp301_esp302_ta2_1_locations.txt`

```text
name positions
1 0.001,-0.101
2 0,-0.100
```

This legacy filename suggests `TA2/esp301/esp302_ta2_1`, but verify it against
the deployed device. The tuple follows the server's `axis` order, not GUI
display order. No automatic conversion or hardware writes have been performed.

## Header-only files

Each of the following contained only `name positions` and no saved presets:

- `esp302_ta2_1_server_locations.txt`
- `esp302_ta2_2_server_locations.txt`
- `laser_esp300_esp300_turning_box3_client_locations.txt`
- `laser_esp301_esp300_grating_client_locations.txt`
- `TA1_esp301_esp302_ta1_1_client_locations.txt`
- `TA1_esp301_esp302_ta1_2_client_locations.txt`
- `TA1_esp301_esp302_ta1_7_client_locations.txt`
- `TA2_esp301_esp302_ta1_5_client_locations.txt`
- `TA2_esp301_esp302_ta2_1_client_locations.txt`
- `TA2_esp301_esp302_ta2_2_client_locations.txt`
- `TA2_esp301_esp302_ta2_2_locations.txt`
- `TA3_esp301_esp302_ta3_1_client_locations.txt`
- `TA3_esp301_esp302_ta3_2_client_locations.txt`
- `test_esp301_esp302_ta1_2_client_locations.txt`
