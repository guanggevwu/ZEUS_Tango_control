'''
Written by Yong Ma, 06-02-2023, yongm@umich.edu -- Edited for TA2 by Paul

* This code is for triggering and saving the images taken by Basler cameras.
* To use it, you have to turn off the Pylon viewer or any other softwares that using the basler cameras first.
* Install pypylon by pip install pypylon if it is not on this PC.
* When more than 2 GigE cammeras are connected to the same POE, there could be a bandwidth issue which gives black lines on the read-out.
* To solve the bandwidth issue, use the bandwidth manager in Pylon to automatively optimize the bandwidth of each GigE camera. 
* The data saved to the diags_path will keep being over-written, but the DAQ code will make sure to grab the most recent data in each path and save the data with unique IDs in the final save_paths in DAQ.
* Automatically find the user defined camera names and ID and save the data to the corresponding folders (with the same user defined names) accordingingly. 
'''
from pypylon import pylon
import numpy as np
from datetime import datetime
import time
import os
import matplotlib.pyplot as plt
import skimage.io
from pathlib import Path
parent_path = "C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\"

# get instance of the pylon TransportLayerFactory
tlf = pylon.TlFactory.GetInstance()
devices = tlf.EnumerateDevices()

cams = []
cams_names = []

select_cam_list = ['TA2-NearField', 'TA2-FarField', 'TA2 ESPEC', 'TA2 S2W']
# select_cam_list = ['TA2-GOSSIP','TA2-NearField','TA2-FarField']
# select_cam_list = ['TA3-EspecL']

numberOfImagesToGrab = 9999
if devices:
    for i in range(len(devices)):
        # Only find the TA2 cameras. They are cameras from the laser room connected to the network which we don't want to deal with.
        if devices[i].GetUserDefinedName() in select_cam_list:
            if "_AlignCam" not in devices[i].GetUserDefinedName():
                print('Detected TA2 basler camera: ',
                      devices[i].GetModelName(), devices[i].GetUserDefinedName())
                cams.append(pylon.InstantCamera(tlf.CreateDevice(devices[i])))
                cams_names.append(devices[i].GetUserDefinedName())
else:
    print('No TA2 basler cameras connected! Connect them and rerun the code (Quit by Ctrl+break).\n')


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
        cams[i].PixelFormat = "Mono12"
        try:
            cams[i].ExposureTime = 200000  # in us
        except Exception:
            cams[i].ExposureTimeRaw = 200000
        try:
            cams[i].Gain.SetValue(0)
        except Exception:
            cams[i].GainRaw.SetValue(230)
        try:
            cams[i].TriggerDelay.SetValue(0)
        except Exception:
            cams[i].TriggerDelayAbs.SetValue(0)
        cams[i].TriggerSelector = "FrameStart"
        cams[i].GainAuto.SetValue('Off')
        # cams[i].TriggerDelay.SetValue(0)
        cams[i].TriggerSource.SetValue("Line1")
        cams[i].TriggerActivation.SetValue('RisingEdge')
        cams[i].TriggerMode.SetValue("On")
        cams[i].StartGrabbingMax(numberOfImagesToGrab)
        shot_numbers.append(1)
        cam_dir = Path(parent_path + '{}-tmp'.format(cams_names[i]))
        if not cam_dir.is_dir():
            os.makedirs(cam_dir)
    print('Boring! Waiting for a trigger.')
    try:
        while True:

            # sleep for 1 second because there might be some cameras saving slow. Could be solved by taking the data from the buffer.
            # time.sleep(1)
            for i in range(len(cams)):
                if cams[i].IsGrabbing():
                    grab = cams[i].RetrieveResult(
                        100, pylon.TimeoutHandling_Return)
                    # print(dir(grab))

                    if grab.IsValid():
                        if grab.GrabSucceeded():
                            now = datetime.now()
                            # dt_string = now.strftime("%d-%m-%Y")
                            dt_string = now.strftime("%d-%m-%Y-%H-%M-%S")
                            array_size = np.shape(grab.Array)
                            skimage.io.imsave(parent_path + '{}-tmp\\{}-{}.tiff'.format(
                                cams_names[i], cams_names[i], dt_string), grab.Array, check_contrast=False)

                            print("Shot {} taken for {} saved {}:".format(
                                shot_numbers[i], cams_names[i],  {array_size}))
                            shot_numbers[i] += 1
    finally:
        for n, cam in enumerate(cams):
            cam.Close()
            print(f'{cams_names[n]} closed')
