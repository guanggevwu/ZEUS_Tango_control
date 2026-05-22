from taurus.qt.qtgui.panel import TaurusValue
from taurus.qt.qtgui.container import TaurusWidget
from taurus.external.qt import Qt
from taurus.qt.qtgui.input import TaurusValueLineEdit
from taurus.qt.qtgui.panel.taurusvalue import UnitLessLineEdit
from taurus.core.units import Quantity
import re
from .taurus_widget import BoolLedSwitcher


class MyMotorExtraWidget(TaurusWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn = BoolLedSwitcher()
        layout.addWidget(self.btn)
        self.modelChanged.connect(self._on_model_changed)

    def _on_model_changed(self, model_name):
        if not model_name:
            return

        # Taurus sets model after __init__; derive the sibling status attribute.
        base = model_name.split("#", 1)[0]
        parts = base.rsplit("/", 1)
        if len(parts) != 2:
            return
        dev_name, attr_name = parts

        match = re.match(r"^ax(\d+)_position$", attr_name, flags=re.IGNORECASE)
        if not match:
            return

        ax_number = match.group(1)
        self.btn.model = f"{dev_name}/ax{ax_number}_status"


class MyMotorWriteWidget(TaurusWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = Qt.QHBoxLayout(self)
        layout.setSpacing(2)

        self.minus = Qt.QPushButton("◀")
        self.plus = Qt.QPushButton("▶")

        self.step = _MagnitudeOnlyLineEdit()
        self.step.setValidator(Qt.QDoubleValidator(0.0, 1e9, 6, self))
        self.abs_input = TaurusValueLineEdit()

        layout.addWidget(self.minus)
        layout.addWidget(self.step)
        layout.addWidget(self.plus)
        layout.addWidget(self.abs_input)

        self.minus.clicked.connect(lambda: self._move(-1))
        self.plus.clicked.connect(lambda: self._move(+1))
        self.modelChanged.connect(self._on_model_changed)

    def _on_model_changed(self, model_name):
        if model_name:
            self.abs_input.model = f"{model_name}#wvalue.magnitude"
            # By using a model instead of regular input, the step value is remembered thus is not reset after restart GUI.
            self.step.model = model_name.replace('_position', '_step')

    def _move(self, sign):
        model = self.getModelObj()
        if model is None:
            return
        pos = model.read().rvalue
        step_text = self.step.text().strip()
        step = float(step_text)
        current = getattr(pos, 'magnitude', pos)
        if current is None:
            return
        target = float(current) + sign * step
        model.write(target)


class MyMotorTaurusValue(TaurusValue):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWriteWidgetClass(MyMotorWriteWidget)
        self.setExtraWidgetClass(MyMotorExtraWidget)


class _MagnitudeOnlyLineEdit(UnitLessLineEdit):

    def setValue(self, v):
        if isinstance(v, Quantity):
            v = v.magnitude
        else:
            v = getattr(v, "magnitude", v)
        return super().setValue(v)


class MyGratingWriteWidget(TaurusWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = Qt.QHBoxLayout(self)
        layout.setSpacing(2)

        self.minus = Qt.QPushButton("◀")
        self.plus = Qt.QPushButton("▶")

        self.step = _MagnitudeOnlyLineEdit()
        self.step.setValidator(Qt.QDoubleValidator(0.0, 1e9, 6, self))

        layout.addWidget(self.minus)
        layout.addWidget(self.step)
        layout.addWidget(self.plus)

        self.minus.clicked.connect(lambda: self._move(-1))
        self.plus.clicked.connect(lambda: self._move(+1))
        self.modelChanged.connect(self._on_model_changed)

    def _on_model_changed(self, model_name):
        if model_name:
            self.step.model = model_name.replace('_distance', '_step')

    def _move(self, sign):
        model = self.getModelObj()
        if model is None:
            return
        ax1_position_attr = model.getParentObj().getAttribute('ax1_position')
        ax1_position = ax1_position_attr.read().rvalue.magnitude
        ax2_position_attr = model.getParentObj().getAttribute('ax2_position')
        ax2_position = ax2_position_attr.read().rvalue.magnitude

        step_text = self.step.text().strip()
        step = float(step_text)
        ax1_position_attr.write(float(ax1_position) + sign * step)
        ax2_position_attr.write(float(ax2_position) + sign * step)


class MyGratingTaurusValue(TaurusValue):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWriteWidgetClass(MyGratingWriteWidget)


def mymotor_item_factory(model):

    try:
        dev = model.getParentObj()
        dev_class = dev.getDeviceProxy().info().dev_class
    except Exception:
        return None

    if "_position" in model.name.lower() and "ax" in model.name.lower():
        return MyMotorTaurusValue()
    elif dev_class == "ESP301" and model.name.lower() == "ax12_distance":
        return MyGratingTaurusValue()
    return None
