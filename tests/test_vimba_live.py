"""Exercise camera callbacks without importing Tango or opening Vimba hardware."""

import ast
import datetime
from pathlib import Path
from queue import Empty, Queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np


def load_device_class():
    path = Path(__file__).resolve().parents[1] / 'Vimba' / 'server.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    source_class = next(node for node in tree.body
                        if isinstance(node, ast.ClassDef) and node.name == 'Vimba')
    method_names = {
        'handler_last_frame', 'handler_one_by_one', 'read_is_new_image',
        'read_image', 'get_ready', 'relax',
    }
    methods = [node for node in source_class.body
               if isinstance(node, ast.FunctionDef) and node.name in method_names]
    for method in methods:
        method.decorator_list = []
    namespace = {
        'np': np, 'datetime': datetime, 'Queue': Queue, 'Empty': Empty,
        'Camera': object, 'Stream': object, 'Frame': object,
        'FrameStatus': SimpleNamespace(Complete='complete'),
    }
    exec(compile(ast.Module(body=methods, type_ignores=[]),
         str(path), 'exec'), namespace)
    return type('VimbaMethods', (), {name: namespace[name] for name in method_names})


DeviceMethods = load_device_class()


class TestVimbaLive(unittest.TestCase):
    def setUp(self):
        self.device = DeviceMethods()
        self.device.imageq = Queue()
        self.device.camera = Mock()
        self.device.camera.is_streaming.return_value = False
        self.device.logger = Mock()
        self.device.push_change_event = Mock()
        self.device.enable_center_of_mass = False
        self.device._trigger_source = 'Off'
        self.device._image_number = 0
        self.device._read_time = 'N/A'
        self.device._image = np.zeros((2, 3), dtype=np.uint16)

    def frame(self, value, status='complete'):
        frame = Mock()
        frame.get_status.return_value = status
        frame.as_numpy_ndarray.return_value = np.full(
            (2, 3, 1), value, dtype=np.uint16)
        return frame

    def deliver(self, frame, live=True):
        handler = self.device.handler_last_frame if live else self.device.handler_one_by_one
        handler(self.device.camera, None, frame)

    def test_live_frame_publishes_image_on_poll(self):
        self.device.get_ready()
        self.device.camera.start_streaming.assert_called_once_with(
            self.device.handler_last_frame)
        frame = self.frame(7)
        self.deliver(frame)
        self.assertTrue(self.device.read_is_new_image())
        name, image = self.device.push_change_event.call_args.args
        self.assertEqual(name, 'image')
        np.testing.assert_array_equal(image, np.full((2, 3), 7))
        self.assertEqual(self.device._image_number, 1)
        self.assertNotEqual(self.device._read_time, 'N/A')
        self.assertFalse(self.device.read_is_new_image())
        self.device.push_change_event.assert_called_once()
        self.device.camera.queue_frame.assert_called_once_with(frame)

    def test_live_retains_only_latest_pending_frame(self):
        for value in range(50):
            self.deliver(self.frame(value))
            self.assertEqual(self.device.imageq.qsize(), 1)
        self.assertTrue(self.device.read_is_new_image())
        np.testing.assert_array_equal(
            self.device.read_image(), np.full((2, 3), 49))
        self.assertFalse(self.device.read_is_new_image())

    def test_triggered_frames_remain_fifo(self):
        for value in range(3):
            self.deliver(self.frame(value), live=False)
        self.assertEqual(self.device.imageq.qsize(), 3)
        for value in range(3):
            self.assertTrue(self.device.read_is_new_image())
            np.testing.assert_array_equal(
                self.device.read_image(), np.full((2, 3), value))
        self.assertFalse(self.device.read_is_new_image())

    def test_requeued_sdk_buffer_cannot_change_retained_image(self):
        for live in (True, False):
            with self.subTest(live=live):
                frame = self.frame(7)
                self.device.camera.queue_frame.side_effect = (
                    lambda queued: queued.as_numpy_ndarray.return_value.fill(99))
                self.deliver(frame, live=live)
                np.testing.assert_array_equal(
                    self.device.read_image(), np.full((2, 3), 7))
                self.assertTrue(self.device.read_is_new_image())
                np.testing.assert_array_equal(
                    self.device.read_image(), np.full((2, 3), 7))

    def test_incomplete_frames_are_requeued_without_publishing(self):
        for live in (True, False):
            with self.subTest(live=live):
                frame = self.frame(7, status='incomplete')
                self.deliver(frame, live=live)
                self.device.camera.queue_frame.assert_called_with(frame)
                frame.as_numpy_ndarray.assert_not_called()
                self.assertFalse(self.device.read_is_new_image())
        self.device.push_change_event.assert_not_called()

    def test_poll_does_not_block_when_queue_is_empty(self):
        self.device.imageq = Mock()
        self.device.imageq.get_nowait.side_effect = Empty
        self.assertFalse(self.device.read_is_new_image())
        self.device.imageq.get.assert_not_called()
        self.device.push_change_event.assert_not_called()

    def test_restart_discards_pending_frames(self):
        self.deliver(self.frame(7), live=False)
        self.device.camera.is_streaming.return_value = True
        self.device.get_ready()
        self.device.camera.stop_streaming.assert_called_once()
        self.assertTrue(self.device.imageq.empty())


if __name__ == '__main__':
    unittest.main()
