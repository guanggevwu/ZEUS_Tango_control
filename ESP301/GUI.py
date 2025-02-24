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
        panel, panel1_layout = basler_app.create_blank_panel('v')
        attr_list = basler_app.attr_list[d]['attrs']
        for attr in attr_list:
            if attr not in ['ax1_position', 'ax2_position', 'ax3_position', 'ax1_step', 'ax2_step', 'ax3_step', 'State', 'Status']:
                basler_app.add_label_widget(panel1_layout, d, attr)
        basler_app.add_label_widget(
            panel1_layout, d, 'eval:{ax1_position}-{ax2_position}')
        axis_index = ['12', '1', '2', '3']
        for a in axis_index:
            if f'ax{a}_position' in attr_list:
                basler_app.add_label_widget(
                    panel1_layout, d, f'ax{a}_position')
            if f'ax{a}_step' in attr_list:
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
                button1.setCustomText('-')
                button1.setModel(d)
                button2 = TaurusCommandButton(
                    command=f'move_relative_axis{a}', parameters=[True]
                )
                button2.setCustomText('+')
                button2.setModel(d)

                relative_panel_layout.addWidget(button1)
                relative_panel_layout.addWidget(step_widget)
                relative_panel_layout.addWidget(button2)
                panel1_layout.addWidget(relative_panel)

        cmd_list = basler_app.attr_list[d]['commands']
        cmd_list = [i for i in cmd_list[3:] if 'move_relative' not in i]
        basler_app.add_command(panel1_layout, d, cmd_list)
        basler_app.gui.createPanel(panel, d)

    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for ESP301', device_default='laser/esp301/esp301', polling_default=500)
    args = parser.parse_args()
    create_app()
