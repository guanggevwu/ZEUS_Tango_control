from taurus.qt.qtgui.display import TaurusLabel
from taurus.qt.qtgui.input import TaurusValueLineEdit, TaurusValueSpinBox, TaurusWheelEdit
import sys
from taurus.external.qt import Qt
from taurus.qt.qtgui.application import TaurusApplication

app = TaurusApplication(sys.argv, cmd_line_parser=None)
panel = Qt.QWidget()
layout = Qt.QHBoxLayout()
panel.setLayout(layout)
w1 = TaurusLabel()
w2 = TaurusLabel()
w3 = TaurusValueLineEdit()  # or TaurusValueSpinBox or TaurusWheelEdit
w4 = TaurusLabel()
layout.addWidget(w1)
layout.addWidget(w2)
layout.addWidget(w3)
layout.addWidget(w4)
w1.model, w1.bgRole = 'sys/taurustest/1/position#label', ''
w2.model = 'sys/taurustest/1/position#rvalue.magnitude'
w3.model = 'sys/taurustest/1/position#wvalue.magnitude'
w4.model, w4.bgRole = 'sys/taurustest/1/position#rvalue.units', ''

panel.show()
sys.exit(app.exec_())
