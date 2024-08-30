

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from common.config import device_name_table, image_panel_config
    from common.TaurusGUI_Argparse import TaurusArgparse
    from Basler.GUI import BaslerGUI
parser = TaurusArgparse(
    description='GUI for Basler camera', device_default='test/basler/testcam', polling_default=1000)
parser.add_argument('-s', '--simple', action='store_true',
                    help="show image without shot number and command")
args = parser.parse_args()

if __name__ == "__main__":
    basler_app = BaslerGUI(args.device, args.polling)
    # get the device list
    if 'combination' in args.device:
        device_list = device_name_table[args.device]
    else:
        device_list = [args.device]
    # get the configuration
    pass_config1, pass_config2 = {}, {}
    if args.device in image_panel_config:
        pass_config1 = {key: value for key, value in image_panel_config[args.device].items(
        ) if key != "combine_form_with_onshot"}
        pass_config2 = {key: value for key, value in image_panel_config[args.device].items(
        ) if key == "combine_form_with_onshot"}
    for d in device_list:
        basler_app.add_device(d)
        basler_app.create_image_panel(d, **pass_config1)
        basler_app.create_form_panel(d)
    if 'combination' in args.device:
        basler_app.combined_panel(device_list, **pass_config2)
    basler_app.gui.show()
    basler_app.app.exec_()
