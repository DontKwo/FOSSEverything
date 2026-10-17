"""Tests for recent-history tracking and favorites-only home filtering."""
import os
import unittest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from app.ui.home_page import HomePage
from app.core.tool_registry import ToolRegistry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class HomeRecentAndFavoritesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['HomeRecentAndFavoritesTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_page(self) -> HomePage:
        settings = QSettings("FOSSEverythingTest", "HomeRecentAndFavorites")
        settings.clear()
        return HomePage(ToolRegistry(), settings=settings)

    def test_recent_history_keeps_latest_unique_entries(self) -> None:
        page = self.make_page()
        page.record_recent_file("docs/a.pdf")
        page.record_recent_file("docs/b.pdf")
        page.record_recent_file("docs/a.pdf")
        page.record_recent_output("out/result.pdf")

        self.assertEqual(page.recent_files[0], "docs/a.pdf")
        self.assertEqual(page.recent_files[1], "docs/b.pdf")
        self.assertEqual(page.recent_outputs[0], "out/result.pdf")

    def test_favorites_toggle_tracks_and_persists(self) -> None:
        page = self.make_page()
        page._toggle_favorite("pdf")
        page._toggle_favorite("image")

        self.assertEqual(page.favorites[:2], ["image", "pdf"])
        self.assertEqual(page.settings.value("home/favorites"), "image,pdf")

    def test_demo_recent_history_is_removed(self) -> None:
        settings = QSettings("FOSSEverythingTest", "HomeRecentAndFavoritesDemo")
        settings.clear()
        settings.setValue("home/recent_files", "C:/docs/photo.png|C:/docs/report.pdf|C:/docs/a.pdf|C:/docs/b.pdf")  # noqa: 26 (must match the demo-seed sentinel paths in home_page.py exactly)
        settings.setValue("home/recent_outputs", "C:/out/result.pdf")  # noqa: 26 (must match the demo-seed sentinel paths in home_page.py exactly)

        page = HomePage(ToolRegistry(), settings=settings)

        self.assertEqual(page.recent_files, [])
        self.assertEqual(page.recent_outputs, [])

    def test_filter_mode_persists_for_home_views(self) -> None:
        page = self.make_page()
        page._set_filter_mode("favorites")

        self.assertEqual(page.filter_mode, "favorites")
        self.assertEqual(page.settings.value("home/filter_mode"), "favorites")


if __name__ == "__main__":
    unittest.main()
