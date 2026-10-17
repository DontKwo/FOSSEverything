"""Tests for routing dropped files from the Home screen."""
import os
import unittest

from PyQt6.QtWidgets import QApplication

from app.ui.home_page import HomePage
from app.core.tool_registry import ToolRegistry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class HomeDropRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['HomeDropRoutingTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dropped_file_paths_are_routed_and_logged(self) -> None:
        seen = []

        def route(paths: list[str]) -> None:
            seen.extend(paths)

        page = HomePage(ToolRegistry(), route_callback=route)
        page._handle_dropped_paths(["docs/report.pdf", "docs/photo.png"])

        self.assertEqual(seen, ["docs/report.pdf", "docs/photo.png"])
        self.assertEqual(page.recent_files[:2], ["docs/photo.png", "docs/report.pdf"])


if __name__ == "__main__":
    unittest.main()
