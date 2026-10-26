"""Device-grouped docking with real Qt docks and no device connections."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from taurus.external.qt import Qt


path = Path(__file__).resolve().parents[1] / 'common' / 'GUI.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
cls = next(node for node in tree.body
           if isinstance(node, ast.ClassDef) and node.name == 'GuiBase')
method = next(node for node in cls.body
              if isinstance(node, ast.FunctionDef) and node.name == 'tile_device_panels')
namespace = {'Qt': Qt}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(
    path), 'exec'), namespace)
tile_device_panels = namespace['tile_device_panels']


class TestDevicePanelLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Qt.QApplication.instance() or Qt.QApplication([])

    def settle(self):
        for _ in range(5):
            self.app.processEvents()

    def make_window(self, groups):
        window = Qt.QMainWindow()
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        panels = {}
        for names in groups:
            for name in names:
                dock = Qt.QDockWidget(name, window)
                dock.setObjectName(name)
                dock.setWidget(Qt.QLabel(name))
                window.addDockWidget(
                    Qt.Qt.DockWidgetArea.TopDockWidgetArea, dock)
                if panels:
                    window.tabifyDockWidget(next(iter(panels.values())), dock)
                panels[name] = dock
        window.getPanelNames = lambda: list(panels)
        window.getPanel = panels.__getitem__
        window.resize(1200, 800)
        window.show()
        self.settle()
        return window, panels

    def test_device_groups_are_separate_and_own_panels_remain_tabbed(self):
        for count in (2, 4, 5):
            with self.subTest(count=count):
                devices = [f'test/motor/{index}' for index in range(count)]
                groups = [[f'{device}_more', f'{device}_less', f'{device}_minimum']
                          for device in devices]
                window, panels = self.make_window(groups)
                owner = SimpleNamespace(
                    gui=window, attr_list=dict.fromkeys(devices))
                # Reapplying should not reunite distinct groups.
                for _ in range(2):
                    tile_device_panels(owner)
                    self.settle()
                    visible_rects = []
                    for device, names in zip(devices, groups):
                        primary = panels[f'{device}_less']
                        self.assertEqual(set(window.tabifiedDockWidgets(primary)),
                                         {panels[name] for name in names if name != f'{device}_less'})
                        self.assertGreater(
                            primary.visibleRegion().boundingRect().width(), 0)
                        visible_rects.append(primary.geometry())
                    for i, rect in enumerate(visible_rects):
                        for other in visible_rects[i + 1:]:
                            self.assertFalse(rect.intersects(other))
                window.close()

    def test_prefix_names_use_longest_device_match(self):
        devices = ['test/motor/a', 'test/motor/a_extra']
        groups = [[devices[0], devices[0] + '_minimum'],
                  [devices[1], devices[1] + '_minimum']]
        window, panels = self.make_window(groups)
        result = tile_device_panels(SimpleNamespace(
            gui=window, attr_list=dict.fromkeys(devices)))
        self.assertEqual(result, groups)
        self.assertEqual(window.tabifiedDockWidgets(panels[devices[0]]),
                         [panels[devices[0] + '_minimum']])

    def test_single_device_and_unmatched_panels_are_not_rearranged(self):
        gui = Mock()
        gui.getPanelNames.return_value = [
            'test/motor/1_more', 'test/motor/1_less', 'Manual']
        result = tile_device_panels(SimpleNamespace(
            gui=gui, attr_list={'test/motor/1': {}}))
        self.assertEqual(len(result), 1)
        gui.removeDockWidget.assert_not_called()
        gui.getPanel.assert_not_called()

    def test_logical_pair_group_and_unmatched_summary(self):
        gui = Mock()
        gui.getPanelNames.return_value = [
            'pair_more', 'pair_less', 'other_form', 'summary']
        panels = {name: Mock() for name in gui.getPanelNames.return_value}
        gui.getPanel.side_effect = panels.__getitem__
        result = tile_device_panels(SimpleNamespace(gui=gui), [
                                    'pair', 'pair', 'other'])
        self.assertEqual(result, [['pair_more', 'pair_less'], ['other_form']])
        self.assertNotIn(panels['summary'],
                         [entry.args[0] for entry in gui.removeDockWidget.call_args_list])


if __name__ == '__main__':
    unittest.main()
