from __future__ import annotations

import unittest

from app.features.unit_converter import ops as unit_ops
from app.web.api import WebApi


class UnitConverterPintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = WebApi()

    def test_offset_temperatures(self) -> None:
        # Verify non-linear temperature conversions between Celsius, Fahrenheit, and Kelvin.
        c0_to_f = unit_ops.convert_unit_value(0.0, "degC", "degF")
        self.assertAlmostEqual(c0_to_f["result"], 32.0, places=2)

        c0_to_k = unit_ops.convert_unit_value(0.0, "degC", "kelvin")
        self.assertAlmostEqual(c0_to_k["result"], 273.15, places=2)

        neg40_c_to_f = unit_ops.convert_unit_value(-40.0, "degC", "degF")
        self.assertAlmostEqual(neg40_c_to_f["result"], -40.0, places=2)

    def test_digital_storage_si_and_iec(self) -> None:
        # Verify distinction between SI decimal and IEC binary digital storage.
        kib_to_b = unit_ops.convert_unit_value(1.0, "KiB", "byte")
        self.assertEqual(kib_to_b["result"], 1024.0)

        kib_to_bit = unit_ops.convert_unit_value(1.0, "KiB", "bit")
        self.assertEqual(kib_to_bit["result"], 8192.0)

        kb_to_b = unit_ops.convert_unit_value(1.0, "kB", "byte")
        self.assertEqual(kb_to_b["result"], 1000.0)

        kb_to_bit = unit_ops.convert_unit_value(1.0, "kB", "bit")
        self.assertEqual(kb_to_bit["result"], 8000.0)

    def test_compound_expressions(self) -> None:
        # Verify compound thermal and mechanical expression calculations.
        res1 = unit_ops.convert_expression("350 BTU / (hr * ft**2 * delta_degF)", target_unit="W / (m**2 * K)")
        self.assertAlmostEqual(res1["result"], 1987.392, places=1)

        res2 = unit_ops.convert_expression("1 lbf / in**2", target_unit="Pa")
        self.assertAlmostEqual(res2["result"], 6894.757, places=1)

    def test_exotic_pint_units_and_compatible_lookup(self) -> None:
        # Verify compatible unit lookup for diverse physical disciplines.
        compat = unit_ops.convert_to_compatible_units(1.0, "parsec", include_all=True)
        unit_ids = [item["id"] for item in compat]
        self.assertIn("light_year", unit_ids)

        catalog = unit_ops.get_unit_catalog()
        self.assertGreaterEqual(len(catalog["categories"]), 30)

    def test_api_endpoints(self) -> None:
        # Verify WebApi unit conversion endpoints return valid responses.
        cat_res = self.api.units_catalog({})
        self.assertTrue(cat_res.get("ok"))

        conv_res = self.api.units_convert({
            "value": 100.0,
            "from_unit": "km_h",
            "to_unit": "mph",
        })
        self.assertTrue(conv_res.get("ok"))
        self.assertAlmostEqual(conv_res.get("result", 0.0), 62.137, places=2)

        table_res = self.api.units_compatible_table({
            "value": 1.0,
            "from_unit": "m",
            "category_id": "length",
        })
        self.assertTrue(table_res.get("ok"))
        self.assertGreaterEqual(table_res.get("count", 0), 10)

        expr_res = self.api.units_expression({
            "expression": "9.80665 m/s**2 * 75 kg",
            "target_unit": "N",
        })
        self.assertTrue(expr_res.get("ok"))
        self.assertAlmostEqual(expr_res.get("result", 0.0), 735.498, places=2)

    def test_error_messages_hide_backend_names(self) -> None:
        # Verify failed conversions and the catalog never expose backend package names.
        mismatch = self.api.units_convert({"value": 1.0, "from_unit": "m", "to_unit": "s"})
        self.assertFalse(mismatch.get("ok"))
        self.assertNotIn("pint", str(mismatch.get("error", "")).lower().replace("pint (us)", ""))

        unknown = self.api.units_expression({"expression": "3 flurbles", "target_unit": "m"})
        self.assertFalse(unknown.get("ok"))
        self.assertNotIn("pint.", str(unknown.get("error", "")).lower())

        catalog = self.api.units_catalog({})
        first_unit = catalog["categories"][0]["units"][0]
        self.assertNotIn("pint", first_unit)
        self.assertIn("expr", first_unit)

    def test_sanitize_error_message_strips_qualified_names(self) -> None:
        # Verify dotted package paths in exception text are replaced.
        cleaned = unit_ops.sanitize_error_message(ValueError("failed in pint.errors.DimensionalityError for x"))
        self.assertNotIn("pint.", cleaned)

    def test_standard_notation_is_default_and_matches_digits(self) -> None:
        # Verify the standard notation honors the configured significant digits.
        res = self.api.units_convert({"value": 1.0, "from_unit": "km", "to_unit": "mi", "format_mode": "standard", "sig_figs": 4})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("formatted"), "0.6214")


if __name__ == "__main__":
    unittest.main()
