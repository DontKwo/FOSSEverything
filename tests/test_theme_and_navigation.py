"""Tests for the app theme persistence and keyboard navigation actions."""
import json
import os
import unittest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from app.ui.main_window import MainWindow
from app.ui.settings_hub import AppearanceSettings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ThemeAndNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['ThemeAndNavigationTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_persists_and_syncs_actions(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation")
        settings.clear()
        window = MainWindow(settings=settings)

        self.assertEqual(window.current_theme, "dark")
        window.set_theme("light")
        self.assertEqual(window.current_theme, "light")
        self.assertEqual(settings.value("app/theme"), "light")

    def test_keyboard_navigation_shortcuts_are_registered(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation2")
        settings.clear()
        window = MainWindow(settings=settings)

        self.assertEqual(window.home_action.shortcut().toString(), "Alt+H")
        window.go_home()
        self.assertGreaterEqual(window.tabs.currentIndex(), 0)

    def test_font_scale_is_persisted_and_applied(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation3")
        settings.clear()
        window = MainWindow(settings=settings)

        window.adjust_font_scale(0.2)
        self.assertAlmostEqual(float(settings.value("app/font_scale")), 1.2, places=2)
        self.assertGreater(window.font_scale, 1.0)

    def test_button_radius_and_accent_are_persisted(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation4")
        settings.clear()
        window = MainWindow(settings=settings)

        window.set_button_radius(12)
        self.assertEqual(window.button_radius, 12)
        self.assertEqual(int(settings.value("app/button_radius")), 12)

        window.accent_color = "#ff7a59"
        settings.setValue("app/accent_color", window.accent_color)
        self.assertEqual(str(settings.value("app/accent_color")), "#ff7a59")

    def test_custom_ui_palette_is_saved(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation5")
        settings.clear()
        window = MainWindow(settings=settings)

        window._apply_custom_palette({
            "background": "#112233",
            "text": "rgb(255, 0, 0)",
            "accent": "#00ff00",
        })

        saved_palette = json.loads(str(settings.value("app/ui_palette")))
        self.assertEqual(saved_palette["background"], "#112233")
        self.assertEqual(saved_palette["text"], "#ff0000")
        self.assertEqual(window._resolved_palette()["background"], "#112233")

    def test_palette_profiles_can_be_saved_and_loaded(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation6")
        settings.clear()
        window = MainWindow(settings=settings)
        page = AppearanceSettings(settings, window)

        page.color_fields["background"].setText("#112233")
        page.color_fields["accent"].setText("#00ff00")
        page.profile_combo.setCurrentIndex(0)
        page._save_profile()

        page.color_fields["background"].setText("#223344")
        page._load_profile()

        self.assertEqual(page.color_fields["background"].text(), "#112233")
        self.assertEqual(window._resolved_palette()["accent"], "#00ff00")

    def test_toolbar_customization_persists_hidden_actions(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation7")
        settings.clear()
        window = MainWindow(settings=settings)

        visible = window.image_tab.toolbar.visible_items()
        open_item = next(item for item in visible if item["label"] == "Open")
        visible_keys = [item["key"] for item in visible if item["key"] != open_item["key"]]

        window.image_tab.toolbar.set_custom_state(visible_keys, [open_item["key"]])
        self.assertNotIn(open_item["key"], [item["key"] for item in window.image_tab.toolbar.visible_items()])
        self.assertIn(open_item["key"], [item["key"] for item in window.image_tab.toolbar.hidden_items()])
        self.assertIsNotNone(settings.value("toolbar/image_toolbar"))

    def test_toolbar_customizer_ignores_numeric_editor_controls(self) -> None:
        settings = QSettings("FOSSEverythingTest", "ThemeNavigation8")
        settings.clear()
        window = MainWindow(settings=settings)

        labels = [item["label"] for item in window.pdf_tab.toolbar.visible_items()]
        self.assertNotIn("Font:", labels)
        self.assertNotIn("Size:", labels)
        self.assertNotIn("Char spacing:", labels)
        self.assertIn("Bold", [item["label"] for item in window.pdf_tab.toolbar.visible_items()])
        self.assertIn("Italic", [item["label"] for item in window.pdf_tab.toolbar.visible_items()])
        self.assertGreater(len(window.pdf_tab.toolbar._extra_rows), 0)


if __name__ == "__main__":
    unittest.main()
