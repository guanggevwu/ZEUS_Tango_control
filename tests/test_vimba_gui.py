"""Test GUI assembly and real argument parsing without Qt or camera access."""

import ast
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from common.TaurusGUI_Argparse import TaurusArgparse


class TestVimbaGui(unittest.TestCase):
    def create_gui(self, arguments, groups=None):
        path = Path(__file__).resolve().parents[1] / 'Vimba' / 'GUI.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'create_app')
        app = Mock()
        app.create_blank_panel.side_effect = lambda *args: (Mock(), Mock())
        namespace = {
            'TaurusArgparse': TaurusArgparse, 'GuiBase': Mock(return_value=app),
            'device_name_table': groups or {}, 'image_panel_config': {},
            'os': __import__('os'), '__file__': str(path),
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(
            path), 'exec'), namespace)
        with patch.object(sys, 'argv', ['GUI.py', *arguments]):
            namespace['create_app']()
        return app

    def assert_single_device_layout(self, app, device):
        self.assertEqual([call.args[1] for call in app.gui.createPanel.call_args_list],
                         [device, f'{device}_form'])
        app.combined_panel.assert_not_called()
        app.tile_panels_with_stacked_panels.assert_not_called()
        image_call = app.create_image_panel.call_args
        commands_call = app.add_command.call_args
        self.assertIs(image_call.args[0], commands_call.args[0])
        self.assertIn('adjust_packet_size',
                      commands_call.kwargs['command_list'])
        self.assertNotIn('Init', commands_call.kwargs['command_list'])
        self.assertEqual(len(commands_call.kwargs['command_list']),
                         len(commands_call.kwargs['cmd_parameters']))
        self.assertNotEqual(image_call.kwargs.get('image_number'), False)

    def test_single_camera_commands_share_image_panel(self):
        device = 'TA1/vimba/50-0503570200'
        self.assert_single_device_layout(self.create_gui([device]), device)

    def test_default_camera_uses_single_layout(self):
        self.assert_single_device_layout(
            self.create_gui([]), 'TA2/vimba/TA2-1')

    def test_single_camera_combination_does_not_add_combined_panel(self):
        device = 'TA1/vimba/50-0503570200'
        app = self.create_gui(['test_combination'], {
                              'test_combination': [device]})
        self.assert_single_device_layout(app, device)

    def test_multiple_cameras_tile_like_basler(self):
        devices = ['TA1/vimba/one', 'TA1/vimba/two']
        app = self.create_gui(devices)
        app.combined_panel.assert_called_once_with(devices)
        app.tile_panels_with_stacked_panels.assert_called_once_with(
            devices, [f'{device}_form' for device in devices] + ['2 devices', 'Manual'])
        self.assertEqual(app.add_command.call_count, 2)

    def test_large_combination_uses_resolved_device_count(self):
        devices = [f'TA1/vimba/{number}' for number in range(4)]
        app = self.create_gui(['test_combination'], {
                              'test_combination': devices})
        app.add_command.assert_not_called()
        for call in app.create_image_panel.call_args_list:
            self.assertFalse(call.kwargs['image_number'])
        app.combined_panel.assert_called_once_with(
            devices, combine_form_with_onshot=False)


if __name__ == '__main__':
    unittest.main()
