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
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class

import argparse

parser = argparse.ArgumentParser(description='GUI for Gentec-EO devices')
parser.add_argument('device', default='test/gentec/1', nargs='?',
                    help="device full name")
parser.add_argument('-p', '--polling', type=int, default=3000,
                    help="polling period")
parser.add_argument('-c', '--compact', action='store_true')
args = parser.parse_args()

device_name = args.device
changeDefaultPollingPeriod(args.polling)
is_form_compact = args.compact

exclude = ['is_new_image']
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name] + [device_name + '/' +
                         attr for attr in attrs if attr not in exclude]

app = TaurusApplication(cmd_line_parser=None,
                        app_name=sys.argv[1].replace('/', '_'))
gui = TaurusGui()

panel1 = Qt.QWidget()
panel1_layout = Qt.QVBoxLayout()
panel1.setLayout(panel1_layout)

panel1_w1 = TaurusImageDialog()
panel1_w1.model = device_name + '/' + 'image'
panel1_layout.addWidget(panel1_w1)

panel1_1 = Qt.QWidget()
panel1_1_layout = Qt.QHBoxLayout()
panel1_1.setLayout(panel1_1_layout)

for cmd in commands:
    if cmd not in ['Init', 'State', 'Status']:
        panel1_1_w = TaurusCommandButton(
            command=cmd
        )
        panel1_1_w.setCustomText(cmd)
        panel1_1_w.setModel(device_name)
        panel1_1_layout.addWidget(panel1_1_w)
panel1_layout.addWidget(panel1_1)

gui.createPanel(panel1, 'image')


panel2 = Qt.QWidget()
panel2_layout = Qt.QVBoxLayout()
panel2.setLayout(panel2_layout)


panel2_w1 = TaurusForm()
form_model = [model[0]]+model[2:]
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
    if full_attr.split('/')[-1] in attrs and dp.attribute_query(full_attr.split('/')[-1]).data_type == 1:
        idx = form_model.index(full_attr)
        panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox
    if full_attr.split('/')[-1] in dropdown:
        panel2_w1[idx].writeWidgetClass = create_my_dropdown_list_class(
            full_attr.split('/')[-1], dropdown[full_attr.split('/')[-1]])

gui.createPanel(panel2, 'parameters')
gui.removePanel('Manual')

gui.show()
app.exec_()
