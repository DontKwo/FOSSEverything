"""Integration tests for WebApi bridge methods."""

from __future__ import annotations

import unittest


from app.web.api import WebApi


class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = WebApi()

    def test_get_apps_returns_all_home_apps(self) -> None:
        res = self.api.get_apps({})
        self.assertTrue(res.get("ok"))
        apps = res["apps"]
        self.assertGreaterEqual(len(apps), 20)
        ids = {app["id"] for app in apps}
        self.assertIn("pdf", ids)
        self.assertIn("images", ids)
        self.assertIn("compressor", ids)
        self.assertIn("model3d", ids)
        self.assertIn("converter", ids)

    def test_settings_and_theme_palette(self) -> None:
        res = self.api.get_theme_palette({"theme_name": "dark"})
        self.assertTrue(res.get("ok"))
        self.assertIn("background", res)
        self.assertIn("accent", res)

        set_res = self.api.set_setting({"key": "test_key", "value": "test_val"})
        self.assertTrue(set_res.get("ok"))
        get_res = self.api.get_setting({"key": "test_key"})
        self.assertTrue(get_res.get("ok"))
        self.assertEqual(get_res.get("value"), "test_val")

        reset_defaults_res = self.api.reset_settings_defaults({})
        self.assertTrue(reset_defaults_res.get("ok"))
        self.assertEqual(
            reset_defaults_res.get("message"), "Settings reset to defaults"
        )
        self.assertEqual(self.api.get_setting({"key": "theme"}).get("value"), "dark")
        self.assertIsNone(self.api.get_setting({"key": "test_key"}).get("value"))

    def test_search_tools(self) -> None:
        res = self.api.search_tools({"query": "pdf"})
        self.assertTrue(res.get("ok"))
        self.assertIsInstance(res.get("results"), list)
        self.assertGreater(len(res["results"]), 0)

    def test_pdf_operations(self) -> None:
        fmt_res = self.api.format_json({"content": '{"b":2,"a":1}', "indent": 2})
        self.assertTrue(fmt_res.get("ok"))
        self.assertIn('"a": 1', fmt_res["result"])

        js_res = self.api.format_js({"content": "function test(){return 1;}"})
        self.assertTrue(js_res.get("ok"))

        # Test structure inspection.
        struct_res = self.api.data_inspect_structure(
            {"content": '{"name": "Tool", "count": 5}'}
        )
        self.assertTrue(struct_res.get("ok"))
        self.assertEqual(struct_res.get("format"), "JSON")
        self.assertIn("root", struct_res)

