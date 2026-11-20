"""Unit tests validating canonical tool inventory completeness and test linkage."""
from __future__ import annotations

import unittest
from pathlib import Path

from app.core.home_apps import HOME_APPS
from app.core.tool_inventory import (
    TOOL_INVENTORY,
    get_tool_entry,
    get_tool_inventory,
    validate_tool_inventory,
)


class ToolInventoryTests(unittest.TestCase):
    def test_inventory_matches_home_apps(self) -> None:
        inventory = get_tool_inventory()
        self.assertEqual(len(inventory), len(HOME_APPS))
        inv_ids = {item.id for item in inventory}
        app_ids = {app.id for app in HOME_APPS}
        self.assertEqual(inv_ids, app_ids)

    def test_validation_passes(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        report = validate_tool_inventory(project_root)
        self.assertTrue(report["valid"], f"Inventory validation failed: {report}")
        self.assertEqual(len(report["missing_inventory"]), 0)
        self.assertEqual(len(report["missing_tests"]), 0)

    def test_get_tool_entry(self) -> None:
        pdf_entry = get_tool_entry("pdf")
        self.assertIsNotNone(pdf_entry)
        assert pdf_entry is not None
        self.assertEqual(pdf_entry.name, "PDF Studio")
        self.assertEqual(pdf_entry.category, "Documents")
        self.assertTrue(len(pdf_entry.test_modules) > 0)

        missing = get_tool_entry("non_existent_tool_1234")
        self.assertIsNone(missing)

    def test_entry_fields_are_well_formed(self) -> None:
        for entry in TOOL_INVENTORY:
            self.assertTrue(len(entry.purpose.strip()) > 10, f"{entry.id} has short purpose")
            self.assertTrue(len(entry.os_support) == 3, f"{entry.id} missing OS support tuple")
            self.assertTrue(len(entry.offline_behavior.strip()) > 5, f"{entry.id} missing offline statement")
            self.assertTrue(len(entry.destructive_risk.strip()) > 3, f"{entry.id} missing destructive risk")
            self.assertTrue(len(entry.test_modules) >= 1, f"{entry.id} missing test modules")


if __name__ == "__main__":
    unittest.main()
