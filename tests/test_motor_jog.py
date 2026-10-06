import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call


def load_methods(relative_path, class_name, method_names):
    """Load only selected methods, without importing or starting device modules."""
    path = Path(__file__).resolve().parents[1] / relative_path
    tree = ast.parse(path.read_text(encoding='utf-8'))
    source_class = next(node for node in tree.body
                        if isinstance(node, ast.ClassDef) and node.name == class_name)
    methods = [node for node in source_class.body
               if isinstance(node, ast.FunctionDef) and node.name in method_names]
    for method in methods:
        method.decorator_list = []
    namespace = {'math': math}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in method_names})


ESP301 = load_methods('ESP301/server.py', 'ESP301',
                      ('_jog_axes', 'jog_axis', 'jog_grating'))


class TestESP301Jog(unittest.TestCase):
    def make_device(self, replies):
        device = SimpleNamespace(
            axis=[1, 2, 3],
            use_grating_config=True,
            dev_write=Mock(),
            dev_read=Mock(side_effect=replies),
            _error_message='previous error',
            should_stop=True,
        )
        device._jog_axes = lambda axes, step: ESP301._jog_axes(device, axes, step)
        return device

    def test_fast_second_single_axis_jog_is_ignored(self):
        device = self.make_device(['1', '10.0', '0'])
        self.assertTrue(ESP301.jog_axis(device, [1, -0.1]))
        self.assertFalse(ESP301.jog_axis(device, [1, -0.1]))
        self.assertEqual(device.dev_write.call_args_list, [
            call(b'1MD?\r'), call(b'1TP\r'), call(b'1PA9.900\r'),
            call(b'1MD?\r'),
        ])

    def test_grating_waits_for_both_axes_then_accepts_next_jog(self):
        device = self.make_device([
            '1', '1', '10.0', '20.0',
            '1', '0',
            '1', '1', '9.9', '19.9',
        ])
        self.assertTrue(ESP301.jog_grating(device, -0.1))
        self.assertFalse(ESP301.jog_grating(device, -0.1))
        self.assertTrue(ESP301.jog_grating(device, -0.1))
        self.assertEqual(device.dev_write.call_args_list, [
            call(b'1MD?\r'), call(b'2MD?\r'),
            call(b'1TP\r'), call(b'2TP\r'), call(b'1PA9.900;2PA19.900\r'),
            call(b'1MD?\r'), call(b'2MD?\r'),
            call(b'1MD?\r'), call(b'2MD?\r'),
            call(b'1TP\r'), call(b'2TP\r'), call(b'1PA9.800;2PA19.800\r'),
        ])

    def test_first_axis_busy_prevents_both_moves(self):
        device = self.make_device(['0'])
        self.assertFalse(ESP301.jog_grating(device, 0.1))
        device.dev_write.assert_called_once_with(b'1MD?\r')
        self.assertEqual(device._error_message, 'previous error')
        self.assertTrue(device.should_stop)

    def test_invalid_status_fails_closed(self):
        for reply in ('', 'garbage', '2'):
            with self.subTest(reply=reply):
                device = self.make_device(['1', reply])
                with self.assertRaises(RuntimeError):
                    ESP301.jog_grating(device, 0.1)
                self.assertEqual(device.dev_write.call_count, 2)

    def test_failed_second_position_read_sends_no_move(self):
        device = self.make_device(['1', '1', '10', 'invalid'])
        with self.assertRaises(ValueError):
            ESP301.jog_grating(device, 0.1)
        self.assertEqual(device.dev_write.call_count, 4)

    def test_invalid_steps_send_no_commands(self):
        for step in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(step=step):
                device = self.make_device([])
                with self.assertRaises(ValueError):
                    ESP301.jog_axis(device, [1, step])
                device.dev_write.assert_not_called()

    def test_invalid_axis_sends_no_commands(self):
        for values in ([1.5, 0.1], [4, 0.1], [1], []):
            with self.subTest(values=values):
                device = self.make_device([])
                with self.assertRaises(ValueError):
                    ESP301.jog_axis(device, values)
                device.dev_write.assert_not_called()

    def test_grating_requires_configured_pair(self):
        device = self.make_device([])
        device.axis = [1]
        with self.assertRaises(ValueError):
            ESP301.jog_grating(device, 0.1)
        device.dev_write.assert_not_called()

    def test_grating_requires_grating_configuration(self):
        device = self.make_device([])
        device.use_grating_config = False
        with self.assertRaises(ValueError):
            ESP301.jog_grating(device, 0.1)
        device.dev_write.assert_not_called()


