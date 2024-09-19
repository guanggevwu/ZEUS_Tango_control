# use lower case
# seems case insensitive
default_config_dict = {
    'ta2-nearfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 230, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
    'ta2-farfield': {'format_pixel': "Mono12", "exposure": 1000, "gain": 0, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
    'ta2-gossip': {'format_pixel': "Mono12", "exposure": 1000, "gain": 240, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False},
    'PW_Comp_In'.lower(): {'format_pixel': "Mono12", "exposure": 5000, "gain": 136, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False, "saving_format": '%s_%t_%e_%h.%f'},
    'testcam': {'format_pixel': "Mono12", "exposure": 1000, "trigger_selector": "FrameStart", "trigger_source": "external", "is_polling_periodically": False, "saving_format": '%s_%t_%e_%h.%f'},
    'file_reader_1': {"is_polling_periodically": False, "saving_format": 'FileReader_%s.%f'},
    'all': {"saving_format": '%s_%t.%f', "trigger_source": "external", "is_polling_periodically": False}
}
