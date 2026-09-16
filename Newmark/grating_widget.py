"""GUI-only relative motion of two independently controlled grating axes."""

import math

import tango
from taurus.core.units import Quantity
from taurus.external.qt import Qt
from taurus.qt.qtgui.container import TaurusWidget


def move_relative_pair(device_names, delta_mm):
    """Read both positions before writing either; never retry failed moves."""
    if len(device_names) != 2 or len(set(device_names)) != 2:
        raise ValueError("MOVE (BOTH) requires two distinct controllers")
    if not math.isfinite(delta_mm) or delta_mm == 0:
        raise ValueError("The relative step must be finite and greater than zero")
    devices = [tango.DeviceProxy(name) for name in device_names]
    targets = []
    for device in devices:
        device.set_timeout_millis(2000)
        unit = device.get_attribute_config("ax1_position").unit
        delta = Quantity(delta_mm, "mm").to(unit).magnitude
        position = device.read_attribute("ax1_position")
        if position.quality == tango.AttrQuality.ATTR_INVALID:
            raise ValueError("Cannot move both: an axis position is invalid")
        target = float(position.value) + delta
        if not math.isfinite(target):
            raise ValueError("Cannot move both: an axis target is not finite")
        targets.append(target)

    try:
        # Separate controllers cannot start atomically. Send back-to-back
        # commands, without waiting for either axis to reach its destination.
        for device, target in zip(devices, targets):
            device.write_attribute("ax1_position", target)
    except Exception as exc:
        raise RuntimeError(
            "Pair move failed. One axis may have moved; separation may have changed. "
            f"Check both positions before retrying. {exc}"
        ) from exc


class PairMoveControl(Qt.QObject):
    """Share the relative step between the less and minimum panels."""

    stepChanged = Qt.pyqtSignal(float)
    failed = Qt.pyqtSignal(str)

    def __init__(self, devices, parent=None):
        super().__init__(parent)
        self.devices = tuple(devices)
        self.step_mm = 0.1

    def set_step(self, value):
        if value != self.step_mm:
            self.step_mm = value
            self.stepChanged.emit(value)

    def move(self, sign):
        try:
            move_relative_pair(self.devices, sign * self.step_mm)
        except Exception as exc:
            self.failed.emit(str(exc))


class PairMoveWidget(TaurusWidget):
    def __init__(self, control, parent=None):
        super().__init__(parent)
        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.minus = Qt.QPushButton("◀")
        self.plus = Qt.QPushButton("▶")
        self.step = Qt.QDoubleSpinBox()
        self.step.setDecimals(3)
        self.step.setRange(0.001, 1e9)
        self.step.setSingleStep(0.1)
        self.step.setButtonSymbols(Qt.QAbstractSpinBox.NoButtons)
        self.step.setValue(control.step_mm)
        self.step.setToolTip("Relative step for BOTH controllers, in mm")
        self.step.valueChanged.connect(control.set_step)
        control.stepChanged.connect(self.step.setValue)
        self.minus.clicked.connect(lambda: control.move(-1))
        self.plus.clicked.connect(lambda: control.move(1))
        for widget in (self.minus, self.step, self.plus):
            widget.setFont(Qt.QFont("Sans Serif", 12 if widget != self.step else 20))
            layout.addWidget(widget)
