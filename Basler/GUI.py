import os
from common.TaurusGUI_Argparse import TaurusArgparse
from common.config import device_name_table, image_panel_config
from common.GUI import GuiBase


def create_app():
    parser = TaurusArgparse(
        description='GUI for Basler camera', device_default='test/basler/test', nargs_string='+', polling_default=3000)
    args = parser.parse_args()

    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    basler_app = GuiBase(device_list, args.polling)
    # check Basler camera friendly name
    if any(['basler' in d for d in device_list]):
        from pypylon import pylon
        serial_number_vs_friendly_name = dict()
        for device in pylon.TlFactory.GetInstance().EnumerateDevices():
            serial_number_vs_friendly_name[device.GetSerialNumber(
            )] = device.GetUserDefinedName()
    else:
        serial_number_vs_friendly_name = None
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
        basler_app.add_device(d)

        # image panel.
        image_panel, image_layout = basler_app.create_blank_panel('v')
        if serial_number_vs_friendly_name and d.split('/')[-1].split('_')[-1] in serial_number_vs_friendly_name:
            friendly_name = serial_number_vs_friendly_name[d.split(
                '/')[-1].split('_')[-1]]
        else:
            friendly_name = d
        basler_app.gui.createPanel(image_panel, f'{friendly_name}')
        basler_app.create_image_panel(image_layout, d, **pass_config1)
        if not len(args.device) > 3:
            basler_app.add_command(image_layout, d, command_list=[
                                   'get_ready', 'relax', 'reset_number', 'send_software_trigger', 'clear_queue'], cmd_parameters=[None, None, [0], None, None])
        # form panel
        form_panel, form_layout = basler_app.create_blank_panel('v')
        basler_app.gui.createPanel(form_panel, f'{friendly_name}_form')
        basler_app.create_form_panel(form_layout,
                                     d, exclude=['image', 'image_r', 'image_g', 'image_b', 'flux', 'energy', 'hot_spot'])
    if len(args.device) == 1 and args.device[0] in image_panel_config:
        pass_config2 = ({key: value for key, value in image_panel_config[args.device[0]].items(
        ) if key == "combine_form_with_onshot"})
    elif len(args.device) > 3:
        pass_config2 = {"combine_form_with_onshot": False}
    else:
        pass_config2 = {}
    if 'combination' in args.device[0] or len(args.device) > 1:
        basler_app.combined_panel(device_list, **pass_config2)
    if len(device_list) > 1:
        basler_app.gui.helpManualURI = os.path.join(os.path.dirname(os.path.dirname(
            __file__)), 'DAQ', 'README.html')
    else:
        basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    create_app()
