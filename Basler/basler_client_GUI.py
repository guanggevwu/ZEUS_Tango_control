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


# class MyComboBox(TaurusValueComboBox):
#     def __init__(self):
#         super().__init__()
#         self.addValueNames((('Off', 'Off'), ('Software', 'Software')))


class MyTaurusValueCheckBox(TaurusValueCheckBox):
    def __init__(self):
        super().__init__()
        self.autoApply = True
        self.showText = False


def add_value_pairs(values):
    def constructor(self):
        TaurusValueComboBox.__init__(self)
        self.addValueNames(values)
        self.autoApply = True
    return constructor


# TriggerSource = type('TriggerSource', (TaurusValueComboBox,), {
#                      '__init__': add_value_pairs((('Off', 'Off'), ('Software', 'Software')))})


# if the polling periods in Taurus is shorter than these in Tango, it either doesn't work or is wasted.
# if the polling periods in Taurus is longer than these in Tango, it only retrives part of information from the server.
device_name = sys.argv[1] if len(sys.argv) > 1 else 'test/basler/1'
changeDefaultPollingPeriod(sys.argv[2]) if len(sys.argv) > 2 else None
device_name = 'test/basler/1'
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name] + [device_name + '/' + attr for attr in attrs]


# with open("modification.json") as outfile:
#     modification = json.load(outfile)


app = TaurusApplication(cmd_line_parser=None, app_name='MyGui')
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
form_model.insert(6, f'{device_name}/exposure')
form_model.insert(7, f'{device_name}/gain')
panel2_w1.model = form_model
panel2_layout.addWidget(panel2_w1)

# change the bool write to auto apply.
boolwidget = {'save_data': None}
for key, value in boolwidget.items():
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox

# change the text write widget to dropdown list and set auto apply
dropdown = {'trigger_source': (('Off', 'Off'), ('Software', 'Software'), ('External', 'Line1')), 'trigger_selector': (
    ('AcquisitionStart', 'AcquisitionStart'), ('FrameStart', 'FrameStart')), }
for key, value in dropdown.items():
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = type(key, (TaurusValueComboBox,), {
        '__init__': add_value_pairs(value)})

gui.createPanel(panel2, 'parameters')
gui.removePanel('Manual')

gui.show()
app.exec_()
