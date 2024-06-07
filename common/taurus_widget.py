
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox


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

def create_my_dropdown_list_class(key, value):
    return type(key, (TaurusValueComboBox,), {
            '__init__': add_value_pairs(value)})