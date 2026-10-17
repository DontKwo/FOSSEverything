"""Unit tests for encoding/decoding operations."""
import os
import tempfile
import unittest
from app.features.encoding import ops as encoding_ops


class Base64OpsTests(unittest.TestCase):
    def test_encode_decode_text_roundtrip(self) -> None:
        encoded = encoding_ops.base64_encode_text("Hello, FOSSEverything!")
        self.assertEqual(encoded, "SGVsbG8sIEZPU1NFdmVyeXRoaW5nIQ==")
        decoded = encoding_ops.base64_decode_text(encoded)
        self.assertEqual(decoded, "Hello, FOSSEverything!")

    def test_url_safe_alphabet_roundtrip(self) -> None:
        text = "\xfb\xff>>subjects?a=1&b=2"
        encoded = encoding_ops.base64_encode_text(text, url_safe=True)
        self.assertNotIn("+", encoded)
        self.assertNotIn("/", encoded)
        decoded = encoding_ops.base64_decode_text(encoded, url_safe=True)
        self.assertEqual(decoded, text)

    def test_decode_invalid_base64_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            encoding_ops.base64_decode_text("not-valid-base64!!!")

    def test_decode_bad_utf8_raises_value_error(self) -> None:
        invalid_utf8_b64 = "gA=="  # single 0x80 byte, invalid UTF-8 continuation
        with self.assertRaises(ValueError):
            encoding_ops.base64_decode_text(invalid_utf8_b64)

    def test_encode_decode_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "source.bin")
            payload = bytes(range(256))
            with open(src, "wb") as f:
                f.write(payload)

            encoded = encoding_ops.base64_encode_file(src)
            out = os.path.join(td, "out.bin")
            encoding_ops.base64_decode_to_file(encoded, out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), payload)


class UrlOpsTests(unittest.TestCase):
    def test_component_encode_decode_roundtrip(self) -> None:
        text = "a b/c?d=e&f"
        encoded = encoding_ops.url_encode(text)
        self.assertEqual(encoded, "a%20b%2Fc%3Fd%3De%26f")
        self.assertEqual(encoding_ops.url_decode(encoded), text)

    def test_full_url_preserves_reserved_chars(self) -> None:
        url = "https://example.com/a b?x=1&y=2"
        encoded = encoding_ops.url_encode(url, full_url=True)
        self.assertEqual(encoded, "https://example.com/a%20b?x=1&y=2")
        self.assertEqual(encoding_ops.url_decode(encoded), url)


class HtmlOpsTests(unittest.TestCase):
    def test_encode_decode_named_entities_roundtrip(self) -> None:
        text = "<script>alert('x & y')</script>"
        encoded = encoding_ops.html_encode(text)
        self.assertNotIn("<", encoded)
        self.assertEqual(encoding_ops.html_decode(encoded), text)

    def test_numeric_character_references(self) -> None:
        text = "café <b>"
        encoded = encoding_ops.html_encode_numeric(text)
        self.assertIn("&#233;", encoded)
        self.assertIn("&lt;b&gt;", encoded)
        self.assertEqual(encoding_ops.html_decode(encoded), text)


class HexOpsTests(unittest.TestCase):
    def test_encode_decode_text_continuous(self) -> None:
        encoded = encoding_ops.hex_encode_text("Hi!")
        self.assertEqual(encoded, "486921")
        self.assertEqual(encoding_ops.hex_decode_text(encoded), "Hi!")

    def test_encode_decode_text_spaced(self) -> None:
        encoded = encoding_ops.hex_encode_text("Hi!", spaced=True)
        self.assertEqual(encoded, "48 69 21")
        self.assertEqual(encoding_ops.hex_decode_text(encoded), "Hi!")

    def test_decode_invalid_hex_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            encoding_ops.hex_decode_text("zzz")
        with self.assertRaises(ValueError):
            encoding_ops.hex_decode_text("abc")  # odd length

    def test_encode_decode_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "source.bin")
            payload = bytes(range(256))
            with open(src, "wb") as f:
                f.write(payload)

            encoded = encoding_ops.hex_encode_file(src, spaced=True)
            out = os.path.join(td, "out.bin")
            encoding_ops.hex_decode_to_file(encoded, out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), payload)


class BinaryOpsTests(unittest.TestCase):
    def test_encode_decode_bytes_spaced(self) -> None:
        data = b"AB"
        encoded = encoding_ops.binary_encode_bytes(data)
        self.assertEqual(encoded, "01000001 01000010")
        self.assertEqual(encoding_ops.binary_decode_to_bytes(encoded), data)

    def test_encode_decode_bytes_continuous(self) -> None:
        data = b"AB"
        encoded = encoding_ops.binary_encode_bytes(data, spaced=False)
        self.assertEqual(encoded, "0100000101000010")
        self.assertEqual(encoding_ops.binary_decode_to_bytes(encoded), data)

    def test_decode_invalid_binary_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            encoding_ops.binary_decode_to_bytes("0101")  # not a multiple of 8
        with self.assertRaises(ValueError):
            encoding_ops.binary_decode_to_bytes("0000000x")  # non-binary digit

    def test_encode_decode_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "source.bin")
            payload = bytes(range(256))
            with open(src, "wb") as f:
                f.write(payload)

            encoded = encoding_ops.binary_encode_file(src)
            out = os.path.join(td, "out.bin")
            encoding_ops.binary_decode_to_file(encoded, out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), payload)


if __name__ == "__main__":
    unittest.main()
