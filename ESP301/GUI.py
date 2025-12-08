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
        form_panel, form_layout = basler_app.create_blank_panel('v')
        basler_app.gui.createPanel(form_panel, f'{d}_form')
        basler_app.create_form_panel(form_layout, d, exclude=[
            'ax1_step', 'ax2_step', 'ax3_step', 'ax4_step', 'ax5_step', 'ax6_step', 'ax7_step', 'ax8_step', 'ax9_step', 'ax12_step'], withButtons=False)
        command_list, modified_cmd_name, cmd_parameters = [], [], []
        command_with_axis_parameters = [
            'move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero']
        for idx, axis in enumerate([1,2,3,'12']):
            if f'ax{axis}_step' in basler_app.attr_list[d]['attrs']:
                one_relative, one_relative_layout = basler_app.create_blank_panel(
                    VorH='h')
                step_widget = TaurusReadWriteSwitcher()
                r_widget = TaurusLabel()
                w_widget = TaurusValueLineEdit()

                step_widget.setReadWidget(r_widget)
                step_widget.setWriteWidget(w_widget)
                step_widget.model = f'{d}/ax{axis}_step'
                if axis == "12":
                    button1 = TaurusCommandButton(
                        command='move_relative_axis12', parameters=[0]
                    )
                    button2 = TaurusCommandButton(
                        command='move_relative_axis12', parameters=[1]
                    )
                else:
                    button1 = TaurusCommandButton(
                        command='move_relative_axis', parameters=[axis, 0]
                    )
                    button2 = TaurusCommandButton(
                        command='move_relative_axis', parameters=[axis, 1]
                    )
                button1.setCustomText(f'ax{axis}-')
                button1.setModel(d)
                button2.setCustomText(f'ax{axis}+')
                button2.setModel(d)

                one_relative_layout.addWidget(button1)
                one_relative_layout.addWidget(step_widget)
                one_relative_layout.addWidget(button2)
                form_layout.addWidget(one_relative)
                if axis != "12":
                    command_list.append([])
                    modified_cmd_name.append([])
                    cmd_parameters.append([])
                    for cmd in command_with_axis_parameters:
                        command_list[-1].append(cmd)
                        modified_cmd_name[-1].append(f'ax{axis}_{cmd}')
                        cmd_parameters[-1].append([axis])
        for axis in range(len(command_list)):
            basler_app.add_command(
                form_layout, d, command_list=command_list[axis], modified_cmd_name=modified_cmd_name[axis], cmd_parameters=cmd_parameters[axis])
        basler_app.add_command(
            form_layout, d, command_list=['stop'])
        basler_app.add_command(
            form_layout, d, command_list=['reset_to_TA1'])
        # command_panel, command_layout = basler_app.create_blank_panel('v')
        # basler_app.gui.createPanel(command_panel, f'{d}_commands')

        # for ax in range(1, 4):
        #     if not hasattr(basler_app.attr_list[d]['dp'], f'ax{ax}_position'):
        #         continue
        #     else:
        #         basler_app.add_command(command_layout, d)
    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for ESP device', device_default='test/esp301/esp302_test', polling_default=1000)
    args = parser.parse_args()
    create_app()
