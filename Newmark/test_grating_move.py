"""No real controllers: simulate only the Tango I/O boundary."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import tango
from taurus.external.qt import Qt
from Newmark.grating_widget import move_relative_pair, PairMoveControl, PairMoveWidget


class Axis:
    def __init__(self, name, position, events):
        self.name, self.position, self.events = name, position, events
        self.unit = "mm"
        self.quality = tango.AttrQuality.ATTR_VALID
        self.fail_read = self.fail_write = False

    def set_timeout_millis(self, timeout):
        self.timeout = timeout

    def get_attribute_config(self, name):
        assert name == "ax1_position"
        return SimpleNamespace(unit=self.unit)

    def read_attribute(self, name):
        assert name == "ax1_position"
        self.events.append((self.name, "read"))
        if self.fail_read:
            raise RuntimeError("Read failed")
        return SimpleNamespace(value=self.position, quality=self.quality)

    def write_attribute(self, name, value):
        assert name == "ax1_position"
        self.events.append((self.name, "write"))
        self.position = value  # Failed reply may still mean the move was accepted.
        if self.fail_write:
            raise RuntimeError("Write failed")

class PairMoveTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.axes = [Axis("first", 111.26, self.events), Axis("second", 108.26, self.events)]
        self.names = ("laser/newmark/first", "laser/newmark/second")
        devices = dict(zip(self.names, self.axes))
        self.proxy_patch = patch("Newmark.grating_widget.tango.DeviceProxy", side_effect=devices.__getitem__)
        self.proxy_patch.start()
        self.addCleanup(self.proxy_patch.stop)

    def test_relative_plus_and_minus_preserve_separation(self):
        move_relative_pair(self.names, 0.1)
        self.assertAlmostEqual(self.axes[0].position, 111.36)
        self.assertAlmostEqual(self.axes[1].position, 108.36)
        self.assertEqual(self.events, [("first", "read"), ("second", "read"), ("first", "write"), ("second", "write")])
        move_relative_pair(self.names, -0.1)
        self.assertAlmostEqual(self.axes[0].position, 111.26)
        self.assertAlmostEqual(self.axes[1].position, 108.26)
        self.assertAlmostEqual(self.axes[0].position - self.axes[1].position, 3.0)

    def test_mm_delta_converts_to_each_axis_unit(self):
        self.axes[1].unit = "um"
        self.axes[1].position = 108260.0
        move_relative_pair(self.names, 0.1)
        self.assertAlmostEqual(self.axes[1].position, 108360.0)

    def test_invalid_steps_write_neither_axis(self):
        for step in (0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                move_relative_pair(self.names, step)
        self.assertEqual(self.events, [])

    def test_read_failure_writes_neither_axis(self):
        self.axes[1].fail_read = True
        with self.assertRaisesRegex(RuntimeError, "Read failed"):
            move_relative_pair(self.names, 0.1)
        self.assertFalse(any(action == "write" for _, action in self.events))

    def test_invalid_quality_writes_neither_axis(self):
        self.axes[1].quality = tango.AttrQuality.ATTR_INVALID
        with self.assertRaises(ValueError):
            move_relative_pair(self.names, 0.1)
        self.assertFalse(any(action == "write" for _, action in self.events))

    def test_invalid_units_or_positions_write_neither_axis(self):
        for unit, position in (("degrees", 1), ("mm", float("nan"))):
            self.axes[1].unit, self.axes[1].position = unit, position
            with self.assertRaises(Exception):
                move_relative_pair(self.names, 0.1)
        self.assertFalse(any(action == "write" for _, action in self.events))

    def test_partial_write_failure_is_reported_without_retry(self):
        self.axes[1].fail_write = True
        with self.assertRaisesRegex(RuntimeError, "One axis may have moved"):
            move_relative_pair(self.names, 0.1)
        self.assertEqual(sum(action == "write" for _, action in self.events), 2)

    def test_first_write_failure_does_not_move_second(self):
        self.axes[0].fail_write = True
        with self.assertRaisesRegex(RuntimeError, "separation may have changed"):
            move_relative_pair(self.names, 0.1)
        self.assertEqual(self.axes[1].position, 108.26)
        self.assertEqual(sum(action == "write" for _, action in self.events), 1)

    def test_buttons_send_equal_steps_and_report_errors(self):
        self.app = Qt.QApplication.instance() or Qt.QApplication([])
        control = PairMoveControl(self.names)
        widget = PairMoveWidget(control)
        errors = []
        control.failed.connect(errors.append)
        for button, expected in ((widget.plus, 111.36), (widget.minus, 111.26)):
            button.click()
            self.assertAlmostEqual(self.axes[0].position, expected)
            self.assertAlmostEqual(self.axes[0].position - self.axes[1].position, 3.0)
        self.assertEqual(errors, [])
        self.axes[1].fail_write = True
        widget.plus.click()
        self.assertEqual(len(errors), 1)
        self.assertIn("separation may have changed", errors[0])
        widget.deleteLater()
        control.deleteLater()


if __name__ == "__main__":
    unittest.main()