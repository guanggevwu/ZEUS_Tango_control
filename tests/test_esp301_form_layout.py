"""Real Qt/Taurus layout checks using local eval models only (no Tango I/O)."""

import unittest
import ast
from pathlib import Path
from types import SimpleNamespace

from taurus.external.qt import Qt
from taurus.qt.qtgui.panel import TaurusForm

from common.my_motor_widget import MyMotorWriteWidget
from common.taurus_widget import preserve_form_row_heights


class OfflineMotorWriteWidget(MyMotorWriteWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Test layout only: do not derive device/step models from eval models.
        self.modelChanged.disconnect(self._on_model_changed)


class TestSharedFormLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Qt.QApplication.instance() or Qt.QApplication([])

    def make_form(self, composite=False):
        form = TaurusForm(withButtons=False)
        self.addCleanup(form.close)
        self.addCleanup(form.deleteLater)
        form.setModel([f'eval:{i}' for i in range(1, 7)])
        if composite:
            form[1].setWriteWidgetClass(OfflineMotorWriteWidget)
        for accessor in ('labelWidget', 'readWidget', 'writeWidget', 'unitsWidget'):
            widget = getattr(form[1], accessor)()
            if widget is not None:
                widget.setFont(Qt.QFont('Sans Serif', 20))
                for child in widget.findChildren(Qt.QLineEdit):
                    child.setFont(Qt.QFont('Sans Serif', 20))
        return form

    def settle(self):
        # Process Qt's queued layout/resize events, without timers or sleeps.
        for _ in range(5):
            self.app.processEvents()

    def test_small_viewport_scrolls_without_compressing_enlarged_rows(self):
        for composite in (False, True):
            with self.subTest(composite=composite):
                form = self.make_form(composite)
                preserve_form_row_heights(form)
                form.resize(900, 180)
                form.show()
                self.settle()
                self.assertTrue(
                    form.scrollArea.verticalScrollBar().isVisible())
                self.assertGreater(
                    form.scrollArea.verticalScrollBar().maximum(), 0)
                for row in form:
                    for accessor in ('labelWidget', 'readWidget', 'writeWidget',
                                     'unitsWidget', 'extraWidget'):
                        widget = getattr(row, accessor)()
                        if widget is None or widget.isHidden():
                            continue
                        self.assertGreaterEqual(
                            widget.height(), widget.sizeHint().height())
                        self.assertGreaterEqual(
                            widget.height(), widget.minimumSizeHint().height())
                if composite:
                    editor = form[1].writeWidget()
                    self.assertIsInstance(editor, OfflineMotorWriteWidget)
                    for child in (editor.abs_input, editor.step):
                        self.assertGreaterEqual(
                            child.height(), child.sizeHint().height())
                        self.assertGreaterEqual(
                            editor.height(), child.height())
                # The fix must not force the outer form to stay tall.
                self.assertEqual(form.height(), 180)
                form.resize(900, 800)
                self.settle()
                self.assertEqual(
                    form.scrollArea.verticalScrollBar().maximum(), 0)
                form.close()

    def test_unstyled_form_is_not_modified_until_opted_in(self):
        form = self.make_form()
        read = form[1].readWidget()
        before = read.minimumHeight()
        self.assertLess(before, read.minimumSizeHint().height())
        preserve_form_row_heights(form)
        self.assertGreater(read.minimumHeight(), before)
        self.assertGreaterEqual(read.minimumHeight(),
                                read.minimumSizeHint().height())

    def test_shared_builder_applies_heights_after_fonts(self):
        # Extract the shared builder to avoid importing image/plot GUI backends.
        path = Path(__file__).resolve().parents[1] / 'common' / 'GUI.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == 'GuiBase')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == 'create_form_panel')
        namespace = {'Qt': Qt, 'TaurusForm': TaurusForm,
                     'preserve_form_row_heights': preserve_form_row_heights}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'),
             namespace)
        for fonts in (None, {'eval:2': {'font': 'Sans Serif', 'size': 20}}):
            with self.subTest(fonts=fonts):
                host = Qt.QWidget()
                self.addCleanup(host.deleteLater)
                layout = Qt.QVBoxLayout(host)
                device = SimpleNamespace(attr_list={'local': {
                    'model': ['eval:1', 'eval:2'], 'attrs': [],
                }})
                form = namespace['create_form_panel'](
                    device, layout, 'local', set_attr_font=fonts, withButtons=False)
                read = form[1].readWidget()
                self.assertGreaterEqual(
                    read.minimumHeight(), read.minimumSizeHint().height())
                if fonts:
                    self.assertEqual(read.font().pointSize(), 20)
                    self.assertGreater(read.minimumHeight(), 20)

    def test_repeated_application_is_stable(self):
        form = self.make_form(composite=True)
        preserve_form_row_heights(form)
        height = form.scrollArea.widget().layout().minimumSize().height()
        preserve_form_row_heights(form)
        self.assertEqual(form.scrollArea.widget(
        ).layout().minimumSize().height(), height)


if __name__ == '__main__':
    unittest.main()
