
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox


class MyTaurusValueCheckBox(TaurusValueCheckBox):
    def __init__(self):
        super().__init__()
        self.autoApply = True
        self.showText = False


def add_value_pairs(values, autoApply=True):
    def constructor(self):
        TaurusValueComboBox.__init__(self)
        self.addValueNames(values)
        self.autoApply = autoApply
    return constructor


def create_my_dropdown_list_class(key, value, autoApply=True):
    return type(key, (TaurusValueComboBox,), {
        '__init__': add_value_pairs(value, autoApply)})
