from common.GUI import GuiBase
from common.TaurusGUI_Argparse import TaurusArgparse
from common.config import device_name_table
import tango
import os


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    newport_xps_app = GuiBase(device_list, args.polling)

    # get the configuration
    for d in device_list:
        newport_xps_app.add_device(d)
        if tango.DeviceProxy(d).info().dev_class == 'NewPortXPS':
            available_axis = []
            less_list = ['user_defined_name', 'error_message',
                         'message', 'current_location', 'customized_location']
            for axis in range(1, 9):
                if hasattr(tango.DeviceProxy(d), f'ax{axis}_position'):
                    available_axis.append(axis)
                    less_list.extend(
                        [f'ax{axis}_position', f'set_ax{axis}_as'])
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
                (locations, locations.split(':')[0]) for locations in newport_xps_app.attr_list[d]['dp'].user_defined_locations)
            dropdown['saved_location_source'] = (
                ('server', 'server'),  ('client', 'client'))
            less_panel, less_layout = newport_xps_app.create_blank_panel('v')
            newport_xps_app.create_form_panel(
                less_layout, d,  dropdown=dropdown, include=less_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in [*[f'ax{axis}_position' for axis in available_axis], 'customized_location']})
            command_list, modified_cmd_name, cmd_parameters = [], [], []
            command_with_axis_parameters = [
                'move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero']
            newport_xps_app.add_command(
                less_layout, d, command_list=['stop'])
            more_panel, more_layout = newport_xps_app.create_blank_panel('v')
            newport_xps_app.create_form_panel(
                more_layout, d,  dropdown=dropdown, include=more_list, withButtons=False)

            for idx, axis in enumerate(available_axis):
                if f'ax{axis}_step' in newport_xps_app.attr_list[d]['attrs']:
                    command_list.append([])
                    modified_cmd_name.append([])
                    cmd_parameters.append([])
                    for cmd in command_with_axis_parameters:
                        command_list[-1].append(cmd)
                        modified_cmd_name[-1].append(f'ax{axis}_{cmd}')
                        cmd_parameters[-1].append([axis])

            for axis in range(len(command_list)):
                newport_xps_app.add_command(
                    more_layout, d, command_list=command_list[axis], modified_cmd_name=modified_cmd_name[axis], cmd_parameters=cmd_parameters[axis])
            newport_xps_app.add_command(
                more_layout, d, command_list=['stop'])
            newport_xps_app.gui.createPanel(more_panel, f'{d}_more')
            newport_xps_app.gui.createPanel(less_panel, f'{d}_less')

    newport_xps_app.gui.removePanel('Manual')
    newport_xps_app.gui.show()
    newport_xps_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for NewPortXPS device', device_default='test/newportxps_test', nargs_string='+', polling_default=1000)
    args = parser.parse_args()
    create_app()
