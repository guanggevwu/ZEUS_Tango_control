from taurus.qt.qtgui.panel import TaurusValue
from taurus.qt.qtgui.container import TaurusWidget
from taurus.external.qt import Qt
from taurus.qt.qtgui.input import TaurusValueLineEdit
from taurus.qt.qtgui.panel.taurusvalue import UnitLessLineEdit
from taurus.core.units import Quantity
from common.taurus_widget import BoolLedSwitcher


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

        if attr_name.lower().endswith("_position"):
            self.btn.model = f"{dev_name}/{attr_name[:-9]}_status"


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
        try:
            step = float(self.step.text().strip())
            device = model.getParentObj().getDeviceProxy()
            if device.info().dev_class in ("ESP301", "Newmark"):
                attr_name = model.name.lower().rsplit('/', 1)[-1]
                axis = int(attr_name.removeprefix('ax').removesuffix('_position'))
                device.jog_axis([axis, sign * step])
                return
        except Exception as exc:
            self.warning("Could not jog motor: %s", exc)
            return
        pos = model.read().rvalue
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


class MyMotorReadOnlyTaurusValue(TaurusValue):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWriteWidgetClass(None)
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
        try:
            step = float(self.step.text().strip())
            model.getParentObj().getDeviceProxy().jog_grating(sign * step)
        except Exception as exc:
            self.warning("Could not jog grating: %s", exc)


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

    model_name = model.name.lower()
    if model_name.endswith("_position"):
        return MyMotorTaurusValue()
    elif dev_class == "ESP301" and model.name.lower() == "ax12_distance":
        return MyGratingTaurusValue()
    return None


def mymotor_read_only_item_factory(model):

    try:
        dev = model.getParentObj()
        dev_class = dev.getDeviceProxy().info().dev_class
    except Exception:
        return None

    model_name = model.name.lower()
    if dev_class in ("ESP301", "Newmark") and model_name.endswith("_position"):
        return MyMotorReadOnlyTaurusValue()
    return None
