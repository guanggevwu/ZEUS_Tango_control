"""Hardware-free checks for pairing and the Taurus grating distance row."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from unittest.mock import patch

import taurus
from taurus.external.qt import Qt

from Newmark.GUI import (
    GRATING_DEVICES, MINIMUM_ATTRIBUTES, add_distance_row, distance_model, resolve_devices,
)
from Newmark.grating_widget import PairMoveControl, PairMoveWidget
from common.my_motor_widget import (
    MyMotorReadOnlyTaurusValue, mymotor_read_only_item_factory,
)


class GratingGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Qt.QApplication.instance() or Qt.QApplication([])

    def test_either_device_expands_to_ordered_pair(self):
        for device in GRATING_DEVICES:
            self.assertEqual(resolve_devices(device), list(GRATING_DEVICES))
            self.assertEqual(resolve_devices([device.upper()]), list(GRATING_DEVICES))

    def test_reverse_order_and_duplicates_do_not_reverse_distance(self):
        self.assertEqual(
            resolve_devices([GRATING_DEVICES[1], *GRATING_DEVICES]),
            list(GRATING_DEVICES),
        )

    def test_other_devices_keep_original_behavior(self):
        self.assertEqual(resolve_devices("test/newmark/other"), ["test/newmark/other"])
        self.assertEqual(
            resolve_devices([GRATING_DEVICES[1], "test/newmark/other"]),
            [*GRATING_DEVICES, "test/newmark/other"],
        )

    def test_combination_expands_pair(self):
        with patch.dict("Newmark.GUI.device_name_table", {"grating_combination": [GRATING_DEVICES[1]]}):
            self.assertEqual(resolve_devices(["grating_combination"]), list(GRATING_DEVICES))

    @staticmethod
    def expression(first, second):
        # Substitute local evaluation attributes for Tango inputs, retaining
        # the cross-attribute references used by the real Taurus engine.
        model = distance_model(GRATING_DEVICES)
        for device, value in zip(GRATING_DEVICES, (first, second)):
            model = model.replace(f"tango:{device}/ax1_position", f"eval:{value}")
        return model

    def test_signed_distance_and_unit_conversion(self):
        for first, second, expected in (
            ('Q(12.5,"mm")', 'Q(3.25,"mm")', 9.25),
            ('Q(3.25,"mm")', 'Q(12.5,"mm")', -9.25),
            ('Q(1,"cm")', 'Q(2,"mm")', 8.0),
        ):
            attribute = taurus.Attribute(self.expression(first, second))
            value = attribute.read().rvalue
            self.assertAlmostEqual(value.to("mm").magnitude, expected)
            self.assertFalse(attribute.isWritable())

    def test_distance_widget_is_read_only_and_formatted(self):
        panel = Qt.QWidget()
        layout = Qt.QVBoxLayout(panel)
        form = add_distance_row(layout, self.expression('Q(12.5,"mm")', 'Q(3.25,"mm")'))
        panel.show()
        self.app.processEvents()
        self.assertIsNone(form[0].writeWidget())
        self.assertIn("9.250", form[0].readWidget().text())
        self.assertIn("MOVE (BOTH)", form[0].labelWidget().text())
        self.assertEqual(form[0].readWidget().font().pointSize(), 20)
        panel.close()
        panel.deleteLater()

    def test_minimum_attribute_allowlist(self):
        self.assertEqual(MINIMUM_ATTRIBUTES, ("user_defined_name", "ax1_position"))

    def test_form_uses_available_height_instead_of_blank_spacer(self):
        panel = Qt.QWidget()
        layout = Qt.QVBoxLayout(panel)
        form = add_distance_row(
            layout, self.expression('Q(12.5,"mm")', 'Q(3.25,"mm")')
        )
        layout.addWidget(Qt.QPushButton("Init / stop"))
        layout.addStretch()
        panel.resize(780, 480)
        panel.show()
        self.app.processEvents()
        height = form.height()
        self.assertGreater(height, 200)
        self.assertEqual(form.scrollArea.verticalScrollBar().maximum(), 0)
        panel.resize(950, 650)
        self.app.processEvents()
        self.assertGreater(form.height(), height)
        self.assertEqual(form.scrollArea.verticalScrollBar().maximum(), 0)
        panel.close()
        panel.deleteLater()

    def test_distance_includes_shared_relative_controls(self):
        control = PairMoveControl(GRATING_DEVICES)
        panel = Qt.QWidget()
        layout = Qt.QVBoxLayout(panel)
        model = self.expression('Q(12.5,"mm")', 'Q(3.25,"mm")')
        first = add_distance_row(layout, model, control)
        second = add_distance_row(layout, model, control)
        panel.show()
        self.app.processEvents()
        first_controls = first[0].writeWidget()
        second_controls = second[0].writeWidget()
        self.assertIsInstance(first_controls, PairMoveWidget)
        self.assertIsInstance(second_controls, PairMoveWidget)
        first_controls.step.setValue(0.25)
        self.assertEqual(second_controls.step.value(), 0.25)
        self.assertEqual(control.step_mm, 0.25)
        self.assertFalse(first[0].getModelObj().isWritable())
        self.assertTrue(first_controls.plus.isEnabled())
        panel.close()
        panel.deleteLater()
        control.deleteLater()

    def test_newmark_and_esp_minimum_use_read_only_motor_widget(self):
        # Only the device-class metadata boundary is substituted; widgets are real.
        from types import SimpleNamespace
        for device_class in ("Newmark", "ESP301"):
            proxy = SimpleNamespace(info=lambda: SimpleNamespace(dev_class=device_class))
            parent = SimpleNamespace(getDeviceProxy=lambda: proxy)
            model = SimpleNamespace(name="ax1_position", getParentObj=lambda: parent)
            widget = mymotor_read_only_item_factory(model)
            self.assertIsInstance(widget, MyMotorReadOnlyTaurusValue)
            self.assertIsNone(widget.writeWidget())
            widget.deleteLater()


if __name__ == "__main__":
    unittest.main()