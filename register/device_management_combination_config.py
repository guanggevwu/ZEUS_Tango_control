import os
root_path = os.path.dirname(os.path.dirname(__file__))
container = {
    'cameras': {'show_name': 'Camera', 'class': {'Basler': None,
                                                 'Vimba': None,
                                                 'FileReader': {'only_these_devices': ['facility/file_reader/andor_1', 'facility/file_reader/sophia', 'facility/file_reader/image_reader_1', 'facility/file_reader/image_reader_2', 'facility/file_reader/image_reader_3', 'facility/file_reader/track_lab_1', 'facility/file_reader/track_lab_2']}}, },
    'motion_control': {'show_name': 'Motion Control', 'class': {
        'ESP301': {'extra_devices': ['TA1_motor_combination', 'TA2_motor_combination', 'TA3_motor_combination']},
        'OwisPS': {'server_code_path': os.path.join(root_path, 'Owis', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'Owis', 'GUI.py')},
        'NewPortXPS': None,
        'Newmark': None,
        'ThorlabsKDC101': {'server_code_path': os.path.join(root_path, 'ThorlabsXA', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'ThorlabsXA', 'GUI.py')},
    }},
    'delay_generator': {'show_name': 'Delay Generator', 'class': {
        'DG535': {'server_code_path': os.path.join(root_path, 'DG', 'dg535_server.py'), 'GUI_code_path': os.path.join(root_path, 'DG', 'GUI.py')},
        'DG645': {'server_code_path': os.path.join(root_path, 'DG', 'dg645_server.py'), 'GUI_code_path': os.path.join(root_path, 'DG', 'GUI.py')}
    }},
    'energy_meter': {'show_name': 'Energy Meter', 'class': {'GentecEO': {'extra_devices': ['MA2_genteceo_combination'], 'server_code_path': os.path.join(root_path, 'Gentec', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'Gentec', 'Taurus_GUI.py')}}},
    '1D_devices': {'show_name': '1-D Device', 'class': {
        'FileReader': {'only_these_devices': ['facility/file_reader/spectrometer', 'other/file_reader/oscilloscope']}
    }},
    'pressure_regulator': {'show_name': 'Pressure Regulator', 'class': {'GXRegulator': {'extra_devices': ['TA1_gxregulator_combination', 'TA3_gxregulator_combination'], 'server_code_path': os.path.join(root_path, 'GX_regulator', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'GX_regulator', 'GUI.py')}}},
    'Labview_translator': {'show_name': 'Labview Translator', 'class': {'LabviewProgram': {'server_code_path': os.path.join(root_path, 'Labview', 'server.py'), 'GUI_code_path': os.path.join(root_path, 'Labview', 'GUI.py')}}},
    'laser_warning_sign': {'show_name': 'Laser Status', 'class': {'LaserWarningSign': None}},
    'miscellaneous': {'show_name': 'Miscellaneous', 'class': {
        'TSP01B': None,
        'Clock': {'server_code_path': os.path.join(root_path, 'Clock', 'clock.py'), 'GUI_code_path': os.path.join(root_path, 'Clock', 'clock_GUI.py')}
    }},
}
