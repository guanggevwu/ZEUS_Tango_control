from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.extra_guiqwt import TaurusImageDialog
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.display import TaurusLabel
from taurus_pyqtgraph import TaurusPlot

import sys
import json
import os
import tango
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class
    from common.TaurusGUI_Argparse import TaurusArgparse
    from common.config import device_name_table, image_panel_config

parser = TaurusArgparse(
    description='GUI for Basler camera', device_default='test/basler/test', nargs_string='+', polling_default=1000)
# parser.add_argument('-s', '--simple', action='store_true',
#                     help="show image without shot number and command")
args = parser.parse_args()
# device_name = args.device
# changeDefaultPollingPeriod(args.polling)
# is_form_compact = args.compact


class BaslerGUI():
    def __init__(self, device_list, polling, is_form_compact=False):
        changeDefaultPollingPeriod(polling)
        if len(device_list) > 1:
            app_name = device_list[0].replace(
                '/', '_') + f'_and_{len(device_list)-1}_more'
        else:
            app_name = device_list[0].replace('/', '_')
        self.is_form_compact = is_form_compact
        self.app = TaurusApplication(cmd_line_parser=None,
                                     app_name=app_name)
        self.gui = TaurusGui()
        self.attr_list = {}

    def add_device(self, device_name):
        exclude = ['is_new_image']
        device_info = {}
        device_info['dp'] = Device(device_name)
        device_info['attrs'] = device_info['dp'].get_attribute_list()
        device_info['commands'] = device_info['dp'].get_command_list()
        device_info['model'] = [device_name] + [device_name + '/' +
                                                attr for attr in device_info['attrs'] if attr not in exclude]
        self.attr_list[device_name] = device_info

    def create_image_panel(self, device_name, image='image', image_number=True, energy_meter=False, calibration=False, command=True):
        '''create TaurusForm panel'''
        # panel 1
        panel1 = Qt.QWidget()
        panel1_layout = Qt.QVBoxLayout()
        panel1.setLayout(panel1_layout)

        panel1_shot = Qt.QWidget()
        panel1_shot_layout = Qt.QHBoxLayout()
        panel1_shot.setLayout(panel1_shot_layout)
        if image_number:
            if 'basler' in device_name:
                self.add_readonly_label_widget(
                    panel1_shot_layout, device_name, 'image_number')
            elif 'file_reader' in device_name:
                self.add_readonly_label_widget(
                    panel1_shot_layout, device_name, 'file_number')
        if calibration:
            self.add_readonly_label_widget(
                panel1_shot_layout, device_name, 'energy')
            self.add_readonly_label_widget(
                panel1_shot_layout, device_name, 'hot_spot')
        if energy_meter:
            self.add_readonly_label_widget(
                panel1_shot_layout, 'laser/gentec/Onshot', 'shot')
            self.add_readonly_label_widget(
                panel1_shot_layout, 'laser/gentec/Onshot', 'main_value')
        panel1_layout.addWidget(panel1_shot)

        # sets of widgets. Image in mid.
        # Check file_reader data dimension to determine use image or plot.
        if 'file_reader' in device_name and self.attr_list[device_name]['dp'].data_dimension == 1:
            panel1_w1 = TaurusPlot()
            model = [(f'{device_name}/x', f'{device_name}/y')]
            panel1_w1.setModel(model)
            panel1_w1_name = f'{device_name}_plot'
        else:
            panel1_w1 = TaurusImageDialog()
            panel1_w1.model = device_name + '/' + image
            panel1_w1_name = f'{device_name}_{image}'
        panel1_layout.addWidget(panel1_w1)
        if command:
            self.add_command(panel1_layout, device_name)

        self.gui.createPanel(panel1, panel1_w1_name)

    def add_readonly_label_widget(self, layout, device_name, attr_name, check_exist=False):
        # if check_exist:
        #     try:
        #         Device(device_name).ping()
        #     except:
        #         return
        panel = Qt.QWidget()
        panel_layout = Qt.QHBoxLayout()
        panel.setLayout(panel_layout)
        panel1_w1, panel1_w2 = TaurusLabel(), TaurusLabel()
        panel1_w1.model, panel1_w1.bgRole = device_name + \
            '/' + f'{attr_name}#label', ''
        panel1_w2.model = device_name + '/' + attr_name
        panel_layout.addWidget(panel1_w1)
        panel_layout.addWidget(panel1_w2)
        layout.addWidget(panel)

    def add_command(self, layout, device_name, command_list=None):
        panel = Qt.QWidget()
        panel_layout = Qt.QHBoxLayout()
        panel.setLayout(panel_layout)
        if command_list is None:
            command_list = [
                i.cmd_name for i in self.attr_list[device_name]['dp'].command_list_query()[3:]]

        for cmd in command_list:
            if cmd in self.attr_list[device_name]['commands']:
                if cmd == "reset_number":
                    panel_w = TaurusCommandButton(
                        command=cmd, parameters=[0]
                    )
                else:
                    panel_w = TaurusCommandButton(
                        command=cmd
                    )
                panel_w.setCustomText(cmd)
                panel_w.setModel(device_name)
                panel_layout.addWidget(panel_w)
        layout.addWidget(panel)

    def create_form_panel(self, device_name, exclude=['image', 'flux', 'energy', 'hot_spot']):

        panel2 = Qt.QWidget()
        panel2_layout = Qt.QVBoxLayout()
        panel2.setLayout(panel2_layout)

        panel2_w1 = TaurusForm()
        form_model = self.attr_list[device_name]['model']
        # re-order. Move trigger to front.
        re_order_list = {'trigger_source': 12, 'filter_option': 4}
        for key, value in re_order_list.items():
            form_model.remove(device_name+'/'+key)
            form_model.insert(value, device_name+'/'+key)
        if 'basler' in device_name.lower():
            form_model = [i for i in form_model if i.split(
                '/')[-1] not in exclude]
        panel2_w1.model = form_model
        panel2_layout.addWidget(panel2_w1)

        # change the text write widget to dropdown list and set auto apply
        dropdown = {'trigger_source': (('Off', 'Off'), ('Software', 'Software'), ('External', 'Line1')), 'trigger_selector': (
            ('AcquisitionStart', 'AcquisitionStart'), ('FrameStart', 'FrameStart')), }
        for idx, full_attr in enumerate(form_model):
            # change the bool write to auto apply.
            if full_attr.split('/')[-1] in self.attr_list[device_name]['attrs'] and self.attr_list[device_name]['dp'].attribute_query(full_attr.split('/')[-1]).data_type == 1:
                idx = form_model.index(full_attr)
                panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox
            if full_attr.split('/')[-1] in dropdown:
                panel2_w1[idx].writeWidgetClass = create_my_dropdown_list_class(
                    full_attr.split('/')[-1], dropdown[full_attr.split('/')[-1]])

        self.gui.createPanel(panel2, f'{device_name}_paramters')

    def combined_panel(self, device_list, combine_form_with_onshot=False):
        panel3 = Qt.QWidget()
        panel3_layout = Qt.QVBoxLayout()
        panel3.setLayout(panel3_layout)
        if combine_form_with_onshot:
            self.add_readonly_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'name_attr', check_exist=True)
            self.add_readonly_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'shot', check_exist=True)
            self.add_readonly_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'main_value', check_exist=True)
        for d in device_list:
            self.add_readonly_label_widget(
                panel3_layout, d, 'user_defined_name')
            # because Basler uses 'image_number' and FileReader uses 'file_number'.
            if 'basler' in d:
                self.add_readonly_label_widget(
                    panel3_layout, d, 'image_number')
            elif 'file_reader' in d:
                self.add_readonly_label_widget(panel3_layout, d, 'file_number')
            self.add_command(panel3_layout, d)
        self.gui.createPanel(panel3, f'{len(device_list)} devices')


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
        pass_config1 = {}
        if d in image_panel_config:
            pass_config1 = ({key: value for key, value in image_panel_config[d].items(
            ) if key != "combine_form_with_onshot"})
        elif len(args.device) > 3:
            pass_config1['image_number'] = False
            pass_config1['command'] = False
        else:
            pass_config1, pass_config2 = {}, {}
        basler_app.add_device(d)
        basler_app.create_image_panel(d, **pass_config1)
        basler_app.create_form_panel(d)
    if len(args.device) == 1 and args.device[0] in image_panel_config:
        pass_config2 = ({key: value for key, value in image_panel_config[args.device[0]].items(
        ) if key == "combine_form_with_onshot"})
    elif len(args.device) > 3:
        pass_config2 = {"combine_form_with_onshot": False}
    else:
        pass_config2 = {}
    if 'combination' in args.device[0] or len(args.device) > 1:
        basler_app.combined_panel(device_list, **pass_config2)
    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    create_app()
