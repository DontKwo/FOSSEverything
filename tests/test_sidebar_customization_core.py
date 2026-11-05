import unittest
from typing import Any
from app.core.sidebar_customization_core import (
    SidebarItem,
    SidebarSection,
    SidebarLayout,
    serialize_sidebar_layout,
    deserialize_sidebar_layout,
    reset_to_defaults,
)
from app.core.home_apps import HOME_APPS, HOME_CATEGORIES


class TestSidebarCustomizationCore(unittest.TestCase):
    def test_reset_to_defaults(self) -> None:
        layout = reset_to_defaults()
        self.assertEqual(layout.version, 1)
        self.assertEqual(len(layout.sections), len(HOME_CATEGORIES))

        for idx, category in enumerate(HOME_CATEGORIES):
            sec = layout.sections[idx]
            self.assertEqual(sec.name, category)
            self.assertEqual(sec.id, f"sec_{category.lower().replace(' ', '_')}")

            # Count apps for this category
            expected_apps = [app for app in HOME_APPS if app.category == category]
            self.assertEqual(len(sec.items), len(expected_apps))
            for i, expected_app in enumerate(expected_apps):
                self.assertEqual(sec.items[i].id, expected_app.id)
                self.assertTrue(sec.items[i].visible)

    def test_serialize_sidebar_layout(self) -> None:
        layout = SidebarLayout(
            version=1,
            sections=[
                SidebarSection(
                    id="sec_test",
                    name="Test Section",
                    collapsed=True,
                    items=[
                        SidebarItem(id="app1", visible=True),
                        SidebarItem(id="app2", visible=False),
                    ],
                )
            ],
        )

        data = serialize_sidebar_layout(layout)
        expected: dict[str, Any] = {
            "version": 1,
            "sections": [
                {
                    "id": "sec_test",
                    "name": "Test Section",
                    "collapsed": True,
                    "items": [
                        {"id": "app1", "visible": True},
                        {"id": "app2", "visible": False},
                    ],
                }
            ],
        }
        self.assertEqual(data, expected)

    def test_deserialize_sidebar_layout_valid(self) -> None:
        data: dict[str, Any] = {
            "version": 1,
            "sections": [
                {
                    "id": "sec_test2",
                    "name": "Another Section",
                    "collapsed": False,
                    "items": [{"id": "app3", "visible": False}],
                }
            ],
        }

        layout = deserialize_sidebar_layout(data)
        self.assertEqual(layout.version, 1)
        self.assertEqual(len(layout.sections), 1)
        sec = layout.sections[0]
        self.assertEqual(sec.id, "sec_test2")
        self.assertEqual(sec.name, "Another Section")
        self.assertFalse(sec.collapsed)
        self.assertEqual(len(sec.items), 1)
        self.assertEqual(sec.items[0].id, "app3")
        self.assertFalse(sec.items[0].visible)

    def test_deserialize_sidebar_layout_invalid_version(self) -> None:
        data: dict[str, Any] = {"version": 2, "sections": []}
        layout = deserialize_sidebar_layout(data)

        defaults = reset_to_defaults()
        self.assertEqual(layout.version, 1)
        self.assertEqual(len(layout.sections), len(defaults.sections))

    def test_deserialize_sidebar_layout_invalid_data(self) -> None:
        layout = deserialize_sidebar_layout(None)
        self.assertEqual(layout.version, 1)
        self.assertEqual(len(layout.sections), len(HOME_CATEGORIES))

        layout = deserialize_sidebar_layout({"sections": {}})
        self.assertEqual(layout.version, 1)
        self.assertEqual(len(layout.sections), len(HOME_CATEGORIES))
