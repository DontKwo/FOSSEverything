# Tests for sidebar customization, canonical app catalog, and scale bounds.
from typing import Any
import os
import unittest
from unittest.mock import patch
from app.core.home_apps import HOME_APPS, HOME_CATEGORIES
from app.system.settings import (
    reset_user_preferences,
)
from main import THEME_BG_MAP


class TestSidebarCustomization(unittest.TestCase):
    # Verify preferences preservation, catalog completeness, and theme scale constraints.

    def test_reset_user_preferences_preserves_customizations(self) -> None:
        # Verify reset_user_preferences preserves layout, favorites, and recents.
        custom_layout: dict[str, Any] = {
            "version": 1,
            "sections": [
                {
                    "id": "sec_custom",
                    "name": "Quick Tools",
                    "collapsed": False,
                    "items": [{"id": "pdf", "visible": True}],
                }
            ],
        }
        test_state: dict[str, Any] = {
            "theme": "cyberpunk",
            "ui_scale": 1.75,
            "custom_colors": {"accent": "#ff0077"},
            "favorites": ["pdf", "ocr"],
            "recent_files": ["C:/tmp/test.pdf"],
            "recent_outputs": ["C:/tmp/out.png"],
            "sidebar_layout": custom_layout,
        }

        with patch("app.system.settings.calc_read_settings", return_value=dict(test_state)):
            written: dict[str, Any] = {}

            def mock_write(data: dict[str, Any]) -> None:
                written.update(data)

            with patch("app.system.settings.calc_write_settings", side_effect=mock_write):
                reset_user_preferences()

                self.assertEqual(written.get("theme"), "dark")
                self.assertEqual(written.get("ui_scale"), 1.0)
                self.assertEqual(written.get("custom_colors"), {})
                self.assertEqual(written.get("favorites"), ["pdf", "ocr"])
                self.assertEqual(written.get("recent_files"), ["C:/tmp/test.pdf"])
                self.assertEqual(written.get("recent_outputs"), ["C:/tmp/out.png"])
                self.assertEqual(written.get("sidebar_layout"), custom_layout)

    def test_app_catalog_completeness(self) -> None:
        # Verify canonical 21 apps and 5 categories are complete and populated.
        expected_ids = {
            "pdf", "ocr", "markdown", "resume",
            "images", "collage", "palette", "model3d",
            "media", "playlist",
            "converter", "compressor", "archive", "renamer", "metadata", "qr", "network_monitor",
            "unit_converter", "data", "text_tools", "encoding",
        }
        actual_ids = {app.id for app in HOME_APPS}
        self.assertEqual(len(HOME_APPS), 21)
        self.assertEqual(actual_ids, expected_ids)

        self.assertEqual(
            list(HOME_CATEGORIES),
            ["Documents", "Visuals", "Media", "Utilities", "Data"],
        )

        for app in HOME_APPS:
            self.assertTrue(bool(app.id))
            self.assertTrue(bool(app.name))
            self.assertIn(app.category, HOME_CATEGORIES)
            self.assertTrue(len(app.description) > 0)
            self.assertIsInstance(app.keywords, tuple)

    def test_theme_background_and_zoom_bounds(self) -> None:
        # Verify theme backgrounds include all presets and JS files exist.
        self.assertIn("cyberpunk", THEME_BG_MAP)
        self.assertIn("ut_austin", THEME_BG_MAP)
        self.assertIn("ut", THEME_BG_MAP)

        router_path = os.path.join("app", "web", "js", "core", "router.js")
        with open(router_path, "r", encoding="utf-8") as f:
            router_js = f.read()
        self.assertIn("resolveSidebarLayout", router_js)
        self.assertIn("sec_documents", router_js)
        self.assertIn("sec_visuals", router_js)
        self.assertIn("sec_media", router_js)
        self.assertIn("sec_utilities", router_js)
        self.assertIn("sec_data", router_js)

        theme_path = os.path.join("app", "web", "js", "core", "theme.js")
        with open(theme_path, "r", encoding="utf-8") as f:
            theme_js = f.read()
        self.assertIn("0.50", theme_js)
        self.assertIn("2.50", theme_js)

    def test_resolve_sidebar_layout_permits_multiple_sections(self) -> None:
        # Verify resolveSidebarLayout permits items across multiple sections.
        router_path = os.path.join("app", "web", "js", "core", "router.js")
        with open(router_path, "r", encoding="utf-8") as f:
            router_js = f.read()

        # Verify there's no global seen-set or deduplication blocking multiple section entries
        self.assertNotIn("seenIds", router_js)
        self.assertNotIn("isAlreadyInAnySection", router_js)

        # Verify it specifically checks only the target section when appending
        self.assertIn("targetSec.items.forEach", router_js)
        self.assertIn("isAlreadyInTarget", router_js)
