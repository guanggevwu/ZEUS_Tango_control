import tango
import os

from common.ui_config import device_name_table, image_panel_config
from common.TaurusGUI_Argparse import TaurusArgparse
from common.GUI import GuiBase


def get_axis_order(device):
    properties = device.get_property(['axis', 'axis_order'])
    axis_text = ','.join(properties.get('axis', [])).strip() or '1'
    order_text = ','.join(properties.get('axis_order', [])).strip()
    try:
        axes = [int(value.strip()) for value in axis_text.split(',')]
        order = [int(value.strip()) for value in order_text.split(
            ',')] if order_text else sorted(axes)
    except ValueError as exc:
        raise ValueError(
            'axis and axis_order must be comma-separated axis numbers') from exc
    if len(order) != len(set(order)) or set(order) != set(axes):
        raise ValueError(
            'axis_order must contain every configured axis exactly once')
    return order


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    owis_app = GuiBase(device_list, args.polling)

    # get the configuration
    for d in device_list:
        owis_app.add_device(d)
        if tango.DeviceProxy(d).info().dev_class == 'OwisPS':
            axis_order = get_axis_order(owis_app.attr_list[d]['dp'])
            less_list = ['user_defined_name'] + [
                attribute_name for axis in axis_order
                for attribute_name in (f'ax{axis}_position', f'set_ax{axis}_as')
            ]
            more_list = ['host_computer', 'status', 'state']
            form_panel, form_layout = owis_app.create_blank_panel('v')
            owis_app.gui.createPanel(form_panel, f'{d}_form')
            exclude_list = [f'ax{i}_step' for i in range(
                1, 10)] + [f'set_ax{i}_as' for i in range(1, 10)]
            owis_app.create_form_panel(
                form_layout, d, include=less_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in [f'ax{ax}_position' for ax in range(1, 10)]})
            owis_app.add_command(
                form_layout, d, command_list=['stop_all_axis'])

            command_panel, command_layout = owis_app.create_blank_panel('v')
            owis_app.gui.createPanel(command_panel, f'{d}_commands')

            for ax in axis_order:
                if not hasattr(owis_app.attr_list[d]['dp'], f'ax{ax}_position'):
                    continue
                else:
                    owis_app.add_command(command_layout, d, command_list=['init_ax', 'go_ref_ax', 'free_switch_ax'], cmd_parameters=[
                        [ax], [ax], [ax]], modified_cmd_name=[f'init_ax{ax}', f'go_ref_ax{ax}', f'free_switch_ax{ax}'])
            owis_app.add_command(
                command_layout, d, command_list=['stop_all_axis'])
    owis_app.gui.helpManualURI = os.path.join(os.path.dirname(
        __file__), 'README.html')
    owis_app.gui.onShowManual()
    owis_app.gui.show()
    owis_app.tile_device_panels()
    owis_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for Owis PS 90', device_default='test/owisps/test', polling_default=500)
    args = parser.parse_args()
    create_app()
