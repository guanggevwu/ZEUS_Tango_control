import os
import sys
from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.extra_guiqwt import TaurusImageDialog
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox, TaurusValueLineEdit
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.display import TaurusLabel
from taurus_pyqtgraph import TaurusPlot
from taurus import tauruscustomsettings
import platform
import tango
if platform.system() == 'Windows':
    tauruscustomsettings.ORGANIZATION_LOGO = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'common', 'img', 'zeus.png')

if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class
    from common.TaurusGUI_Argparse import TaurusArgparse
    from common.config import device_name_table, image_panel_config


class BaslerGUI():
    def __init__(self, device_list, polling, is_form_compact=False):
        changeDefaultPollingPeriod(polling)
        if len(device_list) > 1:
            device_list_sorted = sorted(
                [i.split('/')[-1] for i in device_list])
            app_name = '&'.join(device_list_sorted)
        else:
            app_name = device_list[0].replace('/', '_')
        self.is_form_compact = is_form_compact
        self.app = TaurusApplication(cmd_line_parser=None,
                                     app_name=app_name)
        self.gui = TaurusGui()
        self.attr_list = {}

    def add_device(self, device_name):
        # this is important to exclude "is_new_image" attribute because we don't want client side periodically polling it.
        # a dictionary containing the device info is stored in self.attr_list[device_name]
        exclude = ['is_new_image']
        device_info = {}
        device_info['dp'] = Device(device_name)
        device_info['attrs'] = device_info['dp'].get_attribute_list()
        device_info['commands'] = device_info['dp'].get_command_list()
        device_info['model'] = [device_name] + [device_name + '/' +
                                                attr for attr in device_info['attrs'] if attr not in exclude]
        self.attr_list[device_name] = device_info

    def create_image_panel(self, layout, device_name, image='image', image_number=True, energy_meter=False, calibration=False):
        '''create Taurus Image panel'''
        panel1_shot = Qt.QWidget()
        panel1_shot_layout = Qt.QHBoxLayout()
        panel1_shot.setLayout(panel1_shot_layout)
        if image_number:
            if 'basler' in device_name:
                self.add_label_widget(
                    panel1_shot_layout, device_name, 'image_number')
            elif 'file_reader' in device_name:
                self.add_label_widget(
                    panel1_shot_layout, device_name, 'file_number')
        if calibration:
            self.add_label_widget(
                panel1_shot_layout, device_name, 'energy')
            self.add_label_widget(
                panel1_shot_layout, device_name, 'hot_spot')
        if energy_meter:
            self.add_label_widget(
                panel1_shot_layout, 'laser/gentec/Onshot', 'shot')
            self.add_label_widget(
                panel1_shot_layout, 'laser/gentec/Onshot', 'main_value')
        layout.addWidget(panel1_shot)

        # sets of widgets. Image in mid.
        # Check file_reader data dimension to determine use image or plot.
        if 'file_reader' in device_name and self.attr_list[device_name]['dp'].data_type == "xy":
            panel1_w1 = TaurusPlot()
            model = [(f'{device_name}/x', f'{device_name}/y')]
            panel1_w1.setModel(model)
        else:
            panel1_w1 = TaurusImageDialog()
            panel1_w1.model = device_name + '/' + image
        layout.addWidget(panel1_w1)

    def add_label_widget(self, layout, device_name, attr_name,  check_exist=False):
        # if check_exist:
        #     try:
        #         Device(device_name).ping()
        #     except:
        #         return
        if "eval" not in attr_name:
            attr_name = device_name+'/' + attr_name
        panel, panel_layout = self.create_blank_panel('h')
        panel_widget = []
        panel_widget.append(TaurusLabel())
        panel_widget.append(TaurusLabel())
        panel_widget[0].model, panel_widget[0].bgRole = f'{attr_name}#label', ''
        if ("eval" not in attr_name and self.attr_list[device_name]['dp'].get_attribute_config(attr_name.split('/')[-1]).unit):
            panel_widget[1].model = attr_name + '#rvalue'
        else:
            panel_widget[1].model = attr_name
        panel_layout.addWidget(panel_widget[0])
        panel_layout.addWidget(panel_widget[1])
        if "eval" not in attr_name and self.attr_list[device_name]['dp'].get_attribute_config(attr_name.split('/')[-1]).writable_attr_name != 'None':
            panel_widget.append(TaurusValueLineEdit())
            panel_widget[-1].model = attr_name + '#wvalue.magnitude'
            panel_layout.addWidget(panel_widget[-1])
        if any(a in attr_name for a in ["energy", "hot_spot"]):
            for i in panel_widget:
                i.setFont(Qt.QFont("Sans Serif", 16))
        layout.addWidget(panel)

    def add_command(self, layout, device_name, command_list=None, modified_cmd_name=None, cmd_parameters=None):
        '''add command buttons
        layout: the layout to add the command buttons
        device_name: the device name
        command_list: list of command names to add. If None, all commands will be added
        cmd_parameters: dictionary of command parameters. If None, no parameters will be passed.
        '''
        panel, panel_layout = self.create_blank_panel('h')
        if command_list is None:
            command_list = [
                i.cmd_name for i in self.attr_list[device_name]['dp'].command_list_query()[3:]]
        if cmd_parameters is None:
            cmd_parameters = [None]*len(command_list)
        if modified_cmd_name is None:
            modified_cmd_name = command_list
        for cmd, parameters, modified_name in zip(command_list, cmd_parameters, modified_cmd_name):
            if cmd in self.attr_list[device_name]['commands']:
                panel_w = TaurusCommandButton(
                    command=cmd, parameters=parameters
                )

                panel_w.setCustomText(modified_name)
                panel_w.setModel(device_name)
                panel_layout.addWidget(panel_w)
        layout.addWidget(panel)

    def create_form_panel(self, layout, device_name, exclude=None, dropdown=None, withButtons=True):
        panel2_w1 = TaurusForm(withButtons=withButtons)
        form_model = self.attr_list[device_name]['model']
        # re-order. Move trigger to front.
        re_order_list = {'trigger_source': 12, 'filter_option': 4}
        for key, value in re_order_list.items():
            if device_name+'/'+key in form_model:
                form_model.remove(device_name+'/'+key)
                form_model.insert(value, device_name+'/'+key)
        if exclude is not None:
            form_model = [i for i in form_model if i.split(
                '/')[-1] not in exclude]
        panel2_w1.model = form_model
        layout.addWidget(panel2_w1)
        if not dropdown:
            # change the text write widget to dropdown list and set auto apply
            dropdown = {'trigger_source': (('Off', 'Off'), ('Software', 'Software'), ('External', 'External')), 'trigger_selector': (
                ('AcquisitionStart', 'AcquisitionStart'), ('FrameStart', 'FrameStart')), }
        for idx, full_attr in enumerate(form_model):
            # change the bool write to auto apply. Only apply to writable bool widget.
            if full_attr.split('/')[-1] in self.attr_list[device_name]['attrs'] and self.attr_list[device_name]['dp'].attribute_query(full_attr.split('/')[-1]).data_type == 1 and self.attr_list[device_name]['dp'].attribute_query(full_attr.split('/')[-1]).writable == tango._tango.AttrWriteType.READ_WRITE:
                idx = form_model.index(full_attr)
                panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox
            if full_attr.split('/')[-1] in dropdown:
                panel2_w1[idx].writeWidgetClass = create_my_dropdown_list_class(
                    full_attr.split('/')[-1], dropdown[full_attr.split('/')[-1]])

    def combined_panel(self, device_list, combine_form_with_onshot=False):
        panel3, panel3_layout = self.create_blank_panel('v')
        if combine_form_with_onshot:
            self.add_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'name_attr', check_exist=True)
            self.add_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'shot', check_exist=True)
            self.add_label_widget(
                panel3_layout, 'laser/gentec/Onshot', 'main_value', check_exist=True)
        for d in device_list:
            widget_one_device = Qt.QWidget()
            widget_one_device_layout = Qt.QHBoxLayout()
            widget_one_device.setLayout(widget_one_device_layout)
            self.add_label_widget(
                widget_one_device_layout, d, 'user_defined_name')
            # because Basler uses 'image_number' and FileReader uses 'file_number'.
            if 'basler' in d:
                self.add_label_widget(
                    widget_one_device_layout, d, 'image_number')
            elif 'file_reader' in d:
                self.add_label_widget(
                    widget_one_device_layout, d, 'file_number')
            panel3_layout.addWidget(widget_one_device)
            self.add_command(panel3_layout, d, command_list=[
                             'get_ready', 'relax', 'reset_number', 'send_software_trigger'],  cmd_parameters=[None, None, [0], None])
        self.gui.createPanel(panel3, f'{len(device_list)} devices')

    def create_blank_panel(self, VorH='V'):
        panel = Qt.QWidget()
        if VorH.lower() == "v":
            panel_layout = Qt.QVBoxLayout()
        else:
            panel_layout = Qt.QHBoxLayout()
        panel.setLayout(panel_layout)
        return panel, panel_layout


def create_app():
    parser = TaurusArgparse(
        description='GUI for Basler camera', device_default='test/basler/test', nargs_string='+', polling_default=1500)
    args = parser.parse_args()

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
        else:
            pass_config1, pass_config2 = {}, {}
        basler_app.add_device(d)

        # image panel.
        image_panel, image_layout = basler_app.create_blank_panel('v')
        basler_app.gui.createPanel(image_panel, f'{d}_image_plot')
        basler_app.create_image_panel(image_layout, d, **pass_config1)
        if not len(args.device) > 3:
            basler_app.add_command(image_layout, d, command_list=[
                                   'get_ready', 'relax', 'reset_number', 'send_software_trigger'], cmd_parameters=[None, None, [0], None])
        # form panel
        form_panel, form_layout = basler_app.create_blank_panel('v')
        basler_app.gui.createPanel(form_panel, f'{d}_form')
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
    basler_app.gui.removePanel('Manual')
    basler_app.gui.show()
    basler_app.app.exec_()


if __name__ == "__main__":
    create_app()
