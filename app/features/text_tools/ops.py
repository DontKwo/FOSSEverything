"""Headless text manipulation: case conversion, reversal, cleanup, line ops, and conversions."""
from __future__ import annotations

import difflib
import re


def _split_words(text: str) -> list[str]:
    """Split text into word tokens, handling camelCase, snake_case, kebab-case, and spaces."""
    spaced = re.sub(r"[_\-]+", " ", text)
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", spaced)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [word for word in re.split(r"\s+", spaced.strip()) if word]


def to_uppercase(text: str) -> str:
    """Convert all characters to UPPERCASE."""
    return text.upper()


def to_lowercase(text: str) -> str:
    """Convert all characters to lowercase."""
    return text.lower()


def to_title_case(text: str) -> str:
    """Convert text to Title Case."""
    return text.title()


def to_sentence_case(text: str) -> str:
    """Lowercase the text and capitalize the first letter of each sentence."""
    lowered = text.lower()

    def _cap(match: re.Match) -> str:
        return match.group(1) + match.group(2).upper()

    return re.sub(r"(^\s*|[.!?]\s+)([a-z])", _cap, lowered)


def to_camel_case(text: str) -> str:
    """Convert text to camelCase."""
    words = _split_words(text)
    if not words:
        return ""
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


def to_snake_case(text: str) -> str:
    """Convert text to snake_case."""
    return "_".join(word.lower() for word in _split_words(text))


def to_kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    return "-".join(word.lower() for word in _split_words(text))


def to_constant_case(text: str) -> str:
    """Convert text to CONSTANT_CASE."""
    return "_".join(word.upper() for word in _split_words(text))


def reverse_characters(text: str) -> str:
    """Reverse every character in the text."""
    return text[::-1]


def reverse_words(text: str) -> str:
    """Reverse the order of words on each line."""
    lines = text.split("\n")
    return "\n".join(" ".join(line.split()[::-1]) for line in lines)


def reverse_lines(text: str) -> str:
    """Reverse the order of lines in the text."""
    return "\n".join(text.split("\n")[::-1])


def trim_trailing_whitespace(text: str) -> str:
    """Trim trailing whitespace from every line."""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def trim_leading_whitespace(text: str) -> str:
    """Trim leading whitespace from every line."""
    return "\n".join(line.lstrip() for line in text.split("\n"))


def collapse_spaces(text: str) -> str:
    """Collapse runs of multiple spaces down to a single space."""
    return re.sub(r" {2,}", " ", text)


def remove_blank_lines(text: str) -> str:
    """Remove empty or whitespace-only lines."""
    return "\n".join(line for line in text.split("\n") if line.strip())


def tabs_to_spaces(text: str, width: int = 4) -> str:
    """Convert tab characters to spaces using the given tab width, per line."""
    return "\n".join(line.expandtabs(width) for line in text.split("\n"))


def spaces_to_tabs(text: str, width: int = 4) -> str:
    """Convert each line's leading run of spaces to tab characters using the given width."""
    if width <= 0:
        raise ValueError("Tab width must be a positive integer.")
    converted = []
    for line in text.split("\n"):
        stripped = line.lstrip(" ")
        leading_len = len(line) - len(stripped)
        num_tabs, remainder = divmod(leading_len, width)
        converted.append(("\t" * num_tabs) + (" " * remainder) + stripped)
    return "\n".join(converted)


def normalize_line_endings(text: str, style: str = "lf") -> str:
    """Normalize all line endings in the text to lf, crlf, or cr."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    style = style.lower()
    if style == "lf":
        return normalized
    if style == "crlf":
        return normalized.replace("\n", "\r\n")
    if style == "cr":
        return normalized.replace("\n", "\r")
    raise ValueError(f"Unsupported line ending style: {style}")


def sort_lines(text: str, reverse: bool = False) -> str:
    """Sort lines alphabetically, optionally in reverse order."""
    return "\n".join(sorted(text.split("\n"), reverse=reverse))


def dedupe_lines(text: str) -> str:
    """Remove duplicate lines, keeping the first occurrence of each."""
    seen: set[str] = set()
    result = []
    for line in text.split("\n"):
        if line not in seen:
            seen.add(line)
            result.append(line)
    return "\n".join(result)


def number_lines(text: str, start: int = 1) -> str:
    """Prepend a sequential number (e.g. '1. ') to every line."""
    lines = text.split("\n")
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, start=start))


def add_prefix_suffix(text: str, prefix: str = "", suffix: str = "") -> str:
    """Add a prefix and/or suffix to every line."""
    return "\n".join(f"{prefix}{line}{suffix}" for line in text.split("\n"))


def join_lines(text: str, delimiter: str = ",") -> str:
    """Join all lines into a single line using the given delimiter."""
    return delimiter.join(text.split("\n"))


def split_text(text: str, delimiter: str = ",") -> str:
    """Split delimiter-separated text into separate lines."""
    if delimiter == "":
        raise ValueError("Delimiter cannot be empty.")
    return "\n".join(text.split(delimiter))


def text_to_code_points(text: str) -> str:
    """Convert text to a space-separated list of decimal Unicode code points."""
    return " ".join(str(ord(ch)) for ch in text)


def code_points_to_text(code_points_str: str) -> str:
    """Convert a space-separated list of decimal code points back to text."""
    tokens = code_points_str.split()
    try:
        return "".join(chr(int(tok)) for tok in tokens)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid code point list: {exc}") from exc


def text_to_binary(text: str) -> str:
    """Convert text to space-separated 8-bit binary octets (UTF-8 byte-wise)."""
    return " ".join(format(byte, "08b") for byte in text.encode("utf-8"))


def binary_to_text(binary_str: str) -> str:
    """Convert space-separated 8-bit binary octets back to UTF-8 text."""
    tokens = binary_str.split()
    if any(len(tok) != 8 or not set(tok) <= {"0", "1"} for tok in tokens):
        raise ValueError("Each binary token must be exactly 8 bits of 0s and 1s.")
    try:
        return bytes(int(tok, 2) for tok in tokens).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Invalid UTF-8 byte sequence: {exc}") from exc


def regex_replace(
    text: str,
    pattern: str,
    replacement: str,
    *,
    ignore_case: bool = False,
    multiline: bool = False,
    dotall: bool = False,
) -> str:
    """Apply a regex find-and-replace to text, raising a clear error for invalid patterns."""
    flags = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    if dotall:
        flags |= re.DOTALL
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc
    try:
        return compiled.sub(replacement, text)
    except re.error as exc:
        raise ValueError(f"Invalid replacement pattern: {exc}") from exc


def diff_texts(left_text: str, right_text: str) -> dict:
    """Compare two text blocks and return a unified diff plus added/removed line counts."""
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    diff_lines = list(difflib.unified_diff(left_lines, right_lines, fromfile="left", tofile="right", lineterm=""))
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return {
        "diff": "\n".join(diff_lines),
        "added": added,
        "removed": removed,
        "changed": bool(diff_lines),
    }
