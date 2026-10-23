"""Hardware-free checks of production acquisition methods (no Tango startup)."""

import ast
import datetime
from pathlib import Path
from queue import Empty, Queue
from types import SimpleNamespace
from typing import Any
from time import monotonic
import unittest
from unittest.mock import Mock

import numpy as np


def load_acquisition_class():
    path = Path(__file__).resolve().parents[1] / 'Vimba' / 'server.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    device = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and node.name == 'Vimba')
    wrapper = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == 'grabbing_wrap')
    names = {'read_packet_size', 'write_packet_size', 'adjust_packet_size', 'get_ready', 'relax',
             'handler_one_by_one', 'handler_last_frame',
             'read_is_new_image', 'read_image'}
    methods = [node for node in device.body
               if isinstance(node, ast.FunctionDef) and node.name in names]
    for method in methods:
        if method.name != 'write_packet_size':
            method.decorator_list = []
    device.bases = []
    device.decorator_list = []
    device.body = list(methods)
    namespace: dict[str, Any] = dict(np=np, Queue=Queue, Empty=Empty, datetime=datetime,
                                     monotonic=monotonic, sleep=Mock(),
                                     Camera=object, Stream=object, Frame=object,
                                     FrameStatus=SimpleNamespace(Complete='Complete'))
    exec(compile(ast.Module(body=[wrapper, device], type_ignores=[]), str(path), 'exec'),
         namespace)
    return namespace['Vimba'], namespace


