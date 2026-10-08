import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


source_path = Path(__file__).resolve().parents[1] / 'Owis' / 'GUI.py'
tree = ast.parse(source_path.read_text(encoding='utf-8'))
function = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == 'get_axis_order')
namespace = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), 'exec'), namespace)
get_axis_order = namespace['get_axis_order']


class TestOwisAxisOrder(unittest.TestCase):
    def get_order(self, properties):
        device = Mock()
        device.get_property.return_value = properties
        order = get_axis_order(device)
        device.get_property.assert_called_once_with(['axis', 'axis_order'])
        return order

    def test_custom_comma_separated_order(self):
        self.assertEqual(self.get_order({
            'axis': ['1,2,3,4,5,6,7,8,9'],
            'axis_order': ['1, 3, 7, 6, 4, 5, 8, 2, 9'],
        }), [1, 3, 7, 6, 4, 5, 8, 2, 9])

    def test_empty_order_sorts_only_configured_axes(self):
        for empty in ([], [''], ['   ']):
            with self.subTest(empty=empty):
                self.assertEqual(self.get_order({
                    'axis': ['7, 1, 3'], 'axis_order': empty,
                }), [1, 3, 7])

    def test_missing_order_uses_configured_axes(self):
        self.assertEqual(self.get_order({'axis': ['1,2,3,4']}), [1, 2, 3, 4])

    def test_missing_axis_uses_server_default(self):
        self.assertEqual(self.get_order({}), [1])

    def test_property_array_values(self):
        self.assertEqual(self.get_order({
            'axis': ['1', '2', '3'], 'axis_order': ['3', '1', '2'],
        }), [3, 1, 2])

    def test_invalid_order_is_rejected(self):
        for value in ('1,1,2', '1,2', '1,2,4', '1,2,three', '1,2,3,'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.get_order({'axis': ['1,2,3'], 'axis_order': [value]})

    def test_form_and_commands_use_same_property_order(self):
        assignments = [node for node in ast.walk(tree)
                       if isinstance(node, ast.Assign) and any(
                           isinstance(target, ast.Name) and target.id == 'less_list'
                           for target in node.targets)]
        order = [3, 1, 2]
        values = {'axis_order': order}
        exec(compile(ast.Module(body=assignments, type_ignores=[]), str(source_path), 'exec'), values)
        self.assertEqual(values['less_list'][2::2], ['ax3_position', 'ax1_position', 'ax2_position'])
        self.assertEqual(values['less_list'][3::2], ['set_ax3_as', 'set_ax1_as', 'set_ax2_as'])
        command_loop = next(node for node in ast.walk(tree)
                            if isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                            and node.target.id == 'ax')
        self.assertIsInstance(command_loop.iter, ast.Name)
        self.assertEqual(command_loop.iter.id, 'axis_order')


if __name__ == '__main__':
    unittest.main()