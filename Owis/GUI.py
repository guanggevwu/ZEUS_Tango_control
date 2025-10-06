from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox, TaurusValueLineEdit
from taurus.qt.qtgui.compact import TaurusReadWriteSwitcher
from taurus.qt.qtgui.display import TaurusLabel

import os
import sys
from taurus.qt.qtgui.button import TaurusCommandButton

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from common.config import device_name_table, image_panel_config
    from common.TaurusGUI_Argparse import TaurusArgparse
    from Basler.GUI import BaslerGUI, create_app


def create_app():
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    basler_app = BaslerGUI(device_list, args.polling)

    # get the configuration
    for d in device_list:
        basler_app.add_device(d)
        dropdown = {}
        dropdown['current_location'] = (
            (locations, locations.split(':')[0]) for locations in basler_app.attr_list[d]['dp'].user_defined_locations)
        layout = basler_app.create_form_panel(d, dropdown=dropdown, exclude=[
                                              'ax1_step', 'ax2_step', 'ax3_step', 'ax4_step', 'ax5_step', 'ax6_step', 'ax7_step', 'ax8_step', 'ax9_step'], withButtons=False)
        for a in range(1, 10):
            if f'ax{a}_step' in basler_app.attr_list[d]['attrs']:
                relative_panel, relative_panel_layout = basler_app.create_blank_panel(
                    VorH='h')
                step_widget = TaurusReadWriteSwitcher()
                r_widget = TaurusLabel()
                w_widget = TaurusValueLineEdit()

                step_widget.setReadWidget(r_widget)
                step_widget.setWriteWidget(w_widget)
                step_widget.model = f'{d}/ax{a}_step'

                button1 = TaurusCommandButton(
                    command=f'move_relative_axis{a}', parameters=[False]
                )
                button1.setCustomText(f'ax{a}-')
                button1.setModel(d)
                button2 = TaurusCommandButton(
                    command=f'move_relative_axis{a}', parameters=[True]
                )
                button2.setCustomText(f'ax{a}+')
                button2.setModel(d)

                relative_panel_layout.addWidget(button1)
                relative_panel_layout.addWidget(step_widget)
                relative_panel_layout.addWidget(button2)
                layout.addWidget(relative_panel)

        cmd_list = [
            i.cmd_name for i in basler_app.attr_list[d]['dp'].command_list_query()[3:]]
        cmd_list = [i for i in cmd_list if 'move_relative' not in i]
        filtered_cmd_list = []
        # these type of commands need to be filtered out if they are not applicable. For example, if axis 2 doesn't exist, then all corresponding commands should not exist.
        filter_list = ['init_ax', 'free_switch_ax', 'go_ref_ax']
        for i in cmd_list:
            if all([t not in i for t in filter_list]):
                filtered_cmd_list.append(i)
            elif (hasattr(basler_app.attr_list[d]['dp'], f'ax{i[-1]}_position')):
                filtered_cmd_list.append(i)
        # commands_per_row equals to the number of axis
        commands_per_row = len(filtered_cmd_list) // len(filter_list)
        if commands_per_row < 2:
            commands_per_row = 2
        for i in range(len(filtered_cmd_list) // commands_per_row+1):
            if i != len(filtered_cmd_list):
                basler_app.add_command(
                    layout, d, command_list=filtered_cmd_list[i*commands_per_row:(i+1)*commands_per_row])
            else:
                basler_app.add_command(
                    layout, d, command_list=filtered_cmd_list[i*commands_per_row:])

    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for Owis PS 90', device_default='test/owisps/test', polling_default=500)
    args = parser.parse_args()
    create_app()
