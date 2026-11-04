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
        res1 = unit_ops.convert_pint_expression("350 BTU / (hr * ft**2 * delta_degF)", target_unit="W / (m**2 * K)")
        self.assertAlmostEqual(res1["result"], 1987.392, places=1)

        res2 = unit_ops.convert_pint_expression("1 lbf / in**2", target_unit="Pa")
        self.assertAlmostEqual(res2["result"], 6894.757, places=1)

    def test_exotic_pint_units_and_compatible_lookup(self) -> None:
        # Verify compatible unit lookup for diverse physical disciplines.
        compat = unit_ops.convert_to_compatible_units(1.0, "parsec", include_all_pint=True)
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

