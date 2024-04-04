Use [Tango Controls](https://www.tango-controls.org) as the control system software in ZEUS. Most of the code here are written in Python and based on [pytango](https://pytango.readthedocs.io/en/latest/contents.html)

# Getting Started

## Installation

- Install the required packages on a Windows computer.

```
#go to the required destination folder
python -m venv venv
./venv/Script/Activate.ps1
pip install -r requirements.txt
```

- Set the enviroment variables.
  TANGO_HOST = 192.168.131.90:10000

## Introduction

- File structure. In each device type folder, there are a few files in it. They are device server file, client GUI file, menu file and example code file. it is recommended to use "menu.py" as the GUI to start server and client.
- The following examples are mostly for code user. However, you should be able to find the corresponding configurations in the GUI easily.

## Basler camera

The example code shows how to trigger the Basler camera by sending a software trigger.

```python
import tango
import numpy as np

# replace 'test/basler/1' with your device name
dp = tango.DeviceProxy('test/basler/1')
dp.save_data = True
dp.trigger_source = 'Software'
dp.get_ready()
dp.send_software_trigger()
while True
    if dp.is_new_image:
        print(f'Mean intensity of the image is: {np.mean(dp.image)}.')
        break
```

Use live mode with the trigger off.

```python
import tango

# replace 'test/basler/1' with your device name
dp = tango.DeviceProxy('test/basler/1')
dp.trigger_source = 'Off'
dp.get_ready()
```

To acquire a set of images from the camera with external triggers.

```python
import tango
import numpy as np

# replace 'test/basler/1' with your device name
dp = tango.DeviceProxy('test/basler/1')
dp.save_data = True
dp.trigger_source = 'External'
dp.trigger_selector = 'AcquisitionStart'
dp.repetition = 3
dp.frames_per_trigger = 3
dp.get_ready()
img_num_to_acquire = dp.repetition * dp.frames_per_trigger
acquired = 0
while True
    if dp.is_new_image:
        print(f'Mean intensity of the image is: {np.mean(dp.image)}.')
        acquired += 1
        if acquired == img_num_to_acquire:
            break
```

## Gentec-EO energy meter/power meter

To aquire the current reading from the device:

```python
import tango

device_name = 'test/gentec/1'
dp = tango.DeviceProxy(device_name)
print(dp.main_value)
print(dp.wavelength)
```

## Laser warning sign

To acquire the status of the laser warning signs:

```python
import tango

device_name = 'facility/laser_warning_sign/1'
dp = tango.DeviceProxy(device_name)
print(dp.ta1)
```
