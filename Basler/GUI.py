from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.extra_guiqwt import TaurusImageDialog
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.display import TaurusLabel
import sys
import json
import os
import tango
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class
    from common.TaurusGUI_Argparse import TaurusArgparse

parser = TaurusArgparse(
    description='GUI for Basler camera', device_default='test/basler/1', polling_default=1000)
parser.add_argument('-s', '--simple', action='store_true',
                    help="show image without shot number and command")
args = parser.parse_args()
# device_name = args.device
# changeDefaultPollingPeriod(args.polling)
# is_form_compact = args.compact


class BaslerGUI():
    def __init__(self, device_name, polling, is_form_compact=False):
        changeDefaultPollingPeriod(polling)

        self.is_form_compact = is_form_compact
        self.app = TaurusApplication(cmd_line_parser=None,
                                app_name=device_name.replace('/', '_'))
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
            self.add_readonly_label_widget(panel1_shot_layout, device_name, 'image_number')
        if calibration:
            self.add_readonly_label_widget(panel1_shot_layout, device_name, 'energy')
            self.add_readonly_label_widget(panel1_shot_layout, device_name, 'hot_spot')
        if energy_meter:
            self.add_readonly_label_widget(panel1_shot_layout, 'laser/gentec/Onshot', 'shot')
            self.add_readonly_label_widget(panel1_shot_layout, 'laser/gentec/Onshot', 'main_value')
        panel1_layout.addWidget(panel1_shot)

        # sets of widgets. Image in mid.
        panel1_w1 = TaurusImageDialog()
        panel1_w1.model = device_name + '/' + image
        panel1_layout.addWidget(panel1_w1)
        if command:
            self.add_command(panel1_layout, device_name, ['get_ready', 'relax', 'send_software_trigger', 'reset_number'])

        self.gui.createPanel(panel1, f'{device_name}_{image}')

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

    def add_command(self, layout, device_name, command_list):
        panel = Qt.QWidget()
        panel_layout = Qt.QHBoxLayout()
        panel.setLayout(panel_layout)
        command_list = ['get_ready', 'relax', 'send_software_trigger', 'reset_number']

        for cmd in command_list:
            if cmd in self.attr_list[device_name]['commands']:
                panel_w = TaurusCommandButton(
                    command=cmd
                )
                panel_w.setCustomText(cmd)
                panel_w.setModel(device_name)
                panel_layout.addWidget(panel_w)
        layout.addWidget(panel)        
    # def add_energy_shot_num_value_widget(self, layout, device_name):
    #     if hasattr(Device(device_name), 'get_attribute_list'):
    #         panel1_gentec_shot_w1, panel1_gentec_shot_w2, panel1_gentec_shot_w3, panel1_gentec_shot_w4 = TaurusLabel(
    #         ), TaurusLabel(), TaurusLabel(), TaurusLabel()
    #         panel1_gentec_shot_w2.model = device_name + '/' + 'shot'

    #         panel1_gentec_shot_w1.model, panel1_gentec_shot_w1.bgRole = device_name + \
    #             '/' + 'shot#label', ''
    #         panel1_gentec_shot_w3.model = device_name + '/' + 'main_value'

    #         panel1_gentec_shot_w1.model, panel1_gentec_shot_w1.bgRole = device_name + \
    #             '/' + 'main_value#label', ''
    #         layout.addWidget(panel1_gentec_shot_w1)
    #         layout.addWidget(panel1_gentec_shot_w2)
    #         layout.addWidget(panel1_gentec_shot_w3)
    #         layout.addWidget(panel1_gentec_shot_w4)        
        
    def create_form_panel(self, device_name, exclude=['image', 'flux','energy', 'hot_spot']):

        panel2 = Qt.QWidget()
        panel2_layout = Qt.QVBoxLayout()
        panel2.setLayout(panel2_layout)


        panel2_w1 = TaurusForm()
        form_model = self.attr_list[device_name]['model']
        form_model =[i for i in form_model if i.split('/')[-1] not in exclude]
        form_model.remove(f'{device_name}/exposure')
        form_model.remove(f'{device_name}/gain')
        trigger_selector_idx = form_model.index(f'{device_name}/trigger_selector')
        form_model.insert(trigger_selector_idx+1, f'{device_name}/exposure')
        form_model.insert(trigger_selector_idx+2, f'{device_name}/gain')
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


    def combined_panel(self, device_list):
        panel3 = Qt.QWidget()
        panel3_layout = Qt.QVBoxLayout()
        panel3.setLayout(panel3_layout)
        self.add_readonly_label_widget(panel3_layout, 'laser/gentec/Onshot', 'name_attr', check_exist=True)
        self.add_readonly_label_widget(panel3_layout, 'laser/gentec/Onshot', 'shot', check_exist=True)
        self.add_readonly_label_widget(panel3_layout, 'laser/gentec/Onshot', 'main_value', check_exist=True)
        for d in device_list:
            self.add_readonly_label_widget(panel3_layout, d, 'user_defined_name')
            self.add_readonly_label_widget(panel3_layout, d, 'image_number')
            self.add_command(panel3_layout, d, ['get_ready', 'relax', 'send_software_trigger', 'reset_number'])
        self.gui.createPanel(panel3, f'{len(device_list)} devices')

if __name__ == "__main__":
    basler_app = BaslerGUI(args.device, args.polling)
    combination_table =  {'TA1_conf1_combine':['TA1/basler/TA1-Ebeam', 'TA1/basler/TA1-EspecH', 'TA1/basler/TA1-EspecL', 'TA1/basler/TA1-Shadowgraphy'], 'TA2_conf1_combine':['TA2/basler/TA2-NearField', 'TA2/basler/TA2-FarField']} 
    image_panel_config = {'combine':{"image_number": False, 'command':False}, 'laser/basler/PW_Comp_In':{'image':'flux', 'calibration': True}}

    # get the device list
    if 'combine' in args.device:
        device_list = combination_table[args.device]
    else:
        device_list = [args.device]
    # get the configuration 
    if 'combine' in args.device:
        pass_config = image_panel_config['combine']
    elif args.device in image_panel_config:
        pass_config = image_panel_config[args.device]
    else:
        pass_config = {}
    for d in device_list:
        basler_app.add_device(d)
        basler_app.create_image_panel(d, **pass_config)
        basler_app.create_form_panel(d)
    if 'combine' in args.device:
        basler_app.combined_panel(device_list)
    basler_app.gui.show()
    basler_app.app.exec_()
