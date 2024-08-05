from daq import Daq
save_dir = '/home/qzhangqz/Tango/ZEUS_Tango_control/ignored_folder'
select_cam_list = ['TA2-NearField', 'TA2-FarField']
daq = Daq(save_dir, select_cam_list=select_cam_list, shots=10)
daq.simulate_send_software_trigger(1)
