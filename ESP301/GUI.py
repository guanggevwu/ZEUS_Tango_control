from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox, TaurusValueLineEdit
from taurus.qt.qtgui.compact import TaurusReadWriteSwitcher
from taurus.qt.qtgui.display import TaurusLabel
import tango
import os
import sys
from taurus.qt.qtgui.button import TaurusCommandButton
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from common.config import device_name_table, image_panel_config
    from common.TaurusGUI_Argparse import TaurusArgparse
    from common.taurus_widget import RelativeMotion
    from Basler.GUI import BaslerGUI, create_app


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    esp_app = BaslerGUI(device_list, args.polling)

    # get the configuration
    for d in device_list:
        esp_app.add_device(d)
        location_file_path = os.path.join(os.path.dirname(
            __file__), f'{d.replace("/", "_")}_locations.txt')
        if not os.path.isfile(location_file_path):
            with open(location_file_path, 'w', newline='') as f:
                f.write(
                    "name positions\n")
        with open(location_file_path, 'r',) as f:
            tmp = []
            next(f)
            for line in f:
                name, positions = [e for e in line.replace(
                    '\t', ' ').strip().replace('"', '').split(' ') if e]
                tmp.append(f"{name}: ({positions})")
        # somehow Taurus.Device does not update the attribute
        if tmp:
            tango.DeviceProxy(d).user_defined_locations = tmp
        else:
            tango.DeviceProxy(d).load_server_side_list()
        dropdown = {}
        dropdown['current_location'] = (
            (locations, locations.split(':')[0]) for locations in esp_app.attr_list[d]['dp'].user_defined_locations)
        form_panel, form_layout = esp_app.create_blank_panel('v')
        esp_app.gui.createPanel(form_panel, f'{d}_form')
        esp_app.create_form_panel(form_layout, d,  dropdown=dropdown, exclude=[
            'ax1_step', 'ax2_step', 'ax3_step', 'set_ax1_as', 'set_ax2_as', 'set_ax3_as', 'ax12_step'], withButtons=False)
        command_list, modified_cmd_name, cmd_parameters = [], [], []
        command_with_axis_parameters = [
            'move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero']
        if 'grating' in d:
            relative_motion = RelativeMotion(esp_app, f'{d}/ax12_step', {
                'name': 'move_relative_axis12',
                'label': [f'ax12-', f'ax12+'],
                'params': [[0], [1]]
            })

            form_layout.addWidget(relative_motion.widget)
        esp_app.add_command(
            form_layout, d, command_list=['stop'])
        relative_panel, relative_layout = esp_app.create_blank_panel('v')
        esp_app.gui.createPanel(relative_panel, f'{d}_relative')
        for idx, axis in enumerate([1, 2, 3]):
            if f'ax{axis}_step' in esp_app.attr_list[d]['attrs']:
                relative_motion = RelativeMotion(esp_app, f'{d}/ax{axis}_step', {
                    'name': 'move_relative_axis',
                    'label': [f'ax{axis}-', f'ax{axis}+'],
                    'params': [[axis, 0], [axis, 1]]
                })
                relative_layout.addWidget(relative_motion.widget)
                command_list.append([])
                modified_cmd_name.append([])
                cmd_parameters.append([])
                for cmd in command_with_axis_parameters:
                    command_list[-1].append(cmd)
                    modified_cmd_name[-1].append(f'ax{axis}_{cmd}')
                    cmd_parameters[-1].append([axis])
                esp_app.add_label_widget(
                    relative_layout, d, f'set_ax{axis}_as')

        for axis in range(len(command_list)):
            esp_app.add_command(
                relative_layout, d, command_list=command_list[axis], modified_cmd_name=modified_cmd_name[axis], cmd_parameters=cmd_parameters[axis])
        esp_app.add_command(
            relative_layout, d, command_list=['stop'])
        if 'turning_box3' in d:
            esp_app.add_command(
                relative_layout, d, command_list=['reset_to_TA1'])
    esp_app.gui.removePanel('Manual')
    esp_app.gui.show()
    esp_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for ESP device', device_default='test/esp301/esp302_test', polling_default=1000)
    args = parser.parse_args()
    create_app()
