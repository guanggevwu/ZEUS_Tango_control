'''
Written by Yong Ma, 06-02-2023, yongm@umich.edu

* This code is for triggering and saving the images taken by Basler cameras.
* To use it, you have to turn off the Pylon viewer or any other softwares that using the basler cameras first.
* Install pypylon by pip install pypylon if it is not on this PC.
* When more than 2 GigE cammeras are connected to the same POE, there could be a bandwidth issue which gives black lines on the read-out.
* To solve the bandwidth issue, use the bandwidth manager in Pylon to automatively optimize the bandwidth of each GigE camera. 
* The data saved to the diags_path will keep being over-written, but the DAQ code will make sure to grab the most recent data in each path and save the data with unique IDs in the final save_paths in DAQ.
* Automatically find the user defined camera names and ID and save the data to the corresonding folers (with the same user defined names) accordingingly. 
'''
from pypylon import pylon
import numpy as np
from datetime import datetime
import time, os
import matplotlib.pyplot as plt
import skimage.io
from pathlib import Path

parent_path = "C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\"

add_laser_cam = True
replace_PW_with_TA2_Far = False
replace_TA1_with_TA2_Near = False
use_software_trigger = False
if add_laser_cam:
	import tango
	import sys
	sys.path.append(r'C:\Users\High Field Science\Desktop\Qing\ZEUS_Tango_control')
	from DAQ.daq import Daq
	if not replace_PW_with_TA2_Far:
		extra_cam_list = ['laser/basler/PW_Comp_In']
	else:
		extra_cam_list = ['TA2/basler/TA2-FarField']
		config_dict = {'ta2-farfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "Software", "is_polling_periodically": False},}
	daq = Daq(parent_path, select_cam_list=extra_cam_list)

# get instance of the pylon TransportLayerFactory
tlf = pylon.TlFactory.GetInstance()
devices = tlf.EnumerateDevices()

cams = []
cams_names = []

# Make folder with -tmp at the end for each new camera
#select_cam_list = ['TA1-EspecL', 'TA1-EspecH', 'TA1-Autocorr', 'TA1-Shadowgraphy']
if replace_TA1_with_TA2_Near:
	select_cam_list = ['TA2-NearField']
else:
	select_cam_list = ['TA1-EspecL', 'TA1-EspecH', 'TA1-Ebeam','TA1-Shadowgraphy']

numberOfImagesToGrab = 9999
if devices:
	for i in range(len(devices)):
		# Only find the TA1 cameras in the selec_cam_list. They are cameras from the laser room connected to the network which we don't want to deal with.
		if devices[i].GetUserDefinedName()  in select_cam_list:
			if "_AlignCam" not in devices[i].GetUserDefinedName():
				print('Detected TA1 basler camera: ', devices[i].GetModelName(), devices[i].GetUserDefinedName())
				cams.append(pylon.InstantCamera(tlf.CreateDevice(devices[i])))
				cams_names.append(devices[i].GetUserDefinedName())
else:
	print('No TA1 basler cameras connected! Connect them and rerun the code (Quit by Ctrl+break).\n')
  

# cams_openable = []
# for n,cam in enumerate(cams):
# 	try:
# 		cam.Open()
# 		cams_openable.append(True)
# 	except:
# 		cams_openable.append(False)
# 		print(f'{cams_names[n]} not openable and so not running')

# cams_names = [cams_names[i] for i in range(len(cams)) if cams_openable[i]]
# cams = [cams[i] for i in range(len(cams)) if cams_openable[i]]

if cams:
	shot_numbers = []
	for i in range(len(cams)):
		cams[i].Open()
		cams[i].PixelFormat.Value = "Mono12"
		try:
			cams[i].ExposureTime.Value = 100000 ## in us # was 100000
		except Exception:
			cams[i].ExposureTimeRaw = 100000
		try:
			cams[i].Gain.SetValue(0)
		except Exception:
			cams[i].GainRaw.SetValue(230)
		# try:
		# 	cams[i].TriggerDelay.SetValue(0)              # In [us]
		# except Exception:
		# 	cams[i].TriggerDelayAbs.SetValue(0)
		cams[i].TriggerSelector.Value = "FrameStart"
		cams[i].GainAuto.SetValue('Off')
		#cams[i].TriggerDelay.SetValue(0)
		if use_software_trigger:
			cams[i].TriggerSource.SetValue("Software")
		else:
			cams[i].TriggerSource.SetValue("Line1")
			cams[i].TriggerActivation.SetValue('RisingEdge')
		cams[i].TriggerMode.SetValue("On")
		cams[i].StartGrabbingMax(numberOfImagesToGrab)
		shot_numbers.append(1)
		cam_dir = Path(parent_path + '{}-tmp'.format(cams_names[i]))
		if not cam_dir.is_dir():
			os.makedirs(cam_dir)

	if add_laser_cam:
		if replace_PW_with_TA2_Far:
			daq.set_camera_default_configuration(config_dict=config_dict)
		else:
			pass
	print('Boring! Waiting for a trigger.')
	try:
		while True:
			if use_software_trigger:
				time.sleep(1)
				cams[i].TriggerSoftware.Execute()
				time.sleep(1)
			#### sleep for 1 second because there might be some cameras saving slow. Could be solved by taking the data from the buffer.
			# time.sleep(1)
			for i in range(len(cams)):
				if cams[i].IsGrabbing():
					grab = cams[i].RetrieveResult(100, pylon.TimeoutHandling_Return)
					# print(dir(grab))

					if grab.IsValid():
						if grab.GrabSucceeded():
							now = datetime.now()
							# dt_string = now.strftime("%d-%m-%Y")
							dt_string = now.strftime("%d-%m-%Y-%H-%M-%S")
							array_size = np.shape(grab.Array)
							skimage.io.imsave(parent_path + '{}-tmp\\{}-{}.tiff'.format(cams_names[i],cams_names[i], dt_string), grab.Array, check_contrast=False)
							
							print("Shot {} taken for {} saved {}:".format(shot_numbers[i], cams_names[i],  {array_size}))
							shot_numbers[i]+=1
			if add_laser_cam:
				daq.acquisition(shot_limit = 1)
	finally:
		for n,cam in enumerate(cams):
			cam.Close()
			print(f'{cams_names[n]} closed')









