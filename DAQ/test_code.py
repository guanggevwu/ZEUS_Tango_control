from daq import Daq
select_cam_list = ['test/basler/testcam']
daq = Daq(select_cam_list)
daq.simulate_send_software_trigger(interval=1, shots=3)
