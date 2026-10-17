"""Regression tests for actions launched from the Home search results."""
import os
import unittest

from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
class HomeActionActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['HomeActionActivationTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_action_ignores_qt_clicked_boolean(self) -> None:
        """QPushButton.clicked(bool) must not replace the captured tab."""
        window = MainWindow()
        received = []
        window._activate_tab_tool = lambda tab, method: received.append((tab, method))

        tool = next(result.tool for result in window.tool_registry.search("merge"))
        tool.activate(True)  # The exact boolean passed by QPushButton.clicked.

        self.assertEqual(received, [(window.pdf_tab, "merge_pdfs")])


if __name__ == "__main__":
    unittest.main()
