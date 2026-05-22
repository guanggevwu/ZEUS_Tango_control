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
    from Basler.GUI import BaslerGUI, create_app
    from common.taurus_widget import RelativeMotion


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    owis_app = BaslerGUI(device_list, args.polling)

    # get the configuration
    for d in device_list:
        owis_app.add_device(d)
        if tango.DeviceProxy(d).info().dev_class == 'OwisPS':
            less_list = ['user_defined_name', 'current_location', 'ax1_position', 'set_ax1_as', 'ax2_position', 'set_ax2_as', 'ax3_position',
                         'set_ax3_as', 'ax4_position', 'set_ax4_as', 'ax5_position', 'set_ax5_as', 'ax6_position', 'set_ax6_as', 'ax7_position', 'set_ax7_as', 'ax8_position', 'set_ax8_as', 'ax9_position', 'set_ax9_as']
            more_list = ['host_computer', 'saved_location_source',
                         'user_defined_locations', 'status', 'state']
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
                (locations, locations.split(':')[0]) for locations in owis_app.attr_list[d]['dp'].user_defined_locations)
            dropdown['saved_location_source'] = (
                ('server', 'server'),  ('client', 'client'))
            form_panel, form_layout = owis_app.create_blank_panel('v')
            owis_app.gui.createPanel(form_panel, f'{d}_form')
            exclude_list = [f'ax{i}_step' for i in range(
                1, 10)] + [f'set_ax{i}_as' for i in range(1, 10)]
            owis_app.create_form_panel(
                form_layout, d,  dropdown=dropdown, include=less_list, withButtons=False, set_attr_font={key: {'font': '"Sans Serif"', 'size': 20} for key in [f'ax{ax}_position' for ax in range(1, 10)]})
            owis_app.add_command(
                form_layout, d, command_list=['stop_all_axis'])

            command_panel, command_layout = owis_app.create_blank_panel('v')
            owis_app.gui.createPanel(command_panel, f'{d}_commands')

            for ax in range(1, 10):
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
    owis_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for Owis PS 90', device_default='test/owisps/test', polling_default=500)
    args = parser.parse_args()
    create_app()
