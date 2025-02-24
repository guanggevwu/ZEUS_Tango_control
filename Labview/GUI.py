from taurus_pyqtgraph import TaurusPlot
import os
import sys
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
        basler_app.create_form_panel(d)

    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description='GUI for Labview programe', device_default='laser/labview/labview_programe', polling_default=1000)
    args = parser.parse_args()
    create_app()
