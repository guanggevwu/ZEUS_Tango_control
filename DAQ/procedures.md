# Operation

1. Start the cameras.
Make sure the cameras are not used by Pylon viewer or other programs.
Open a terminal. Enter the following command:
cd .\Desktop\Qing\ZEUS_Tango_control\
.\venv\Scripts\Activate.ps1
python .\Basler\menu.py
On the popup window, select "TA2-NearField" and "start server". In the terminal, it should show 
"Camera is connected. TA2-NearField: 24871200"
Select "TA2/basler/TA2-NearField" and "Start Taurus GUI".
Repeat previous operations for every camera.

2. Start the data acquisiton script.
Open a terminal. Enter the following command:
cd .\Desktop\Qing\ZEUS_Tango_control\
.\venv\Scripts\Activate.ps1
python .\DAQ\daq.py
When the acquisition is finished, press "CTRL+C" in the terminal.

3. Add new camera to acquisition list.
Add configuratio to "config_dict". Add camera name to "select_cam_list".

# Add a device to Tango control system

How to add a new device to Tango.
1. To identify the device, one would need unique id. It can either be an IP address, serial number or somethimes just device type. For Basler cameras, we can use the "friendly_name" which you defined in Pylon Viewer. Although you can use any computers for this step, I suggest to use the Linux computer in the experimental control room. Find the Tango code repository, edit register/register_device_server.py. For example, to add a camera named "TA2-Alignment", you need to insert the line to "reg_dict"
```
"basler_TA2-Alignment": {'server': 'Basler/TA2-Alignment', '_class': 'Basler', 'name': 'TA2/basler/TA2-Alignment'},
```
to "reg_dict". Save and then run the command in terminal:
```
python register/register_device_server.py add basler_TA2-Alignment
```

2. Use the Linux computer in the experimental control room. Find the JIVE window, and find the device you just added. Select "properties", click "add", enter "firendly_name" and "TA2-Alignment" as key and value repectively, and click "Apply".
