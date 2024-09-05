device_name_table = {
    'TA1_basler_combination1': ['TA1/basler/TA1-Ebeam', 'TA1/basler/TA1-EspecH', 'TA1/basler/TA1-EspecL', 'TA1/basler/TA1-Shadowgraphy'],
    'TA2_basler_combination1': ['TA2/basler/TA2-NearField', 'TA2/basler/TA2-FarField'],
    'PW_Comp_In_basler_combination': ['laser/basler/MA3_NF', 'laser/basler/PW_Comp_In_NF',  'laser/basler/PW_Comp_In_FF'],
    'testcam_basler_combination': ['test/basler/testcam', 'facility/file_reader/file_reader_1']
}
# Dor most of the combination cases , the instance name is same as the last part of the device name. For non-combination cases, the instance name is searched by class name  and thus no problem here.
instance_exception = {"testcam_basler_combination": ["testsr"]}
instance_table = dict({key: [i.split(
    '/')[-1] for i in value] for key, value in device_name_table.items() if key not in instance_exception}, **instance_exception)

image_panel_config = {
    'TA1_basler_combination1': {"image_number": False, 'command': False, "combine_form_with_onshot": True},
    'TA2_basler_combination1': {"image_number": False, 'command': False, "combine_form_with_onshot": True},
    'PW_Comp_In_basler_combination': {'image': 'flux', 'calibration': True},
    'testcam_basler_combination': {"combine_form_with_onshot": False},
    'laser/basler/PW_Comp_In_NF': {'image': 'flux', 'calibration': True},
    'test/basler/testcam': {'image': 'flux', 'calibration': True},
    'laser/basler/PW_Comp_In_FF': {'image': 'flux', 'calibration': True}
}
