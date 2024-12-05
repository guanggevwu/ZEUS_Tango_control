import argparse
from taurus_pyqtgraph import TaurusTrend, TaurusPlot
from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox
from taurus.qt.qtgui.button import TaurusCommandButton

import sys
import os
from taurus import tauruscustomsettings
tauruscustomsettings.ORGANIZATION_LOGO = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'common', 'img', 'zeus.png')
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class
    from common.TaurusGUI_Argparse import TaurusArgparse

parser = TaurusArgparse(
    description='GUI for Gentec-EO devices', device_default='test/dg535/1', polling_default=3000)
args = parser.parse_args()

device_name = args.device
changeDefaultPollingPeriod(args.polling)
is_form_compact = args.compact
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name + '/' +
         attr for attr in attrs if not attr.startswith('hide_')]

app = TaurusApplication(cmd_line_parser=None,
                        app_name=device_name.replace('/', '_'))
gui = TaurusGui()

panel1 = Qt.QWidget()
panel1_layout = Qt.QVBoxLayout()
panel1.setLayout(panel1_layout)


panel1_w1 = TaurusForm()

form_model = [i for i in model]
order_list = ['name_attr', 'trigger', 'internal_rate', 'burst_rate', 'A_relative_channel', 'A_relative_delay', 'B_relative_channel',
              'B_relative_delay', 'C_relative_channel', 'C_relative_delay', 'D_relative_channel', 'D_relative_delay', 'send_write', 'send_query']
for idx, attr in enumerate(order_list):
    form_model.remove(f'{device_name}/{attr}')
    form_model.insert(idx, f'{device_name}/{attr}')

panel1_w1.model = form_model
panel1_layout.addWidget(panel1_w1)
panel1_w1.compact = is_form_compact

# TaurusLabel auto trim function not work in TaurusForm
# change the text write widget to dropdown list and set auto apply
# must convert numpy.float64 to float so that the dropdown list can work.
dropdown = {}
common_dropdown = (('T0', 'T0'), ('A', 'A'),
                   ('B', 'B'), ('C', 'C'), ('D', 'D'))
for channel in ['A', 'B', 'C', 'D']:
    dropdown[f'{channel}_relative_channel'] = tuple(
        i for i in common_dropdown if i != (channel, channel))
dropdown['trigger'] = (('Internal', 'Internal'), ('External', 'External'),
                       ('Single Shot', 'Single Shot'), ('Burst', 'Burst'))

# change the bool write to auto apply.
for idx, full_attr in enumerate(form_model):
    if full_attr.split('/')[-1] in attrs and dp.attribute_query(full_attr.split('/')[-1]).data_type == 1:
        panel1_w1[idx].writeWidgetClass = MyTaurusValueCheckBox
    if full_attr.split('/')[-1] in dropdown:
        panel1_w1[idx].writeWidgetClass = create_my_dropdown_list_class(
            full_attr.split('/')[-1], dropdown[full_attr.split('/')[-1]], autoApply=False)

panel1_command = Qt.QWidget()
panel1_command_layout = Qt.QHBoxLayout()
panel1_command.setLayout(panel1_command_layout)

# sets of widgets. command in bottom.
order_list = ['send_single_shot']

for cmd in order_list:
    if cmd in commands:
        panel1_command_w = TaurusCommandButton(
            command=cmd
        )
        panel1_command_w.setCustomText(cmd)
        panel1_command_w.setModel(device_name)
        panel1_command_layout.addWidget(panel1_command_w)
panel1_layout.addWidget(panel1_command)


gui.removePanel('Manual')
gui.createPanel(panel1, 'parameters')

gui.show()
app.exec_()
