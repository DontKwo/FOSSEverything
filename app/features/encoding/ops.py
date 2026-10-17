"""Encoding/decoding operations: Base64, URL/percent-encoding, HTML entities, hex, binary. No PyQt imports."""
from __future__ import annotations

import base64
import binascii
import html
import re
from urllib.parse import quote, unquote

FULL_URL_SAFE_CHARS = "/:?#[]@!$&'()*+,;="


def _b64decode(data: str, url_safe: bool) -> bytes:
    """Decode a Base64 string to raw bytes, validating the alphabet strictly."""
    payload = data.strip()
    if url_safe:
        payload = payload.translate(str.maketrans("-_", "+/"))
    try:
        return base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError(f"Invalid Base64 input: {exc}") from exc


def base64_encode_text(text: str, url_safe: bool = False) -> str:
    """Encode UTF-8 text to a Base64 string using the standard or URL-safe alphabet."""
    data = text.encode("utf-8")
    encoded = base64.urlsafe_b64encode(data) if url_safe else base64.b64encode(data)
    return encoded.decode("ascii")


def base64_decode_text(data: str, url_safe: bool = False) -> str:
    """Decode a Base64 string back to UTF-8 text."""
    raw = _b64decode(data, url_safe)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Decoded bytes are not valid UTF-8 text: {exc}") from exc


def base64_encode_file(path: str, url_safe: bool = False) -> str:
    """Encode a file's raw bytes to a Base64 string."""
    with open(path, "rb") as f:
        data = f.read()
    encoded = base64.urlsafe_b64encode(data) if url_safe else base64.b64encode(data)
    return encoded.decode("ascii")


def base64_decode_to_file(data: str, output_path: str, url_safe: bool = False) -> str:
    """Decode a Base64 string and write the resulting bytes to output_path."""
    raw = _b64decode(data, url_safe)
    with open(output_path, "wb") as f:
        f.write(raw)
    return output_path


def url_encode(text: str, full_url: bool = False) -> str:
    """Percent-encode text; full_url preserves reserved URL characters instead of a component-safe encode."""
    if full_url:
        return quote(text, safe=FULL_URL_SAFE_CHARS)
    return quote(text, safe="")


def url_decode(text: str) -> str:
    """Decode a percent-encoded string back to text."""
    return unquote(text)


def html_encode(text: str) -> str:
    """Escape text to named HTML entities (&, <, >, quotes)."""
    return html.escape(text)


def html_decode(text: str) -> str:
    """Unescape named and numeric HTML character references back to text."""
    return html.unescape(text)


def html_encode_numeric(text: str) -> str:
    """Escape reserved HTML characters and every non-ASCII character as numeric character references."""
    escaped = html.escape(text)
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in escaped)


def _space_hex_pairs(hex_str: str) -> str:
    """Insert a space between every hex byte pair."""
    return " ".join(hex_str[i:i + 2] for i in range(0, len(hex_str), 2))


def hex_encode_text(text: str, spaced: bool = False) -> str:
    """Encode UTF-8 text as a hex string, optionally space-separated by byte."""
    hex_str = binascii.hexlify(text.encode("utf-8")).decode("ascii")
    return _space_hex_pairs(hex_str) if spaced else hex_str


def hex_decode_text(hex_str: str) -> str:
    """Decode a hex string (spaced or continuous) back to UTF-8 text."""
    cleaned = "".join(hex_str.split())
    try:
        raw = binascii.unhexlify(cleaned)
    except binascii.Error as exc:
        raise ValueError(f"Invalid hex input: {exc}") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Decoded bytes are not valid UTF-8 text: {exc}") from exc


def hex_encode_file(path: str, spaced: bool = False) -> str:
    """Encode a file's raw bytes as a hex dump string."""
    with open(path, "rb") as f:
        data = f.read()
    hex_str = binascii.hexlify(data).decode("ascii")
    return _space_hex_pairs(hex_str) if spaced else hex_str


def hex_decode_to_file(hex_str: str, output_path: str) -> str:
    """Decode a hex string (spaced or continuous) and write the resulting bytes to output_path."""
    cleaned = "".join(hex_str.split())
    try:
        raw = binascii.unhexlify(cleaned)
    except binascii.Error as exc:
        raise ValueError(f"Invalid hex input: {exc}") from exc
    with open(output_path, "wb") as f:
        f.write(raw)
    return output_path


def binary_encode_bytes(data: bytes, spaced: bool = True) -> str:
    """Encode raw bytes as a base-2 string, optionally space-separated per byte."""
    octets = [format(b, "08b") for b in data]
    return " ".join(octets) if spaced else "".join(octets)


def binary_decode_to_bytes(binary_str: str) -> bytes:
    """Decode a base-2 string (spaced or continuous) back to raw bytes."""
    cleaned = "".join(binary_str.split())
    if not cleaned or len(cleaned) % 8 != 0 or not re.fullmatch(r"[01]+", cleaned):
        raise ValueError("Binary input must be a non-empty sequence of 0s and 1s, a multiple of 8 bits long.")
    return bytes(int(cleaned[i:i + 8], 2) for i in range(0, len(cleaned), 8))


def binary_encode_file(path: str, spaced: bool = True) -> str:
    """Encode a file's raw bytes as a base-2 string."""
    with open(path, "rb") as f:
        data = f.read()
    return binary_encode_bytes(data, spaced=spaced)


def binary_decode_to_file(binary_str: str, output_path: str) -> str:
    """Decode a base-2 string and write the resulting bytes to output_path."""
    raw = binary_decode_to_bytes(binary_str)
    with open(output_path, "wb") as f:
        f.write(raw)
    return output_path
