import json
import os


CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'UI_config.json')


def load_ui_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError('UI configuration must be a JSON object.')
    return config


_ui_config = load_ui_config()
device_name_table = _ui_config.get('device_name_table', {})
image_panel_config = _ui_config.get('image_panel_config', {})
basler_server_config = _ui_config.get('basler_server_config', {})
