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
        if tango.DeviceProxy(d).info().dev_class == 'ESP301':
            less_list = ['user_defined_name', 'error_message', 'message', 'current_location', 'customized_location', 'ax1_position', 'set_ax1_as', 'ax2_position', 'set_ax2_as', 'ax3_position',
                         'set_ax3_as']
            if 'grating' in d:
                less_list.append('ax12_distance')
            more_list = ['host_computer', 'saved_location_source', 'user_defined_locations',
                         'raw_command', 'status', 'state']
            location_file_path = os.path.join(os.path.dirname(
                __file__), f'{d.replace("/", "_")}_client_locations.txt')
            if not os.path.isfile(location_file_path):
                with open(location_file_path, 'w', newline='') as f:
                    f.write(
                        "name positions\n")
            with open(location_file_path, 'r',) as f:
                tmp = []
                next(f)
                for line in f:
                    if line.strip():
                        name, positions = [e for e in line.replace(
                            '\t', ' ').strip().replace('"', '').split(' ') if e]
                        tmp.append(f"{name}: ({positions})")
            # somehow Taurus.Device does not update the attribute
            if tmp and tango.DeviceProxy(d).saved_location_source == 'client':
                tango.DeviceProxy(d).user_defined_locations = tmp
            else:
                tango.DeviceProxy(d).load_server_side_list()
            dropdown = {}
            dropdown['current_location'] = (
                (locations, locations.split(':')[0]) for locations in esp_app.attr_list[d]['dp'].user_defined_locations)
            dropdown['saved_location_source'] = (
                ('server', 'server'),  ('client', 'client'))
            less_panel, less_layout = esp_app.create_blank_panel('v')
            esp_app.create_form_panel(
                less_layout, d,  dropdown=dropdown, include=less_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in ['ax1_position', 'ax2_position', 'ax3_position', 'ax12_distance', 'customized_location']})
            command_list, modified_cmd_name, cmd_parameters = [], [], []
            command_with_axis_parameters = [
                'move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero']
            esp_app.add_command(
                less_layout, d, command_list=['stop'])
            more_panel, more_layout = esp_app.create_blank_panel('v')
            esp_app.create_form_panel(
                more_layout, d,  dropdown=dropdown, include=more_list, withButtons=False)

            for idx, axis in enumerate([1, 2, 3]):
                if f'ax{axis}_step' in esp_app.attr_list[d]['attrs']:
                    command_list.append([])
                    modified_cmd_name.append([])
                    cmd_parameters.append([])
                    for cmd in command_with_axis_parameters:
                        command_list[-1].append(cmd)
                        modified_cmd_name[-1].append(f'ax{axis}_{cmd}')
                        cmd_parameters[-1].append([axis])

            for axis in range(len(command_list)):
                esp_app.add_command(
                    more_layout, d, command_list=command_list[axis], modified_cmd_name=modified_cmd_name[axis], cmd_parameters=cmd_parameters[axis])
            esp_app.add_command(
                more_layout, d, command_list=['stop'])
            if 'turning_box3' in d:
                esp_app.add_command(
                    more_layout, d, command_list=['reset_to_TA1'])
            esp_app.gui.createPanel(more_panel, f'{d}_more')
            esp_app.gui.createPanel(less_panel, f'{d}_less')

    esp_app.gui.removePanel('Manual')
    esp_app.gui.show()
    esp_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for ESP device', device_default='test/esp301/esp302_test', nargs_string='+', polling_default=1000)
    args = parser.parse_args()
    create_app()
