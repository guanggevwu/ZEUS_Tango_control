# the key of this table, i.e., the name of the combination needs to include its class name.
device_name_table = {
    'TA1_gxregulator_combination': ['TA1/gx_regulator/TA1_regulator_1', 'TA1/gx_regulator/TA1_regulator_2'],
    '3PW_basler_combination': ['laser/basler/3PW_Screen', 'laser/basler/3PW_Grating-4_NF',  'laser/basler/3PW_Grating-4_FF'],
    'testcam_basler_combination': ['test/basler/testcam', 'facility/file_reader/file_reader_1'],
    'MA2_genteceo_combination': ['laser/gentec/MA2', 'laser/gentec/MA2_north', 'laser/gentec/MA2_south']
}
# For most of the combination cases , the instance name is same as the last part of the device name. For non-combination cases, the instance name is searched by class name  and thus no problem here.
instance_exception = {"testcam_basler_combination": ["testsr"]}
instance_table = dict({key: [i.split(
    '/')[-1] for i in value] for key, value in device_name_table.items() if key not in instance_exception}, **instance_exception)

# For multiple cameras (not combination), configuration for a single camera is checked first, but only for "image" key.
image_panel_config = {
    'TA1_basler_combination1': {"image_number": False, 'command': False, "combine_form_with_onshot": True},
    'TA2_basler_combination1': {"image_number": False, 'command': False, "combine_form_with_onshot": True},
    '3PW_basler_combination': {'image': 'flux', 'calibration': True},
    'testcam_basler_combination': {"combine_form_with_onshot": False},
    'laser/basler/3PW_Grating-4_NF': {'image': 'flux', 'calibration': True},
    'laser/basler/3PW_Screen': {'image': 'flux', 'calibration': True},
    # 'test/basler/test': {'image': 'image_with_MeV_mark', 'calibration': True},
    'laser/basler/3PW_Grating-4_FF': {'image': 'image', 'calibration': False},
    'TA1/basler/TA1-EspecH': {'image': 'image_with_MeV_mark'},
}
