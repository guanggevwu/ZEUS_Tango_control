    
import numpy as np
from datetime import datetime
import os
import logging
from daq import Daq

dt_string = datetime.now().strftime("%Y%m%d")
run_num = input('\nPlease input a run number: ')
save_dir = os.path.join(r'N:\2024\Qing_test', f'{dt_string}_run{run_num}')
# select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
select_cam_list = ['TA1/basler/TA1-Ebeam', 'TA1/basler/TA1-EspecH', 'TA1/basler/TA1-EspecL', 'TA1/basler/TA1-Shadowgraphy']
daq = Daq(save_dir, select_cam_list=select_cam_list, shots=30)
daq.set_camera_default_configuration()
# daq.take_background()
daq.test_mode()
daq.acquisition()