import os
root_path = os.path.dirname(os.path.dirname(__file__))
container = {
    'cameras': {'show_name': 'Cameras', 'class': {'Basler': None,
                                                  'Vimba': None,
                                                  'FileReader': {'only_these_devices': ['facility/file_reader/andor_1']}}, },
    'motion_control': {'show_name': 'Motion Control', 'class': {'ESP301': {'extra_devices': ['TA1_motor_combination', 'TA2_motor_combination']},
                                                                'OwisPS': {'server_code_path': os.path.join(root_path, 'Owis', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'Owis', 'GUI.py')}}},
    'delay_generator': {'show_name': 'Delay Generator', 'class': {'DG535': {'server_code_path': os.path.join(root_path, 'DG', 'dg535_server.py'), 'GUI_code_path': os.path.join(root_path, 'DG', 'GUI.py')},
                                                                  'DG645': {'server_code_path': os.path.join(root_path, 'DG', 'dg645_server.py'), 'GUI_code_path': os.path.join(root_path, 'DG', 'GUI.py')}}},
    'energy_meter': {'show_name': 'Energy Meters', 'class': {'GentecEO': None}},
    '1D_devices': {'show_name': '1-D Devices', 'class': {'FileReader': {'only_these_devices': ['facility/file_reader/spectrometer', 'other/file_reader/oscilloscope']}}},
    'pressure_regulator': {'show_name': 'Pressure Regulators', 'class': {'GXRegulator': {'server_code_path': os.path.join(root_path, 'GX_regulator', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'GX_regulator', 'GUI.py')}}},
    'TH': {'show_name': 'TH', 'class': {'TSP01B': None}},
    'Labview_translator': {'show_name': 'Labview Translator', 'class': {'LabviewProgram': {'server_code_path': os.path.join(root_path, 'Labview', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'Labview', 'GUI.py')}}},
    'laser_warning_sign': {'show_name': 'Laser Status', 'class': {'LaserWarningSign': None}}
}
