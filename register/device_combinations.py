import json
import os
from tempfile import NamedTemporaryFile


CONFIG_PATH = os.path.join(os.path.dirname(
    __file__), 'device_combinations.json')

# For these combinations, the server instance cannot be derived from the final
# segment of each Tango device name.
instance_exception = {'testcam_basler_combination': ['testsr']}


def load_device_name_table():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError('Combination configuration must be a JSON object.')
    for combination_name, devices in data.items():
        if not isinstance(combination_name, str) or not isinstance(devices, list):
            raise ValueError(
                'Each combination must map a name to a device list.')
        if not all(isinstance(device, str) and device for device in devices):
            raise ValueError(
                f'All devices in {combination_name} must be non-empty strings.')
    return data


def _build_instance_table(table):
    return {
        name: instance_exception.get(
            name, [device.split('/')[-1] for device in devices])
        for name, devices in table.items()
    }


device_name_table = load_device_name_table()
instance_table = _build_instance_table(device_name_table)


def save_combination(combination_name, devices):
    devices = list(dict.fromkeys(device.strip() for device in devices
                                 if device.strip()))
    updated_table = load_device_name_table()
    updated_table[combination_name] = devices

    temporary_path = None
    try:
        with NamedTemporaryFile(
                'w', encoding='utf-8', dir=os.path.dirname(CONFIG_PATH),
                prefix='device_combinations_', suffix='.tmp', delete=False) as config_file:
            temporary_path = config_file.name
            json.dump(updated_table, config_file, indent=2)
            config_file.write('\n')
        os.replace(temporary_path, CONFIG_PATH)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)

    device_name_table.clear()
    device_name_table.update(updated_table)
    instance_table.clear()
    instance_table.update(_build_instance_table(device_name_table))
    return devices