class TestVimbaAcquisition(unittest.TestCase):
    def setUp(self):
        cls, self.namespace = load_acquisition_class()
        self.device = cls()
        self.device.camera = Mock()
        self.device.camera.is_streaming.return_value = False
        self.device.camera.get_streams.return_value = []
        self.device.logger = Mock()
        self.device.imageq = Queue()
        self.device.enable_center_of_mass = False
        self.device._trigger_source = 'Software'
        self.device._image_number = 0
        self.device.push_change_event = Mock()

    def frame(self, status='Complete'):
        frame = Mock()
        frame.get_status.return_value = status
        frame.as_numpy_ndarray.return_value = np.ones(
            (3, 4, 1), dtype=np.uint16)
        return frame

    def test_streaming_does_not_adjust_packet_size(self):
        adjust = Mock()
        stream = SimpleNamespace(GVSPAdjustPacketSize=adjust,
                                 GVSPPacketSize=Mock())
        self.device.camera.get_streams.return_value = [stream]
        self.device.get_ready()
        adjust.run.assert_not_called()
        stream.GVSPPacketSize.set.assert_not_called()
        self.device.camera.start_streaming.assert_called_once_with(
            self.device.handler_one_by_one)

    def test_non_gige_stream_needs_no_adjustment(self):
        self.device.camera.get_streams.return_value = [SimpleNamespace()]
        self.device.get_ready()
        self.device.camera.start_streaming.assert_called_once()

    def test_adjust_packet_size_on_demand(self):
        stream = SimpleNamespace(
            GVSPAdjustPacketSize=Mock(), GVSPPacketSize=Mock())
        stream.GVSPAdjustPacketSize.is_done.side_effect = [False, True]
        stream.GVSPPacketSize.get.return_value = 1500
        self.device.camera.get_streams.return_value = [stream]
        self.device.adjust_packet_size()
        stream.GVSPAdjustPacketSize.run.assert_called_once()
        self.namespace['sleep'].assert_called_once_with(0.01)
        self.device.logger.info.assert_called_with(
            'GigE stream packet size: 1500 bytes')
        self.device.camera.start_streaming.assert_not_called()

    def test_adjust_packet_size_resumes_active_stream(self):
        stream = SimpleNamespace(
            GVSPAdjustPacketSize=Mock(), GVSPPacketSize=Mock())
        self.device.camera.get_streams.return_value = [stream]
        self.device.camera.is_streaming.side_effect = [True, False]
        calls = Mock()
        calls.attach_mock(self.device.camera.stop_streaming, 'stop')
        calls.attach_mock(stream.GVSPAdjustPacketSize.run, 'adjust')
        calls.attach_mock(self.device.camera.start_streaming, 'start')
        self.device.adjust_packet_size()
        self.assertEqual([call[0] for call in calls.mock_calls], [
                         'stop', 'adjust', 'start'])

    def test_adjust_packet_size_timeout_leaves_stream_stopped(self):
        stream = SimpleNamespace(GVSPAdjustPacketSize=Mock())
        stream.GVSPAdjustPacketSize.is_done.return_value = False
        self.device.camera.get_streams.return_value = [stream]
        self.device.camera.is_streaming.return_value = True
        self.namespace['monotonic'] = Mock(side_effect=[0, 11])
        with self.assertRaises(TimeoutError):
            self.device.adjust_packet_size()
        self.device.camera.stop_streaming.assert_called_once()
        self.device.camera.start_streaming.assert_not_called()

    def test_adjust_packet_size_unsupported_does_not_stop_stream(self):
        for streams in ([], [SimpleNamespace()]):
            with self.subTest(streams=streams):
                self.device.camera.get_streams.return_value = streams
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    self.device.adjust_packet_size()
        self.device.camera.stop_streaming.assert_not_called()

    def test_adjust_packet_size_failure_is_propagated(self):
        adjust = Mock()
        adjust.run.side_effect = RuntimeError('Transport failure')
        self.device.camera.get_streams.return_value = [
            SimpleNamespace(GVSPAdjustPacketSize=adjust)]
        with self.assertRaisesRegex(RuntimeError, 'Transport failure'):
            self.device.adjust_packet_size()
        self.device.camera.start_streaming.assert_not_called()

    def test_packet_size_reads_stream_without_changing_it(self):
        stream = SimpleNamespace(
            GVSPPacketSize=Mock(), GVSPAdjustPacketSize=Mock())
        self.device.camera.get_streams.return_value = [stream]
        for size in (1500, 8228):
            with self.subTest(size=size):
                stream.GVSPPacketSize.get.return_value = size
                self.assertEqual(self.device.read_packet_size(), size)
        stream.GVSPPacketSize.set.assert_not_called()
        stream.GVSPAdjustPacketSize.run.assert_not_called()
        self.device.camera.GevSCPSPacketSize.get.assert_not_called()

    def test_packet_size_unavailable_on_unsupported_transport(self):
        for streams in ([], [SimpleNamespace()]):
            with self.subTest(streams=streams):
                self.device.camera.get_streams.return_value = streams
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    self.device.read_packet_size()
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    self.device.write_packet_size(1500)

    def test_packet_size_write_while_stopped(self):
        stream = SimpleNamespace(
            GVSPPacketSize=Mock(), GVSPAdjustPacketSize=Mock())
        self.device.camera.get_streams.return_value = [stream]
        self.device.write_packet_size(1500)
        stream.GVSPPacketSize.set.assert_called_once_with(1500)
        self.device.camera.stop_streaming.assert_not_called()
        self.device.camera.start_streaming.assert_not_called()
        stream.GVSPAdjustPacketSize.run.assert_not_called()

    def test_packet_size_write_pauses_then_resumes_streaming(self):
        feature = Mock()
        self.device.camera.get_streams.return_value = [
            SimpleNamespace(GVSPPacketSize=feature)]
        self.device.camera.is_streaming.side_effect = [True, False]
        calls = Mock()
        calls.attach_mock(self.device.camera.stop_streaming, 'stop')
        calls.attach_mock(feature.set, 'set')
        calls.attach_mock(self.device.camera.start_streaming, 'start')
        self.device.write_packet_size(1500)
        self.assertEqual([call[0] for call in calls.mock_calls],
                         ['stop', 'set', 'start'])
        feature.set.assert_called_once_with(1500)

    def test_packet_size_write_rejection_is_propagated(self):
        feature = Mock()
        feature.set.side_effect = ValueError('Out of range')
        self.device.camera.get_streams.return_value = [
            SimpleNamespace(GVSPPacketSize=feature)]
        with self.assertRaisesRegex(ValueError, 'Out of range'):
            self.device.write_packet_size(-1)
        self.device.camera.start_streaming.assert_not_called()

    def test_packet_size_read_failure_is_not_hidden(self):
        feature = Mock()
        feature.get.side_effect = RuntimeError('Device disconnected')
        self.device.camera.get_streams.return_value = [
            SimpleNamespace(GVSPPacketSize=feature)]
        with self.assertRaisesRegex(RuntimeError, 'Device disconnected'):
            self.device.read_packet_size()

    def test_triggered_frame_is_owned_and_published(self):
        frame = self.frame()
        self.device.handler_one_by_one(self.device.camera, None, frame)
        frame.as_numpy_ndarray.return_value.fill(99)
        self.assertTrue(self.device.read_is_new_image())
        np.testing.assert_array_equal(self.device.read_image(),
                                      np.ones((3, 4), dtype=np.uint16))
        self.assertEqual(self.device._image_number, 1)
        self.device.push_change_event.assert_called_once()
        self.device.camera.queue_frame.assert_called_once_with(frame)
        self.assertFalse(self.device.read_is_new_image())

    def test_live_frame_is_owned(self):
        frame = self.frame()
        self.device.handler_last_frame(self.device.camera, None, frame)
        frame.as_numpy_ndarray.return_value.fill(99)
        np.testing.assert_array_equal(self.device.read_image(),
                                      np.ones((3, 4), dtype=np.uint16))

    def test_incomplete_frames_are_logged_and_requeued(self):
        for name in ('handler_one_by_one', 'handler_last_frame'):
            with self.subTest(handler=name):
                self.device.logger.reset_mock()
                cam = Mock()
                frame = self.frame('Incomplete')
                getattr(self.device, name)(cam, None, frame)
                self.device.logger.warning.assert_called_once()
                self.assertIn('Incomplete',
                              self.device.logger.warning.call_args.args[0])
                cam.queue_frame.assert_called_once_with(frame)
                self.assertTrue(self.device.imageq.empty())

    def test_processing_error_still_returns_buffer(self):
        self.device.enable_center_of_mass = True
        self.device.calculate_center_of_mass = Mock(
            side_effect=RuntimeError('Processing failed'))
        for name in ('handler_one_by_one', 'handler_last_frame'):
            with self.subTest(handler=name):
                cam = Mock()
                frame = self.frame()
                with self.assertRaisesRegex(RuntimeError, 'Processing failed'):
                    getattr(self.device, name)(cam, None, frame)
                cam.queue_frame.assert_called_once_with(frame)


if __name__ == '__main__':
    unittest.main()
