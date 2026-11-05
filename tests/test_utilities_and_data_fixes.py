"""Verification test suite for utilities and data suite overhaul (Phase 17.1-17.7)."""
import os
import tempfile
import unittest

from PIL import Image

from app.features.encoding.ops import html_encode_numeric
from app.features.metadata.ops import gps_preview_for_metadata, strip_any_metadata
from app.features.network_monitor.resolver import DomainResolver
from app.features.qr.ops import make_calendar_payload
from app.web.api import WebApi
from app.web.api.hdf5_reader import inspect_hdf5, is_hdf5_file


class UtilitiesAndDataFixesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = WebApi()

    # 17.1: Metadata GPS DMS and arbitrary byte stripping
    def test_metadata_strip_any_metadata_bytes(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf_in:
            in_path = tf_in.name
        img = Image.new("RGB", (20, 20), color="blue")
        img.save(in_path)
        out_path = in_path + ".clean.png"
        try:
            res = strip_any_metadata(in_path, out_path)
            self.assertIsInstance(res, dict)
            self.assertIn("output_path", res)
            self.assertTrue(os.path.exists(out_path))
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_metadata_gps_extraction(self) -> None:
        coords = gps_preview_for_metadata({"gpslatitude": "37.7749", "gpslatituderef": "N", "gpslongitude": "122.4194", "gpslongituderef": "W"})
        self.assertIsNotNone(coords)
        if coords:
            self.assertTrue(coords.get("has_gps"))
            self.assertAlmostEqual(coords["latitude"], 37.7749, places=3)
            self.assertAlmostEqual(coords["longitude"], -122.4194, places=3)

    # 17.2: QR & Barcode generation & ICS handling
    def test_qr_barcode_bounding_box(self) -> None:
        res = self.api.qr_generate_barcode({"payload": "12345678", "barcode_type": "code128"})
        self.assertTrue(res.get("ok"))
        self.assertIn("data_url", res)
        self.assertGreater(res.get("width", 0), 0)
        self.assertGreater(res.get("height", 0), 0)

    def test_qr_calendar_generation(self) -> None:
        payload = make_calendar_payload(summary="Sync Meeting", start="2026-11-02T10:00:00", end="2026-11-02T11:00:00")
        self.assertIn("BEGIN:VCALENDAR", payload)
        self.assertIn("SUMMARY:Sync Meeting", payload)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ics") as tf:
            out_ics = tf.name
        try:
            res = self.api.qr_export_ics({"title": "Sync Meeting", "start_time": "2026-11-02T10:00:00", "output_path": out_ics})
            self.assertTrue(res.get("ok"))
            self.assertTrue(os.path.exists(out_ics))
        finally:
            if os.path.exists(out_ics):
                os.remove(out_ics)

    # 17.3: Hash endpoints
    def test_all_seven_hash_endpoints(self) -> None:
        if not hasattr(self.api, "hash_supported_algorithms"):
            self.skipTest("Hash tool erased in Phase 2")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
            tf.write(b"hash test payload")
            tmp_path = tf.name

        try:
            r1 = self.api.hash_supported_algorithms({})
            self.assertTrue(r1.get("ok"))
            self.assertIn("algorithms", r1)

            r2 = self.api.hash_file({"file_path": tmp_path, "algorithm": "sha256"})
            self.assertTrue(r2.get("ok"))
            computed = r2["hash"]

            r3 = self.api.hash_text({"text": "Antigravity", "algorithm": "sha256"})
            self.assertTrue(r3.get("ok"))
            self.assertIn("hash", r3)

            r4 = self.api.hash_multi({"file_path": tmp_path})
            self.assertTrue(r4.get("ok"))
            self.assertIn("hashes", r4)

            r5 = self.api.hash_compare_files({"path1": tmp_path, "path2": tmp_path, "algorithm": "sha256"})
            self.assertTrue(r5.get("ok"))
            self.assertTrue(r5.get("identical"))

            r6 = self.api.hash_hmac({"key": "secret", "data": "hello", "algorithm": "sha256"})
            self.assertTrue(r6.get("ok"))
            self.assertIn("hmac", r6)

            r7 = self.api.hash_verify({"file_path": tmp_path, "expected_hash": computed, "algorithm": "sha256"})
            self.assertTrue(r7.get("ok"))
            self.assertTrue(r7.get("matches"))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # 17.4: Data suite fixes (HDF5, format_css, json_schema, cron)
    def test_data_hdf5_real_bytes(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tf:
            # Write standard 64-byte HDF5 superblock header
            tf.write(b"\x89HDF\r\n\x1a\n" + b"\x00" * 56)
            h5_path = tf.name
        try:
            self.assertTrue(is_hdf5_file(h5_path))
            info = inspect_hdf5(h5_path)
            self.assertIsInstance(info, dict)
            self.assertEqual(info.get("format"), "HDF5")
        finally:
            if os.path.exists(h5_path):
                os.remove(h5_path)

    def test_data_format_css(self) -> None:
        css = "body{color:red;margin:0;}"
        res = self.api.data_format_code({"content": css, "language": "css"})
        self.assertTrue(res.get("ok"))
        self.assertIn("{\n", res.get("result", ""))

    def test_data_json_schema(self) -> None:
        res = self.api.data_infer_schema({"content": '{"name": "Alice", "age": 30}'})
        self.assertTrue(res.get("ok"))
        self.assertIn("schema", res)

    def test_data_cron_parser(self) -> None:
        res = self.api.data_cron_describe({"expression": "*/15 * * * *"})
        self.assertTrue(res.get("ok"))
        self.assertIn("description", res)

    # 17.5: Text tools & word counter
    def test_text_tools_regex_replace_and_reverse(self) -> None:
        res1 = self.api.text_tools_regex_replace({"text": "abc 123 def 456", "pattern": r"\d+", "replacement": "NUM"})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("result"), "abc NUM def NUM")

        res2 = self.api.text_tools_lines({"text": "line1\nline2", "operation": "reverse_lines"})
        self.assertTrue(res2.get("ok"))
        self.assertEqual(res2.get("result"), "line2\nline1")

    def test_word_counter_unified_stats(self) -> None:
        text = "Antigravity is a fast and responsive agentic coding platform."
        res = self.api.word_counter_analyze({"text": text})
        self.assertTrue(res.get("ok"))
        self.assertIn("char_count", res)
        self.assertIn("char_no_spaces", res)
        self.assertIn("reading_time_min", res)
        self.assertIn("speaking_time_min", res)
        self.assertIn("flesch_ease", res)
        self.assertIn("fk_grade", res)

    # 17.6: Encoding transforms
    def test_encoding_html_numeric_hex(self) -> None:
        encoded = html_encode_numeric("Caf\u00e9", hex_format=True)
        self.assertIn("&#xe9;", encoded)

    def test_encoding_binary_text(self) -> None:
        res_enc = self.api.encoding_binary_encode_text({"text": "Hi"})
        self.assertTrue(res_enc.get("ok"))
        bin_str = res_enc.get("result")
        self.assertEqual(bin_str, "01001000 01101001")

        res_dec = self.api.encoding_binary_decode_text({"text": bin_str})
        self.assertTrue(res_dec.get("ok"))
        self.assertEqual(res_dec.get("result"), "Hi")

    # 17.7: Network monitor non-blocking domain resolution and throughput
    def test_network_monitor_throughput_and_status(self) -> None:
        res = self.api.network_get_connections({})
        self.assertTrue(res.get("ok"))
        self.assertIn("throughput", res)
        self.assertIn("connections", res)
        self.assertIn("up_kb", res["throughput"])
        self.assertIn("down_kb", res["throughput"])

    def test_network_monitor_resolver_nonblocking(self) -> None:
        resolver = DomainResolver()
        resolver.preload({"8.8.8.8": "dns.google"})
        self.assertEqual(resolver.resolve_cached("8.8.8.8"), "dns.google")
        self.assertEqual(resolver.resolve_cached("1.2.3.4"), "")


if __name__ == "__main__":
    unittest.main()
