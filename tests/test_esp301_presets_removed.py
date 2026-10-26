"""Offline ESP301 regression tests; never import Tango, Qt, or device modules."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from common.axis_order import get_axis_order


ROOT = Path(__file__).resolve().parents[1]
REMOVED = ('current_location', 'saved_location_source', 'user_defined_locations',
           'load_server_side_list', 'is_position_close')


def load_functions(filename, namespace, class_name=None, names=None):
    path = ROOT / 'ESP301' / filename
    tree = ast.parse(path.read_text(encoding='utf-8'))
    if class_name:
        tree = next(node for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == class_name)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and (names is None or node.name in names)]
    for node in functions:
        node.decorator_list = []
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'),
         namespace)
    return namespace


class TestPresetRemoval(unittest.TestCase):
    def test_server_and_gui_have_no_generic_preset_dependencies(self):
        for filename in ('server.py', 'GUI.py'):
            source = (ROOT / 'ESP301' / filename).read_text(encoding='utf-8')
            for name in REMOVED:
                with self.subTest(file=filename, symbol=name):
                    self.assertNotIn(name, source)
            self.assertNotIn('locations.txt', source)

    def test_no_runtime_location_files_remain(self):
        self.assertEqual(list((ROOT / 'ESP301').glob('*locations.txt')), [])

    def test_gui_startup_without_preset_api_or_file_access(self):
        for grating, turning_box in ((False, False), (True, False), (False, True)):
            with self.subTest(grating=grating, turning_box=turning_box):
                name = ('laser/esp300/esp300_turning_box3' if turning_box
                        else 'test/esp301/test')
                proxy = Mock(spec_set=['info', 'get_property'])
                proxy.info.return_value = SimpleNamespace(dev_class='ESP301')
                properties = {
                    'axis_property': ['1,2,3'], 'axis_order': ['3,1,2'],
                    'use_grating_config': [str(grating)],
                }
                proxy.get_property.side_effect = lambda keys: {
                    key: properties.get(key, [])
                    for key in ([keys] if isinstance(keys, str) else keys)
                }
                app = Mock()
                app.attr_list = {name: {
                    'dp': proxy,
                    'attrs': [f'ax{axis}_{suffix}' for axis in (1, 2, 3)
                              for suffix in ('position', 'step')],
                }}
                app.create_blank_panel.side_effect = [
                    (f'panel{i}', f'layout{i}') for i in range(3)
                ]
                forbidden_open = Mock(
                    side_effect=AssertionError('Unexpected file I/O'))
                namespace = load_functions('GUI.py', {
                    '__file__': str(ROOT / 'ESP301' / 'GUI.py'),
                    'args': SimpleNamespace(device=[name], polling=1000),
                    'GuiBase': Mock(return_value=app),
                    'tango': SimpleNamespace(DeviceProxy=Mock(return_value=proxy)),
                    'get_axis_order': get_axis_order,
                    'mymotor_read_only_item_factory': object(),
                    'open': forbidden_open,
                }, names={'get_device_property', 'get_boolean_device_property',
                          'create_app'})
                namespace['create_app']()
                forbidden_open.assert_not_called()
                app.gui.show.assert_called_once_with()
                app.tile_device_panels.assert_called_once_with()
                app.app.exec_.assert_called_once_with()
                forms = app.create_form_panel.call_args_list
                self.assertEqual(len(forms), 2 if grating else 1)
                self.assertEqual(app.create_blank_panel.call_count, len(forms))
                panels = [invocation.args for invocation in
                          app.gui.createPanel.call_args_list]
                self.assertEqual(panels, [('panel0', name)] +
                                 ([('panel1', f'{name}_minimum')] if grating else []))
                for form in forms:
                    self.assertTrue(set(REMOVED).isdisjoint(
                        form.kwargs['include']))
                    self.assertNotIn('dropdown', form.kwargs)
                less = forms[0].kwargs['include']
                self.assertEqual(less[:6], [
                    'ax3_position', 'set_ax3_as',
                    'ax1_position', 'set_ax1_as',
                    'ax2_position', 'set_ax2_as',
                ])
                self.assertEqual(forms[0].args, ('layout0', name))
                self.assertEqual(less[-4:],
                                 ['host_computer', 'raw_command', 'status', 'state'])
                self.assertIn('customized_location', less)
                self.assertEqual([attr for attr in less if attr.endswith('_position')],
                                 ['ax3_position', 'ax1_position', 'ax2_position'])
                self.assertEqual('ax12_distance' in less, grating)
                if grating:
                    minimum = forms[1].kwargs
                    self.assertEqual(minimum['include'][:3],
                                     ['ax3_position', 'ax1_position', 'ax2_position'])
                    self.assertFalse(any(attr.startswith('set_ax')
                                         for attr in minimum['include']))
                    self.assertIn('item_factories', minimum)
                commands = [cmd for invocation in app.add_command.call_args_list
                            for cmd in invocation.kwargs['command_list']]
                self.assertIn('stop', commands)
                self.assertEqual('reset_to_TA1' in commands, turning_box)
                main_calls = [invocation for invocation in
                              app.add_command.call_args_list
                              if invocation.args[0] == 'layout0']
                main_commands = [cmd for invocation in main_calls
                                 for cmd in invocation.kwargs['command_list']]
                self.assertEqual(main_commands.count('Init'), 1)
                self.assertEqual(main_commands.count('stop'), 1)
                for command in ('move_to_negative_limit',
                                'move_to_positive_limit', 'set_as_zero'):
                    self.assertEqual(main_commands.count(command), 3)
                self.assertEqual('reset_to_TA1' in main_commands, turning_box)
                axis_calls = [invocation for invocation in main_calls
                              if 'cmd_parameters' in invocation.kwargs]
                self.assertEqual([invocation.kwargs['cmd_parameters']
                                  for invocation in axis_calls],
                                 [[[3]] * 3, [[1]] * 3, [[2]] * 3])
                if grating:
                    self.assertEqual(forms[1].args, ('layout1', name))
                    minimum_commands = [cmd for invocation in
                                        app.add_command.call_args_list
                                        if invocation.args[0] == 'layout1'
                                        for cmd in invocation.kwargs['command_list']]
                    self.assertEqual(minimum_commands, ['Init', 'stop'])


class TestTurningBoxPreserved(unittest.TestCase):
    def test_dynamic_initialization_keeps_motion_attributes_and_commands(self):
        namespace = load_functions('server.py', {
            'attribute': lambda **kwargs: SimpleNamespace(**kwargs),
            'command': lambda f, **kwargs: f,
            'AttrWriteType': SimpleNamespace(READ_WRITE='rw', READ='r'),
        }, 'ESP301', {'initialize_dynamic_attributes'})
        for turning_box, grating in ((False, False), (True, False), (False, True)):
            with self.subTest(turning_box=turning_box, grating=grating):
                device = Mock()
                device.axis = [1, 2, 3]
                device.use_turning_box_3_config = turning_box
                device.use_grating_config = grating
                device._axis1_unit = 'mm'
                for factory, prefix in (
                    ('create_position_attribute', 'position'),
                    ('create_set_as_attribute', 'set_as'),
                    ('create_ax_step_attribute', 'step'),
                    ('create_ax_status', 'status'),
                ):
                    getattr(device, factory).side_effect = (
                        lambda axis, prefix=prefix: SimpleNamespace(
                            name=f'{prefix}{axis}')
                    )
                namespace['initialize_dynamic_attributes'](device)
                device.remove_attribute.assert_not_called()
                attrs = [invocation.args[0].name
                         for invocation in device.add_attribute.call_args_list]
                for axis in device.axis:
                    for prefix in ('position', 'set_as', 'step', 'status'):
                        self.assertIn(f'{prefix}{axis}', attrs)
                self.assertEqual('customized_location' in attrs, turning_box)
                self.assertEqual('ax12_distance' in attrs, grating)
                self.assertEqual('ax12_step' in attrs, grating)
                registered = [invocation.args[0]
                              for invocation in device.add_command.call_args_list]
                self.assertEqual(
                    device.reset_to_TA1 in registered, turning_box)
                if turning_box:
                    self.assertEqual(device.TA1, [0, 135])
                    self.assertEqual(device.TA2, [89, 0])
                    self.assertEqual(device.TA3, [101, 90])
                    self.assertEqual(
                        device.TA2_to_TA3_intermediate, [41, None])

    def test_all_turning_box_transitions_keep_order_and_stop_checks(self):
        namespace = load_functions('server.py', {}, 'ESP301',
                                   {'threaded_write_customized_location'})
        transitions = {
            ('TA1', 'TA2'): [('axis2', 0), ('wait', 2, 0), ('axis1', 89)],
            ('TA1', 'TA3'): [('axis2', 90), ('wait', 2, 90), ('axis1', 101)],
            ('TA2', 'TA1'): [('axis1', 0), ('wait', 1, 0), ('axis2', 135)],
            ('TA3', 'TA1'): [('axis1', 0), ('wait', 1, 0), ('axis2', 135)],
            ('TA3', 'TA2'): [('axis1', 41), ('wait', 1, 41), ('axis2', 0),
                             ('wait', 2, 0), ('axis1', 89)],
            ('TA2', 'TA3'): [('axis1', 41), ('wait', 1, 41), ('axis2', 90),
                             ('wait', 2, 90), ('axis1', 101)],
        }
        for (start, end), expected in transitions.items():
            # Stop after each wait in turn, as well as exercise normal completion.
            stops = [None] + [i for i,
                              step in enumerate(expected) if step[0] == 'wait']
            for stop_at in stops:
                with self.subTest(start=start, end=end, stop_at=stop_at):
                    device = SimpleNamespace(
                        _customized_location=start, should_stop=False,
                        TA1=[0, 135], TA2=[89, 0], TA3=[101, 90],
                        TA2_to_TA3_intermediate=[41, None],
                    )
                    events = []
                    device.write_ax1_position = lambda self, value: events.append(
                        ('axis1', value))
                    device.write_ax2_position = lambda self, value: events.append(
                        ('axis2', value))

                    def wait(axis, target):
                        events.append(('wait', axis, target))
                        device.should_stop = len(events) - 1 == stop_at

                    device.wait_until_arrive = wait
                    attr = Mock()
                    attr.get_write_value.return_value = end
                    namespace['threaded_write_customized_location'](
                        device, attr)
                    self.assertEqual(events, expected if stop_at is None
                                     else expected[:stop_at + 1])


if __name__ == '__main__':
    unittest.main()
