import numpy as np
from datetime import datetime
import os
import logging
from daq import Daq

dt_string = datetime.now().strftime("%Y%m%d")
run_num = input('\nPlease input a run number: ')
save_dir = os.path.join(
    r'Z:\user_data\2024\Qing_Zhang\TA_data', f'{dt_string}_run{run_num}')
# select_cam_list = ['TA2-NearField', 'TA2-FarField', "TA2-GOSSIP"]
select_cam_list = ['test/basler/testcam', 'facility/file_reader/file_reader_1']
# select_cam_list = ['test/basler/testcam']
daq = Daq(select_cam_list, dir=save_dir)
daq.set_camera_configuration()
daq.take_background()
daq.test_mode()
daq.acquisition()
