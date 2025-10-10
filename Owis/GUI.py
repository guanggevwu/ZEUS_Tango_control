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
        form_panel, form_layout = basler_app.create_blank_panel('v')
        basler_app.gui.createPanel(form_panel, f'{d}_form')
        basler_app.create_form_panel(form_layout, d, dropdown=dropdown, exclude=[
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
                    command=f'move_relative_axis{a}', parameters=[a, 0]
                )
                button1.setCustomText(f'ax{a}-')
                button1.setModel(d)
                button2 = TaurusCommandButton(
                    command=f'move_relative_axis{a}', parameters=[a, 1]
                )
                button2.setCustomText(f'ax{a}+')
                button2.setModel(d)

                relative_panel_layout.addWidget(button1)
                relative_panel_layout.addWidget(step_widget)
                relative_panel_layout.addWidget(button2)
                form_layout.addWidget(relative_panel)

        basler_app.add_command(form_layout, d, command_list=['stop_all_axis'])
        for ax in range(1, 10):
            if not hasattr(basler_app.attr_list[d]['dp'], f'ax{ax}_position'):
                continue
            else:
                basler_app.add_command(form_layout, d, command_list=['init_ax', 'go_ref_ax', 'free_switch_ax'], cmd_parameters=[
                                       [ax], [ax], [ax]], modified_cmd_name=[f'init_ax{ax}', f'go_ref_ax{ax}', f'free_switch_ax{ax}'])

    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for Owis PS 90', device_default='test/owisps/test', polling_default=500)
    args = parser.parse_args()
    create_app()
