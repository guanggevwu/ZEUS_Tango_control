import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from common.axis_order import get_axis_order


class TestNewportAxisOrder(unittest.TestCase):
    def get_order(self, properties, attributes=()):
        device = Mock()
        device.get_property.return_value = properties
        result = get_axis_order(device, attributes)
        device.get_property.assert_called_once_with(['axis_property', 'axis_order'])
        return result

    def test_custom_order(self):
        self.assertEqual(self.get_order({
            'axis_property': ['1,2,3'], 'axis_order': ['3, 1, 2'],
        }), [3, 1, 2])

    def test_empty_order_sorts_configured_axes(self):
        for empty in ([], [''], ['   ']):
            with self.subTest(empty=empty):
                self.assertEqual(self.get_order({
                    'axis_property': ['8, 2, 5'], 'axis_order': empty,
                }), [2, 5, 8])

    def test_missing_order_uses_numeric_order(self):
        self.assertEqual(self.get_order({'axis_property': ['3,1']}), [1, 3])

    def test_detected_axes_used_when_axis_property_is_empty(self):
        attributes = ['ax3_position', 'ax1_position', 'ax1_step', 'ax12_distance', 'set_ax1_as']
        self.assertEqual(self.get_order({}, attributes), [1, 3])
        self.assertEqual(self.get_order({
            'axis_property': [''], 'axis_order': ['3, 1'],
        }, attributes), [3, 1])

    def test_property_array_values(self):
        self.assertEqual(self.get_order({
            'axis_property': ['1', '2', '3'], 'axis_order': ['2', '3', '1'],
        }), [2, 3, 1])

    def test_invalid_order_is_rejected(self):
        for order in ('1,1,2', '1,2', '1,2,4', '1,2,three', '1,2,3,'):
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    self.get_order({'axis_property': ['1,2,3'], 'axis_order': [order]})

    def test_gui_forms_and_command_parameters_follow_order(self):
        root = Path(__file__).resolve().parents[1]
        for folder, app_name, order_name in (
            ('ESP301', 'esp_app', 'axis_order'),
            ('NewPortXPS', 'newport_xps_app', 'available_axis'),
        ):
            with self.subTest(gui=folder):
                path = root / folder / 'GUI.py'
                tree = ast.parse(path.read_text(encoding='utf-8'))
                statements = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id in
                        (order_name, 'less_list', 'command_with_axis_parameters')
                        for target in node.targets
                    ):
                        statements.append(node)
                    if isinstance(node, ast.For):
                        if isinstance(node.iter, ast.Name) and node.iter.id == order_name:
                            statements.append(node)
                        elif isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'enumerate':
                            statements.append(node)
                statements.sort(key=lambda node: node.lineno)
                device = Mock()
                device.get_property.return_value = {
                    'axis_property': ['1,2,3'], 'axis_order': ['3, 1, 2'],
                }
                app = SimpleNamespace(attr_list={'test/device/1': {
                    'dp': device,
                    'attrs': [f'ax{axis}_{suffix}' for axis in (1, 2, 3)
                              for suffix in ('position', 'step')],
                }})
                values = {
                    'get_axis_order': get_axis_order, 'device_proxy': device,
                    'd': 'test/device/1', app_name: app,
                    'command_list': [], 'modified_cmd_name': [], 'cmd_parameters': [],
                }
                exec(compile(ast.Module(body=statements, type_ignores=[]), str(path), 'exec'), values)
                self.assertEqual(values['less_list'][5::2], ['ax3_position', 'ax1_position', 'ax2_position'])
                self.assertEqual(values['less_list'][6::2], ['set_ax3_as', 'set_ax1_as', 'set_ax2_as'])
                self.assertEqual(values['cmd_parameters'], [[[3]] * 3, [[1]] * 3, [[2]] * 3])
                self.assertEqual(values['command_list'], [
                    ['move_to_negative_limit', 'move_to_positive_limit', 'set_as_zero'],
                ] * 3)


if __name__ == '__main__':
    unittest.main()