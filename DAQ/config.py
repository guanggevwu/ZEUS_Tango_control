# default setting for camera parameters
# The key is the user_defined_name. It is not always equal to the third part of the device name.
default_config_dict = {
    'TA2-NearField': {'format_pixel': "Mono12", },
    'TA2-FarField': {'format_pixel': "Mono12",  },
    # 'TA2-Gossip': {'format_pixel': "Mono12", "exposure": 1000, "gain": 240},
    'PW_Comp_In'.lower(): {'format_pixel': "Mono8", "exposure": 5000, "gain": 136, "saving_format": '%s_%t_%e_%h.%f'},
    'test': {'format_pixel': "Mono8", "exposure": 1000, "saving_format": '%s_%t_%e_%h.%f'},
    'file_reader_1': {"saving_format": 'FileReader_%s.%f'},
    'scope': {"saving_format": '%s_%t_%o'},
    'all': {"saving_format": '%s_%t.%f', "trigger_selector": "FrameStart", "trigger_source": "External", "is_polling_periodically": False}
}
