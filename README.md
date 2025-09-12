Use [Tango Controls](https://www.tango-controls.org) as the control system software in ZEUS. Most of the code here is written in Python and is based on [pytango](https://pytango.readthedocs.io/en/latest/contents.html).

# Getting Started

## Installation

### Windows computer

- Install the required packages on a Windows computer.

```
#go to the required destination folder
python -m venv venv
./venv/Script/Activate.ps1
pip install -r requirements.txt
```

- Set the environment variables. Search "Environment" and select "Edit the system environment variables". On the pop-up window, select "Environment variables", then "New..". Enter "Variable name": TANGO_HOST. Enter "Variable value": 192.168.131.90:10000.

### Unix computer

- Install the required packages on a Unix computer.

```
#go to the required destination folder
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

- Set the environment variables. First open the file,

```
  nano ~/.bashrc
```

- Then insert the following code to the top of the file.

```
TANGO_HOST = 192.168.131.90:10000
```

## Introduction

- File structure. In each device type folder, there are a few files. They are device server file, client GUI file, menu file and example code file. it is recommended to use "menu.py" as the GUI to start server and client.
- You can either use the GUI, do the programming or do both. The following examples are mostly for code users and the commands are self-explanatory. However, you should be able to find the corresponding configurations in the [Taurus GUI](https://taurus-scada.org/) easily.

## Quick start

Assuming you are working on a computer with all the required software installed, start the menu file in from the terminal:

```
python path/to/menu.py
```

- To use a computer as a device server, select the name of the device and "start server".
- To use a computer as a client, select the name of the device and "start Taurus GUI".
- To shut down the device server or the client, click the 'X' button.

## Data acquisition

Usually we use data acquisition scrip to visualize the data from multiple devices and save them to a designated folder.
Run "Python .DAQ/GUI.py" to start the GUI.
A few buttons on the interface.

- "Select" button. Select the devices that we would like to acquire the data from.
- Device name buttons. Start the device server. Blue background of the button indicates the devices are started successfully.
- "GUI" button. Start a Taurus GUI for the selected devices.
- "Scan" button. Select the scannable devices and their parameters vs. shot number.
- "Start" button. Start acquisition. For most image devices (cameras), this will disable automatic polling.

It is possible to run "Python .DAQ/GUI.py" in a second computer to start a second Taurus GUI. Just don't start the device servers again or "Start".

## Add a new device to Tango system

Run "./register/register_device_server.py" and follow the prompts.

## Basler/Allied Vision camera

The example code shows how to obtain one image by triggerring a Basler camera with a software trigger.

```python
import tango
import numpy as np

# replace 'test/basler/1' with your device name
dp = tango.DeviceProxy('test/basler/1')
dp.save_data = True
dp.trigger_selector = 'FrameStart'
dp.trigger_source = 'Software'
dp.send_software_trigger()
while True:
    if dp.is_new_image:
        print(f'Mean intensity of the image is: {np.mean(dp.image)}.')
        break
```

Use live mode with the trigger off.

```python
import tango

dp = tango.DeviceProxy('test/basler/1')
dp.trigger_source = 'Off'
```

Acquire a set of images from the camera with external triggers. When the bandwidth is smaller than data generation rate, the camera stores images in its buffer and transfers the files to the host computer later.

```python
import tango
import numpy as np

dp = tango.DeviceProxy('test/basler/1')
dp.trigger_selector = 'AcquisitionStart'
dp.repetition = 3
dp.frames_per_trigger = 3
dp.trigger_source = 'External'
dp.is_polling_periodically = False
img_num_to_acquire = dp.repetition * dp.frames_per_trigger
acquired = 0
while True:
    if dp.is_new_image:
        print(f'Mean intensity of the image is: {np.mean(dp.image)}.')
        acquired += 1
        if acquired == img_num_to_acquire:
            break
```

## Gentec-EO energy meter/power meter

To acquire the current reading from the device:

```python
import tango

dp = tango.DeviceProxy('test/gentec/1')
print(dp.main_value)
print(dp.wavelength)
```

## LeCroy scopes

Requires Pywin32 and "activedsoinstaller2.39.exe"
To acquire the waveform:

```python
import tango

scope = tango.DeviceProxy('facility/lecroy/wavesurfer_3034z_1')
print(scope.waveform_c1_x)
print(scope.waveform_c1_y)
```

## DG535

Requires Pyvisa

```python
import tango

dg = tango.DeviceProxy('facility/dgd535/1')
print(dg.A_relative_channel)
print(dg.A_relative_delay)
```

## Laser warning sign

To acquire the status of the laser warning signs:

```python
import tango

dp = tango.DeviceProxy('facility/laser_warning_sign/1')
print(dp.ta1)
```
