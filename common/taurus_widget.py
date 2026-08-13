
from taurus import Device, changeDefaultPollingPeriod
from taurus.external.qt import Qt
from taurus.qt.qtgui.input import TaurusValueComboBox, TaurusValueCheckBox, TaurusValueLineEdit
from taurus.qt.qtgui.compact import TaurusReadWriteSwitcher
from taurus.qt.qtgui.display import TaurusLabel, TaurusLed
from taurus.qt.qtgui.button import TaurusCommandButton


class MyTaurusValueCheckBox(TaurusValueCheckBox):
    def __init__(self):
        super().__init__()
        self.autoApply = True
        self.showText = False


class ToggleTaurusLed(TaurusLed):
    """A TaurusLed that toggles a writable boolean attribute on left click."""

    def __init__(self, parent=None, designMode=False):
        super().__init__(parent=parent, designMode=designMode)
        self.setCursor(Qt.Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to toggle")

    def mouseReleaseEvent(self, a0):
        if a0 is not None and a0.button() == Qt.Qt.MouseButton.LeftButton and self._toggle_value():
            a0.accept()
            return
        super().mouseReleaseEvent(a0)

    def _toggle_value(self):
        model = self.getModelObj()
        if model is None:
            return False
        try:
            value = model.read().rvalue
            value = getattr(value, "magnitude", value)
            model.write(not bool(value))
            return True
        except Exception as exc:
            self.warning("Could not toggle %s: %s", self.getModelName(), exc)
            return False


class BoolLedSwitcher(TaurusReadWriteSwitcher):
    """Shows a TaurusLed that toggles on click; F2 switches to checkbox editing.
    Use as the read widget of a TaurusForm row with write widget set to None:
        row.setReadWidgetClass(BoolLedSwitcher)
        row.setWriteWidgetClass(None)
    """
    readWClass = ToggleTaurusLed
    writeWClass = MyTaurusValueCheckBox
    enterEditTriggers = (Qt.Qt.Key.Key_F2,)
    exitEditTriggers = ("applied", Qt.Qt.Key.Key_Escape)

    def _onEnterEditActionTriggered(self):
        self._sync_write_widget()
        super()._onEnterEditActionTriggered()

    def _sync_write_widget(self):
        model = self.getModelObj()
        if model is None or self.writeWidget is None:
            return
        try:
            value = model.read().rvalue
            value = getattr(value, "magnitude", value)
            self.writeWidget.blockSignals(True)
            self.writeWidget.setValue(value)
        finally:
            self.writeWidget.blockSignals(False)


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