class TestNewmarkJog(unittest.TestCase):
    methods = load_methods('Newmark/server.py', 'Newmark', (
        'is_motion_done', 'jog_axis', 'move_absolute_if_idle',
        '_read_axis_position', '_write_axis_position',
    ))

    def make_device(self, replies):
        device = SimpleNamespace(
            _send_command=Mock(side_effect=replies),
            _steps_to_position=lambda steps: steps / 12500,
            _position_to_steps=lambda position: round(position * 12500),
        )
        for name, method in vars(self.methods).items():
            setattr(device, name, lambda *args, method=method: method(device, *args))
        return device

    def test_fast_second_click_is_discarded(self):
        device = self.make_device(['0', '125000', '0', 'OK', 'OK', '1'])
        self.assertTrue(device.jog_axis([1, -0.1]))
        self.assertFalse(device.jog_axis([1, -0.1]))
        self.assertEqual(device._send_command.call_args_list, [
            call('MST'), call('PX'), call('MST'), call('ABS'), call('X123750'),
            call('MST'),
        ])

    def test_all_motion_phases_inhibit_moves(self):
        for status in range(1, 8):
            with self.subTest(status=status):
                device = self.make_device([str(status)])
                self.assertFalse(device.jog_axis([1, 0.1]))
                device._send_command.assert_called_once_with('MST')

    def test_idle_input_bits_are_not_motion(self):
        for status in (0, 8, 16, 32, 256, 512):
            with self.subTest(status=status):
                self.assertTrue(self.make_device([str(status)]).is_motion_done())

    def test_invalid_status_or_fault_cannot_move(self):
        for reply in ('', '?', '-1', '2048', '64', '128', '1024'):
            with self.subTest(reply=reply):
                device = self.make_device([reply])
                with self.assertRaises((ValueError, RuntimeError)):
                    device.jog_axis([1, 0.1])
                device._send_command.assert_called_once_with('MST')

    def test_pair_target_rechecks_busy_state(self):
        device = self.make_device(['2'])
        self.assertFalse(device.move_absolute_if_idle(10.1))
        device._send_command.assert_called_once_with('MST')

    def test_motion_starting_after_position_read_prevents_jog(self):
        device = self.make_device(['0', '125000', '4'])
        self.assertFalse(device.jog_axis([1, 0.1]))
        self.assertEqual(device._send_command.call_args_list,
                         [call('MST'), call('PX'), call('MST')])

    def test_invalid_arguments_send_no_commands(self):
        for values in ([2, 0.1], [1.5, 0.1], [1], [1, float('nan')], [1, float('inf')]):
            with self.subTest(values=values):
                device = self.make_device([])
                with self.assertRaises(ValueError):
                    device.jog_axis(values)
                device._send_command.assert_not_called()

    def test_invalid_pair_target_sends_no_commands(self):
        device = self.make_device([])
        with self.assertRaises(ValueError):
            device.move_absolute_if_idle(float('nan'))
        device._send_command.assert_not_called()


class TestMotorJogWidgets(unittest.TestCase):
    motor = load_methods('common/my_motor_widget.py', 'MyMotorWriteWidget', ('_move',))
    grating = load_methods('common/my_motor_widget.py', 'MyGratingWriteWidget', ('_move',))

    def make_widget(self, device_class='ESP301'):
        model = Mock()
        model.name = 'ax1_position'
        device = model.getParentObj.return_value.getDeviceProxy.return_value
        device.info.return_value.dev_class = device_class
        widget = Mock()
        widget.getModelObj.return_value = model
        widget.step.text.return_value = '0.1'
        return widget, model, device

    def test_motor_sends_signed_step_without_client_position_read(self):
        for device_class in ('ESP301', 'Newmark'):
            for sign in (-1, 1):
                with self.subTest(device_class=device_class, sign=sign):
                    widget, model, device = self.make_widget(device_class)
                    self.motor._move(widget, sign)
                    device.jog_axis.assert_called_once_with([1, sign * 0.1])
                    model.read.assert_not_called()
                    model.write.assert_not_called()

    def test_grating_sends_one_paired_command(self):
        widget, model, device = self.make_widget()
        self.grating._move(widget, -1)
        device.jog_grating.assert_called_once_with(-0.1)
        model.getParentObj.return_value.getAttribute.assert_not_called()

    def test_busy_response_does_not_fall_back_to_absolute_writes(self):
        for handler, command_name in ((self.motor, 'jog_axis'),
                                      (self.grating, 'jog_grating')):
            with self.subTest(command=command_name):
                widget, model, device = self.make_widget()
                getattr(device, command_name).return_value = False
                handler._move(widget, -1)
                model.read.assert_not_called()
                model.write.assert_not_called()
                model.getParentObj.return_value.getAttribute.assert_not_called()

    def test_command_failure_does_not_fall_back_to_absolute_writes(self):
        for handler, command_name in ((self.motor, 'jog_axis'),
                                      (self.grating, 'jog_grating')):
            with self.subTest(command=command_name):
                widget, model, device = self.make_widget()
                getattr(device, command_name).side_effect = RuntimeError('unavailable')
                handler._move(widget, -1)
                widget.warning.assert_called_once()
                model.read.assert_not_called()
                model.write.assert_not_called()
                model.getParentObj.return_value.getAttribute.assert_not_called()

    def test_other_motor_backends_keep_existing_behavior(self):
        for device_class in ('Owis', 'NewPortXPS'):
            with self.subTest(device_class=device_class):
                widget, model, device = self.make_widget(device_class)
                model.read.return_value.rvalue = SimpleNamespace(magnitude=10)
                self.motor._move(widget, -1)
                device.jog_axis.assert_not_called()
                model.write.assert_called_once_with(9.9)

    def test_newmark_busy_or_missing_command_never_falls_back(self):
        for error in (None, RuntimeError('old server')):
            with self.subTest(error=error):
                widget, model, device = self.make_widget('Newmark')
                device.jog_axis.return_value = False
                device.jog_axis.side_effect = error
                self.motor._move(widget, -1)
                model.read.assert_not_called()
                model.write.assert_not_called()

    def test_empty_step_sends_no_move(self):
        for handler in (self.motor, self.grating):
            widget, model, device = self.make_widget()
            widget.step.text.return_value = ''
            handler._move(widget, -1)
            device.jog_axis.assert_not_called()
            device.jog_grating.assert_not_called()
            model.write.assert_not_called()


if __name__ == '__main__':
    unittest.main()