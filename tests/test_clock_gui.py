"""Clock GUI wiring tests; no Qt application or Tango database required."""

from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from Clock import clock_GUI


class TestClockGui(unittest.TestCase):
    def test_default_arguments(self):
        with patch.object(clock_GUI, 'create_app', return_value=0) as create_app:
            self.assertEqual(clock_GUI.main([]), 0)
        args = create_app.call_args.args[0]
        self.assertEqual(args.device, 'other/Clock/clock')
        self.assertEqual(args.polling, 100)
        self.assertFalse(args.compact)

    def test_custom_arguments(self):
        with patch.object(clock_GUI, 'create_app') as create_app:
            clock_GUI.main(['test/clock/1', 'test/clock/2',
                           '--polling', '500', '-c'])
        args = create_app.call_args.args[0]
        self.assertEqual(args.device, ['test/clock/1', 'test/clock/2'])
        self.assertEqual(args.polling, 500)
        self.assertTrue(args.compact)

    def test_device_panels(self):
        for devices in ('other/Clock/clock', ['test/clock/1', 'test/clock/2']):
            with self.subTest(devices=devices):
                device_list = devices if isinstance(
                    devices, list) else [devices]
                gui_module = ModuleType('common.GUI')
                gui_base = Mock()
                gui_module.GuiBase = gui_base
                app = gui_base.return_value
                panel, layout = Mock(), Mock()
                app.create_blank_panel.return_value = panel, layout
                app.app.exec_.return_value = 0
                args = SimpleNamespace(
                    device=devices, polling=250, compact=True)

                with patch.dict('sys.modules', {'common.GUI': gui_module}):
                    self.assertEqual(clock_GUI.create_app(args), 0)

                gui_base.assert_called_once_with(
                    device_list, 250, is_form_compact=True)
                self.assertEqual(
                    app.create_form_panel.call_count, len(device_list))
                for device in device_list:
                    app.add_device.assert_any_call(device)
                    app.gui.createPanel.assert_any_call(
                        panel, f'{device}_clock')
                    app.create_form_panel.assert_any_call(
                        layout, device,
                        include=['time', 'host_computer', 'state', 'status'],
                        withButtons=False,
                        set_attr_font={
                            'time': {'font': 'Monospace', 'size': 24}},
                    )
                app.gui.removePanel.assert_called_once_with('Manual')
                app.gui.show.assert_called_once_with()
                app.app.exec_.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
