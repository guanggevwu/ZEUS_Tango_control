import sys
import taurus
from taurus import changeDefaultPollingPeriod
from taurus.qt.qtgui.panel import TaurusForm
from taurus.external.qt import Qt
# from taurus.qt.qtgui import extra_guiqwt
from taurus.qt.qtgui.application import TaurusApplication
import tango

# changeDefaultPollingPeriod(500)
app = TaurusApplication(sys.argv, cmd_line_parser=None)
w = TaurusForm()

device_name = 'test/asyncio_device/asyncio_device_1'
dp = tango.DeviceProxy(device_name)
# dp = taurus.Device(device_name)

attrs = dp.get_attribute_list()
model = [device_name] + [device_name + '/' + attr for attr in attrs]
w = TaurusForm()

w.model = model
w.show()
sys.exit(app.exec_())
