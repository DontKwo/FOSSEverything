"""Unit tests verifying sanitized diagnostics bundle generation and path sanitization."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from app.system.diagnostics import (
    check_external_dependencies,
    export_diagnostics_json,
    generate_diagnostics_report,
    sanitize_path,
)


class DiagnosticsTests(unittest.TestCase):
    def test_sanitize_path_scrubs_home(self) -> None:
        home = os.path.expanduser("~")
        private_path = os.path.join(home, "Documents", "secret.pdf")
        sanitized = sanitize_path(private_path)
        self.assertFalse(sanitized.startswith(home))
        self.assertTrue(sanitized.startswith("~") or "<USER>" in sanitized)

    def test_check_external_dependencies_structure(self) -> None:
        deps = check_external_dependencies()
        self.assertIn("ffmpeg", deps)
        self.assertIn("tesseract", deps)
        self.assertIn("libreoffice", deps)
        for dep_name, info in deps.items():
            self.assertIn("available", info)
            self.assertIn("description", info)
            if info["available"]:
                self.assertIsNotNone(info["version"])

    def test_generate_diagnostics_report_schema(self) -> None:
        report = generate_diagnostics_report()
        self.assertEqual(report["schema_version"], "1.0.0")
        self.assertIn("timestamp_utc", report)
        self.assertIn("runtime", report)
        self.assertIn("tool_inventory", report)
        self.assertIn("dependencies", report)

        self.assertTrue(report["tool_inventory"]["validated"])
        self.assertGreaterEqual(report["tool_inventory"]["total_tools"], 22)

    def test_export_diagnostics_json(self) -> None:
        payload_str = export_diagnostics_json()
        parsed = json.loads(payload_str)
        self.assertEqual(parsed["schema_version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
