from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.extra_guiqwt import TaurusImageDialog
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.display import TaurusLabel

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


class MyTaurusLabel(TaurusLabel):
    def __init__(self):
        super().__init__()
        print(self.resetAutoTrim())


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
# changeDefaultPollingPeriod(500)
device_name = 'test/gentec/1'
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name + '/' +
         attr for attr in attrs if not attr.startswith('hide_')]

app = TaurusApplication(cmd_line_parser=None, app_name='gentec')
gui = TaurusGui()

panel2 = Qt.QWidget()
panel2_layout = Qt.QVBoxLayout()
panel2.setLayout(panel2_layout)


panel2_w1 = TaurusForm()

form_model = model
# form_model.remove(f'{device_name}/exposure')
# form_model.remove(f'{device_name}/gain')
# form_model.insert(6, f'{device_name}/exposure')
# form_model.insert(7, f'{device_name}/gain')
panel2_w1.model = form_model
panel2_layout.addWidget(panel2_w1)

# change the bool write to auto apply.
boolwidget = ['save_data', 'auto_range', 'set_zero', 'attenuator']
for key in boolwidget:
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox

boolwidget = {'save_path': None}
for key, value in boolwidget.items():
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].readWidgetClass = MyTaurusLabel


# change the text write widget to dropdown list and set auto apply
dropdown = {'display_range': ((text, value) for text, value in zip(
    dp.hide_display_range_dropdown_text_list, dp.hide_display_range_dropdown_text_value)), 'measure_mode': (('power', 'power'), ('energy', 'energy'), ('SSE', 'SSE'))}
for key, value in dropdown.items():
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = type(key, (TaurusValueComboBox,), {
        '__init__': add_value_pairs(value)})

gui.createPanel(panel2, 'parameters')
gui.removePanel('Manual')

gui.show()
app.exec_()
