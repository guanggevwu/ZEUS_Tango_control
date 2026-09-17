import json
import os
from tempfile import NamedTemporaryFile
from common.ui_config import CONFIG_PATH, device_name_table, load_ui_config


def save_combination(combination_name, devices):
    devices = list(dict.fromkeys(device.strip() for device in devices
                                 if device.strip()))
    updated_config = load_ui_config()
    updated_table = updated_config['device_name_table']
    updated_table[combination_name] = devices
    updated_config['device_name_table'] = updated_table

    temporary_path = None
    try:
        with NamedTemporaryFile(
                'w', encoding='utf-8', dir=os.path.dirname(CONFIG_PATH),
                prefix='UI_config_', suffix='.tmp', delete=False) as config_file:
            temporary_path = config_file.name
            json.dump(updated_config, config_file, indent=2)
            config_file.write('\n')
        os.replace(temporary_path, CONFIG_PATH)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)

    device_name_table.clear()
    device_name_table.update(updated_table)
    return devices
