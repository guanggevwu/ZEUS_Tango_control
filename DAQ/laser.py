
import numpy as np
from datetime import datetime
import os
import logging
from daq import Daq
import atexit


dt_string = datetime.now().strftime("%Y%m%d")

save_dir = r'Z:\Laser Beam Images\Qing_test'
# select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
select_cam_list = ['test/basler/testcam']
daq = Daq(select_cam_list, dir=save_dir)
atexit.register(daq.termination)
daq.set_camera_configuration()
daq.test_mode()
daq.acquisition(interval_threshold=0)
