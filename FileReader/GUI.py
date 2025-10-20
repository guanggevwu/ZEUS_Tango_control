from taurus_pyqtgraph import TaurusPlot
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from common.config import device_name_table, image_panel_config
    from common.TaurusGUI_Argparse import TaurusArgparse
    from Basler.GUI import BaslerGUI, create_app
parser = TaurusArgparse(
    description='GUI for File Reader', device_default='test/basler/testcam', nargs_string='+', polling_default=1000)
parser.add_argument('-s', '--simple', action='store_true',
                    help="show image without shot number and command")
args = parser.parse_args()

if __name__ == "__main__":
    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    file_reader_app = BaslerGUI(device_list, args.polling)

    # get the configuration
    for d in device_list:
        pass_config1 = {}
        if d in image_panel_config:
            pass_config1 = ({key: value for key, value in image_panel_config[d].items(
            ) if key != "combine_form_with_onshot"})
        elif len(args.device) > 3:
            pass_config1['image_number'] = False
        else:
            pass_config1, pass_config2 = {}, {}
        file_reader_app.add_device(d)

        # image panel.
        image_panel, image_layout = file_reader_app.create_blank_panel('v')
        file_reader_app.gui.createPanel(image_panel, f'{d}_image_plot')
        file_reader_app.create_image_panel(image_layout, d, **pass_config1)
        if not len(args.device) > 3:
            file_reader_app.add_command(image_layout, d, command_list=[
                'reset_number', 'read_files'], cmd_parameters=[[0], None])
        # form panel
        form_panel, form_layout = file_reader_app.create_blank_panel('v')
        file_reader_app.gui.createPanel(form_panel, f'{d}_form')
        file_reader_app.create_form_panel(form_layout, d)

    file_reader_app.gui.removePanel('Manual')
    file_reader_app.gui.show()
    file_reader_app.app.exec_()
