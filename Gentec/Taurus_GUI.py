from taurus_pyqtgraph import TaurusTrend
from taurus.qt.qtgui.application import TaurusApplication
from taurus.qt.qtgui.taurusgui import TaurusGui
from taurus.external.qt import Qt
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueComboBox
import sys
import os
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class

# TriggerSource = type('TriggerSource', (TaurusValueComboBox,), {
#                      '__init__': add_value_pairs((('Off', 'Off'), ('Software', 'Software')))})


# if the polling periods in Taurus is shorter than these in Tango, it either doesn't work or is wasted.
# if the polling periods in Taurus is longer than these in Tango, it only retrives part of information from the server.
# changeDefaultPollingPeriod(500)
device_name = sys.argv[1] if len(sys.argv) > 1 else 'test/gentec/1'
changeDefaultPollingPeriod(500)
changeDefaultPollingPeriod(sys.argv[2]) if len(sys.argv) > 2 else None
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name + '/' +
         attr for attr in attrs if not attr.startswith('hide_')]
statistic_panel = ['shot', 'statistics_shots',
                   'average', 'max', 'min', 'std',  'start_statistics', ]
app = TaurusApplication(cmd_line_parser=None, app_name=device_name)
gui = TaurusGui()

panel1 = Qt.QWidget()
panel1_layout = Qt.QVBoxLayout()
panel1.setLayout(panel1_layout)


panel1_w1 = TaurusForm()


form_model = [i for i in model if i.split('/')[-1] not in statistic_panel]
order_list = ['model', 'main_value', 'read_time', 'save_data',
              'save_path', 'display_range', 'auto_range', 'wavelength']
for idx, attr in enumerate(order_list):
    form_model.remove(f'{device_name}/{attr}')
    form_model.insert(idx, f'{device_name}/{attr}')

panel1_w1.model = form_model
panel1_layout.addWidget(panel1_w1)

# change the bool write to auto apply.
for i in form_model:
    if i.split('/')[-1] in attrs and dp.attribute_query(i.split('/')[-1]).data_type == 1:
        idx = form_model.index(i)
        panel1_w1[idx].writeWidgetClass = MyTaurusValueCheckBox

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
    panel1_w1[idx].writeWidgetClass = create_my_dropdown_list_class(key, value)

gui.removePanel('Manual')

# panel for trend
panel2 = TaurusTrend()
model2 = [f'{device_name}/main_value_float']
panel2.setModel(model2)

# panel for statistics
panel3 = TaurusForm()
statistic_panel.insert(0, 'main_value')
form_model_3 = [device_name + '/' +
                attr for attr in statistic_panel if not attr.startswith('hide_')]

panel3.model = form_model_3
# change the bool write to auto apply.
for i in form_model_3:
    if i.split('/')[-1] in attrs and dp.attribute_query(i.split('/')[-1]).data_type == 1:
        idx = form_model_3.index(i)
        panel3[idx].writeWidgetClass = MyTaurusValueCheckBox

# change font size
for row in panel3:
    for method_attr in ['readWidget', 'writeWidget', 'unitsWidget', 'labelWidget']:
        col_widget = getattr(row, method_attr)()
        if col_widget:
            col_widget.setStyleSheet("font-size: 20px")


gui.createPanel(panel1, 'parameters')
gui.createPanel(panel3, 'statistics_numbers')
gui.createPanel(panel2, 'statistics_trend')


gui.show()
app.exec_()
