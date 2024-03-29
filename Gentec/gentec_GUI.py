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
# changeDefaultPollingPeriod(500)
device_name = sys.argv[1] if len(sys.argv) > 1 else 'test/gentec/1'
changeDefaultPollingPeriod(sys.argv[2]) if len(sys.argv) > 2 else None
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
form_model.remove(f'{device_name}/main_value')
form_model.remove(f'{device_name}/display_range')
form_model.insert(2, f'{device_name}/main_value')
form_model.insert(3, f'{device_name}/display_range')
panel2_w1.model = form_model
panel2_layout.addWidget(panel2_w1)

# change the bool write to auto apply.
boolwidget = ['save_data', 'auto_range', 'set_zero', 'attenuator']
boolwidget = [e for e in boolwidget if e in [
    f.split('/')[-1] for f in form_model]]
for key in boolwidget:
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = MyTaurusValueCheckBox

# TaurusLabel auto trim function not work in TaurusForm
# change the text write widget to dropdown list and set auto apply
# must convert numpy.float64 to float so that the dropdown list can work.
dropdown = {'display_range': ((text, float(value)) for text, value in zip(
    dp.hide_display_range_dropdown_text_list, dp.hide_display_range_dropdown_text_value))}
if dp.model == "PH100-Si-HA-OD1":
    dropdown['measure_mode'] = (('Power', '0'), ('SSE', '2'))
else:
    dropdown['measure_mode'] = (('Energy', '1'), ('SSE', '2'))
for key, value in dropdown.items():
    idx = form_model.index(f'{device_name}/{key}')
    panel2_w1[idx].writeWidgetClass = type(key, (TaurusValueComboBox,), {
        '__init__': add_value_pairs(value)})

gui.createPanel(panel2, 'parameters')
gui.removePanel('Manual')

gui.show()
app.exec_()
