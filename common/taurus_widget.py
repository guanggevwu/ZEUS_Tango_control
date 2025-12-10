
from taurus import Device, changeDefaultPollingPeriod
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox, TaurusValueLineEdit
from taurus.qt.qtgui.compact import TaurusReadWriteSwitcher
from taurus.qt.qtgui.display import TaurusLabel
from taurus.qt.qtgui.button import TaurusCommandButton


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


class RelativeMotion():
    def __init__(self, app, attr: str, command: dict):
        '''Create a relative motion panel for one axis
        Parameters
        ----------
        app : BaslerGUI
            The application instance to which the panel will be added.
        attr : str
            The relative motion step attribute for the step widget.
        command : dict
            The command dictionary. It contains the following keys:
            - name: str
                The name of the command.
            - label: list[str]
                The label for the command buttons. There should be two labels, one for each button.
            - params: list[list]
                The parameters for the command. The format is [[parameters for first button],[parameters for second button]]
        '''
        self.widget, self.layout = app.create_blank_panel(
            VorH='h')
        step_widget = TaurusReadWriteSwitcher()
        r_widget = TaurusLabel()
        w_widget = TaurusValueLineEdit()

        step_widget.setReadWidget(r_widget)
        step_widget.setWriteWidget(w_widget)
        step_widget.model = attr
        button1 = TaurusCommandButton(
            command=command['name'], parameters=command['params'][0]
        )
        button2 = TaurusCommandButton(
            command=command['name'], parameters=command['params'][1]
        )
        button1.setCustomText(command['label'][0])
        button1.setModel('/'.join(attr.split('/')[:-1]))
        button2.setCustomText(command['label'][1])
        button2.setModel('/'.join(attr.split('/')[:-1]))

        self.layout.addWidget(button1)
        self.layout.addWidget(step_widget)
        self.layout.addWidget(button2)
