from common.GUI import GuiBase
from common.axis_order import get_axis_order
from common.TaurusGUI_Argparse import TaurusArgparse
from common.ui_config import device_name_table
from common.my_motor_widget import mymotor_read_only_item_factory
import tango


def get_device_property(device_proxy, property_name, default: object = ''):
    try:
        values = device_proxy.get_property(
            property_name).get(property_name, [])
    except Exception:
        return default
    return values[0] if values else default


def get_boolean_device_property(device_proxy, property_name, default=False):
    value = get_device_property(device_proxy, property_name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    esp_app = GuiBase(device_list, args.polling)

    # get the configuration
    for d in device_list:
        esp_app.add_device(d)
        device_proxy = tango.DeviceProxy(d)
        if device_proxy.info().dev_class == 'ESP301':
            is_grating = get_boolean_device_property(
                device_proxy, 'use_grating_config')
            axis_order = get_axis_order(
                device_proxy, esp_app.attr_list[d]['attrs'])
            less_list = [
                attribute_name for axis in axis_order
                for attribute_name in (f'ax{axis}_position', f'set_ax{axis}_as')
            ] + ['user_defined_name', 'error_message', 'message', 'customized_location']
            if is_grating:
                less_list.append('ax12_distance')
            more_list = ['host_computer', 'raw_command', 'status', 'state']
            main_panel, main_layout = esp_app.create_blank_panel('v')
            esp_app.create_form_panel(
                main_layout, d, include=less_list + more_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in ['ax1_position', 'ax2_position', 'ax3_position', 'ax12_distance', 'customized_location']})
            minimum_panel = None
            if is_grating:
                minimum_panel, minimum_layout = esp_app.create_blank_panel('v')
                minimum_list = [attr for attr in less_list
                                if not attr.startswith('set_ax')]
                esp_app.create_form_panel(
                    minimum_layout, d, include=minimum_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in ['ax1_position', 'ax2_position', 'ax3_position', 'ax12_distance', 'customized_location']}, item_factories=[mymotor_read_only_item_factory, ".*"])
                esp_app.add_command(
                    minimum_layout, d, command_list=['Init', 'stop'])
            command_list, modified_cmd_name, cmd_parameters = [], [], []
            command_with_axis_parameters = [
                'move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero']
            esp_app.add_command(
                main_layout, d, command_list=['Init', 'stop'])

            for idx, axis in enumerate(axis_order):
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
                    main_layout, d, command_list=command_list[axis], modified_cmd_name=modified_cmd_name[axis], cmd_parameters=cmd_parameters[axis])
            if 'turning_box3' in d:
                esp_app.add_command(
                    main_layout, d, command_list=['reset_to_TA1'])
            esp_app.gui.createPanel(main_panel, d)
            if minimum_panel is not None:
                esp_app.gui.createPanel(minimum_panel, f'{d}_minimum')

    esp_app.gui.removePanel('Manual')
    esp_app.gui.show()
    esp_app.tile_device_panels()
    esp_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for ESP device', device_default='test/esp301/esp302_test', nargs_string='+', polling_default=1000)
    args = parser.parse_args()
    create_app()
