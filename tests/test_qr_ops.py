"""Tests for QR Code generation and payload formats."""
import unittest
import os
import tempfile
from PIL import Image
from app.features.qr import ops as qr_ops


class QrOpsTests(unittest.TestCase):
    def test_generate_qr_code(self) -> None:
        img = qr_ops.generate_qr_code("https://example.com", error_correction="M", box_size=8)
        self.assertIsNotNone(img)
        self.assertEqual(img.mode, "RGBA")
        self.assertGreater(img.width, 50)

    def test_wifi_payload(self) -> None:
        payload = qr_ops.make_wifi_payload("HomeGuest", "superSecret123", security="WPA")
        self.assertIn("WIFI:", payload)
        self.assertIn("S:HomeGuest;", payload)
        self.assertIn("P:superSecret123;", payload)
        self.assertIn("T:WPA;", payload)

    def test_vcard_payload(self) -> None:
        payload = qr_ops.make_vcard_payload("Alice Smith", phone="555-1234", email="alice@corp.com", org="Corp")
        self.assertIn("BEGIN:VCARD", payload)
        self.assertIn("FN:Alice Smith", payload)
        self.assertIn("TEL;TYPE=CELL:555-1234", payload)
        self.assertIn("EMAIL:alice@corp.com", payload)
        self.assertIn("END:VCARD", payload)

    def test_email_payload(self) -> None:
        payload = qr_ops.make_email_payload("dev@FOSSEverything.local", subject="Hello", body="World")
        self.assertTrue(payload.startswith("mailto:dev@FOSSEverything.local"))
        self.assertIn("subject=Hello", payload)

    def test_save_qr_code(self) -> None:
        img = qr_ops.generate_qr_code("Test Save")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            saved = qr_ops.save_qr_code(img, tmp_path, format="PNG")
            self.assertTrue(os.path.exists(saved))
            self.assertGreater(os.path.getsize(saved), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


    def test_generate_barcode(self) -> None:
        img = qr_ops.generate_barcode("ABC123", barcode_type="code39", width=2, height=80, include_label=True)
        self.assertIsNotNone(img)
        self.assertEqual(img.mode, "RGBA")
        self.assertGreater(img.width, 50)
        self.assertGreater(img.height, 50)

    def test_generate_qr_with_logo(self) -> None:
        logo = Image.new("RGBA", (40, 40), (255, 0, 0, 255))
        img = qr_ops.generate_qr_with_logo("https://github.com", logo=logo, logo_scale=0.25)
        self.assertIsNotNone(img)
        self.assertEqual(img.mode, "RGBA")

    def test_generate_qr_svg(self) -> None:
        svg = qr_ops.generate_qr_svg("https://FOSSEverything.local", error_correction="M")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("<rect", svg)

    def test_decode_qr_code(self) -> None:
        img = qr_ops.generate_qr_code("https://github.com/fosseverything", box_size=10)
        results = qr_ops.decode_qr_and_barcodes(img)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["payload"], "https://github.com/fosseverything")
        self.assertEqual(results[0]["parsed"]["type"], "url")

    def test_parse_qr_payload(self) -> None:
        wifi = qr_ops.parse_qr_payload("WIFI:T:WPA;S:MyNet;P:SecretKey;;")
        self.assertEqual(wifi["type"], "wifi")
        self.assertEqual(wifi["data"]["ssid"], "MyNet")
        self.assertEqual(wifi["data"]["password"], "SecretKey")

        url = qr_ops.parse_qr_payload("https://example.org")
        self.assertEqual(url["type"], "url")

    def test_extended_payload_helpers(self) -> None:
        sms = qr_ops.make_sms_payload("+15551234567", "Dinner at 7")
        self.assertTrue(sms.startswith("SMSTO:"))
        self.assertEqual(qr_ops.parse_qr_payload(sms)["type"], "sms")

        geo = qr_ops.make_geo_payload(40.7128, -74.0060)
        self.assertEqual(qr_ops.parse_qr_payload(geo)["type"], "geo")

        event = qr_ops.make_calendar_payload(
            summary="Team sync",
            start="2026-09-01T10:00:00",
            end="2026-09-01T10:30:00",
            location="HQ",
            description="Review sprint",
        )
        self.assertIn("BEGIN:VCALENDAR", event)
        self.assertEqual(qr_ops.parse_qr_payload(event)["type"], "calendar")

    def test_decode_qr_from_numpy_array(self) -> None:
        img = qr_ops.generate_qr_code("https://FOSSEverything.local/qrcode-array", box_size=8)
        arr = __import__("numpy").array(img)
        results = qr_ops.decode_qr_and_barcodes(arr)
        self.assertTrue(results)
        self.assertIn("https://FOSSEverything.local/qrcode-array", results[0]["payload"])

    def test_calendar_payload_uses_ical_datetime(self) -> None:
        event = qr_ops.make_calendar_payload("Sync", "2026-11-01T12:00", "2026-11-01T13:30:00Z")
        self.assertIn("DTSTART:20261101T120000", event)
        self.assertIn("DTEND:20261101T133000Z", event)

    def test_save_barcode_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = os.path.join(directory, "code.svg")
            qr_ops.save_barcode_svg("123456789012", "ean13", out)
            with open(out, "r", encoding="utf-8") as handle:
                self.assertIn("<svg", handle.read())


class QrApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.web.api import WebApi

        self.api = WebApi()

    def test_generate_from_schema_fields_and_size(self) -> None:
        res = self.api.qr_generate({
            "schema": "wifi",
            "fields": {"ssid": "Cafe", "password": "pw", "security": "WPA", "hidden": False},
            "size_px": 256,
            "error_correction": "H",
        })
        self.assertTrue(res["ok"])
        self.assertEqual((res["width"], res["height"]), (256, 256))
        self.assertTrue(res["payload"].startswith("WIFI:"))

    def test_generate_each_payload_schema(self) -> None:
        schemas = {
            "url": {"text": "https://example.com"},
            "text": {"text": "hello"},
            "vcard": {"name": "Ada Lovelace", "phone": "555"},
            "sms": {"phone": "+15550100", "message": "hi"},
            "whatsapp": {"phone": "+15550100", "message": "hi"},
            "geo": {"lat": 40.7, "lon": -74.0},
            "calendar": {"title": "Sync", "start_time": "2026-11-01T12:00"},
            "asset": {"asset_id": "abc123"},
        }
        for schema, fields in schemas.items():
            res = self.api.qr_generate({"schema": schema, "fields": fields})
            self.assertTrue(res["ok"], schema)
            self.assertTrue(res["payload"], schema)

    def test_save_png_and_svg_follow_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            png = os.path.join(directory, "barcode.png")
            res = self.api.qr_generate({"payload": "hello", "output_path": png, "size_px": 128})
            self.assertTrue(res["ok"])
            with Image.open(png) as saved:
                self.assertEqual(saved.size, (128, 128))
            svg = os.path.join(directory, "barcode.svg")
            res = self.api.qr_generate_svg({"payload": "hello", "output_path": svg, "fill_color": "#112233"})
            self.assertTrue(res["ok"])
            with open(svg, "r", encoding="utf-8") as handle:
                self.assertIn("#112233", handle.read())

    def test_barcode_png_and_svg_and_decode_data_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for name, kind in (("c128.png", "code128"), ("c128.svg", "code128"), ("ean.svg", "ean13")):
                out = os.path.join(directory, name)
                value = "123456789012" if kind == "ean13" else "ABC-123"
                res = self.api.qr_generate_barcode({"payload": value, "barcode_type": kind, "output_path": out})
                self.assertTrue(res["ok"], name)
                self.assertTrue(os.path.getsize(out) > 0)
        qr = self.api.qr_generate({"payload": "https://example.org/decode-me", "box_size": 8})
        decoded = self.api.qr_decode_data_url({"data_url": qr["data_url"]})
        self.assertTrue(decoded["ok"])
        self.assertEqual(decoded["results"][0]["payload"], "https://example.org/decode-me")

    def test_empty_params_do_not_raise(self) -> None:
        self.assertFalse(self.api.qr_generate({})["ok"])
        self.assertFalse(self.api.qr_generate_barcode({})["ok"])
        self.assertFalse(self.api.qr_decode_data_url({})["ok"])


if __name__ == "__main__":
    unittest.main()
