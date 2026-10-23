import os
from common.ui_config import device_name_table, image_panel_config
from common.TaurusGUI_Argparse import TaurusArgparse
from common.GUI import GuiBase


def create_app():
    parser = TaurusArgparse(
        description='GUI for Vimba camera', device_default='TA2/vimba/TA2-1', nargs_string='*', polling_default=200)
    parser.add_argument('-s', '--simple', action='store_true',
                        help="show image without shot number and command")
    args = parser.parse_args()
    # Normalize defaults as well as explicit arguments before indexing/counting.
    if isinstance(args.device, str):
        args.device = [args.device]

    if 'combination' in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]
    vimba_app = GuiBase(device_list, args.polling)
    # get the configuration
    image_panel_names = []
    stacked_panel_names = []
    for d in device_list:
        pass_config1 = {}
        if d in image_panel_config:
            pass_config1 = ({key: value for key, value in image_panel_config[d].items(
            ) if key != "combine_form_with_onshot"})
        elif len(device_list) > 3:
            pass_config1['image_number'] = False
        else:
            pass_config1, pass_config2 = {}, {}
        vimba_app.add_device(d)

        # image panel.
        image_panel, image_layout = vimba_app.create_blank_panel('v')
        vimba_app.gui.createPanel(image_panel, f'{d}')
        image_panel_names.append(d)
        vimba_app.create_image_panel(image_layout, d, **pass_config1)
        if len(device_list) <= 3:
            vimba_app.add_command(image_layout, d, command_list=[
                'get_ready', 'relax', 'reset_number', 'send_software_trigger',
                'clear_queue', 'adjust_packet_size'],
                cmd_parameters=[None, None, [0], None, None, None])
        # form panel
        form_panel, form_layout = vimba_app.create_blank_panel('v')
        vimba_app.gui.createPanel(form_panel, f'{d}_form')
        stacked_panel_names.append(f'{d}_form')
        vimba_app.create_form_panel(form_layout,
                                    d, exclude=['image', 'image_r', 'image_g', 'image_b', 'flux', 'energy', 'hot_spot'])
    if len(args.device) == 1 and args.device[0] in image_panel_config:
        pass_config2 = ({key: value for key, value in image_panel_config[args.device[0]].items(
        ) if key == "combine_form_with_onshot"})
    elif len(device_list) > 3:
        pass_config2 = {"combine_form_with_onshot": False}
    else:
        pass_config2 = {}
    if len(device_list) > 1:
        vimba_app.combined_panel(device_list, **pass_config2)
        stacked_panel_names.append(f'{len(device_list)} devices')
    if len(device_list) > 1:
        vimba_app.gui.helpManualURI = os.path.join(os.path.dirname(os.path.dirname(
            __file__)), 'DAQ', 'README.html')
        stacked_panel_names.append('Manual')
    else:
        vimba_app.gui.removePanel('Manual')
    if len(device_list) > 1:
        vimba_app.tile_panels_with_stacked_panels(
            image_panel_names, stacked_panel_names)
    vimba_app.gui.show()
    vimba_app.app.exec_()


if __name__ == "__main__":
    create_app()
