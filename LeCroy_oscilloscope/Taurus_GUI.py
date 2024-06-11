from taurus_pyqtgraph import TaurusPlot
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
import os
if True:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from common.taurus_widget import MyTaurusValueCheckBox, create_my_dropdown_list_class

# if the polling periods in Taurus is shorter than these in Tango, it either doesn't work or is wasted.
# if the polling periods in Taurus is longer than these in Tango, it only retrives part of information from the server.
# changeDefaultPollingPeriod(500)
device_name = sys.argv[1] if len(sys.argv) > 1 else 'facility/lecroy/wavesurfer_3034z_1'
changeDefaultPollingPeriod(sys.argv[2]) if len(sys.argv) > 2 else None
dp = Device(device_name)

attrs = dp.get_attribute_list()
commands = dp.get_command_list()
model = [device_name + '/' +
         attr for attr in attrs if not attr.startswith('hide_')]

app = TaurusApplication(cmd_line_parser=None, app_name='gentec')
gui = TaurusGui()

panel1 = Qt.QWidget()
panel1_layout = Qt.QVBoxLayout()
panel1.setLayout(panel1_layout)


panel1_w1 = TaurusForm()

form_model = model
panel1_w1.model = form_model
panel1_layout.addWidget(panel1_w1)

# change the bool write to auto apply.
for i in form_model:
    if i.split('/')[-1] in attrs and dp.attribute_query(i.split('/')[-1]).data_type == 1:
        idx = form_model.index(i)
        panel1_w1[idx].writeWidgetClass = MyTaurusValueCheckBox

gui.createPanel(panel1, 'parameters')
gui.removePanel('Manual')

channel_panel = []
channel_index = [1,2,3,4]
for idx, channel in enumerate(channel_index):
    channel_panel.append(TaurusPlot())
    channel_panel[idx].setModel([(f'{device_name}/waveform_c{channel}_x',f'{device_name}/waveform_c{channel}_y')])
    gui.createPanel(channel_panel[idx], f'channel {channel}')

# panel2 = TaurusPlot()
# model2 = [(f'{device_name}/waveform_c1_x', f'{device_name}/waveform_c1_y')]
# panel2.setModel(model2)
# gui.createPanel(panel2, f'channel 1')

gui.show()
app.exec_()

