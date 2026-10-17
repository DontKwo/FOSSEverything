"""Tests for Text Tools operations (case conversion, cleanup, line ops, conversions)."""
import pytest

from app.features.text_tools import ops as text_tools_ops


def test_to_uppercase() -> None:
    assert text_tools_ops.to_uppercase("Hello World") == "HELLO WORLD"
    assert text_tools_ops.to_uppercase("") == ""


def test_to_lowercase() -> None:
    assert text_tools_ops.to_lowercase("Hello World") == "hello world"
    assert text_tools_ops.to_lowercase("") == ""


def test_to_title_case() -> None:
    assert text_tools_ops.to_title_case("hello world") == "Hello World"
    assert text_tools_ops.to_title_case("") == ""


def test_to_sentence_case() -> None:
    assert text_tools_ops.to_sentence_case("hello WORLD. this IS a test.") == "Hello world. This is a test."
    assert text_tools_ops.to_sentence_case("") == ""


def test_to_camel_case() -> None:
    assert text_tools_ops.to_camel_case("hello world example") == "helloWorldExample"
    assert text_tools_ops.to_camel_case("snake_case_value") == "snakeCaseValue"
    assert text_tools_ops.to_camel_case("") == ""


def test_to_snake_case() -> None:
    assert text_tools_ops.to_snake_case("Hello World Example") == "hello_world_example"
    assert text_tools_ops.to_snake_case("camelCaseValue") == "camel_case_value"
    assert text_tools_ops.to_snake_case("") == ""


def test_to_kebab_case() -> None:
    assert text_tools_ops.to_kebab_case("Hello World Example") == "hello-world-example"
    assert text_tools_ops.to_kebab_case("") == ""


def test_to_constant_case() -> None:
    assert text_tools_ops.to_constant_case("hello world example") == "HELLO_WORLD_EXAMPLE"
    assert text_tools_ops.to_constant_case("") == ""


def test_reverse_characters() -> None:
    assert text_tools_ops.reverse_characters("abc") == "cba"
    assert text_tools_ops.reverse_characters("") == ""


def test_reverse_words() -> None:
    assert text_tools_ops.reverse_words("one two three") == "three two one"
    assert text_tools_ops.reverse_words("") == ""


def test_reverse_lines() -> None:
    assert text_tools_ops.reverse_lines("a\nb\nc") == "c\nb\na"
    assert text_tools_ops.reverse_lines("") == ""


def test_trim_trailing_whitespace() -> None:
    assert text_tools_ops.trim_trailing_whitespace("hello   \nworld\t\t") == "hello\nworld"
    assert text_tools_ops.trim_trailing_whitespace("") == ""


def test_trim_leading_whitespace() -> None:
    assert text_tools_ops.trim_leading_whitespace("   hello\n\tworld") == "hello\nworld"
    assert text_tools_ops.trim_leading_whitespace("") == ""


def test_collapse_spaces() -> None:
    assert text_tools_ops.collapse_spaces("a    b  c") == "a b c"
    assert text_tools_ops.collapse_spaces("") == ""


def test_remove_blank_lines() -> None:
    assert text_tools_ops.remove_blank_lines("a\n\n  \nb\nc") == "a\nb\nc"
    assert text_tools_ops.remove_blank_lines("") == ""


def test_tabs_to_spaces() -> None:
    assert text_tools_ops.tabs_to_spaces("\ta", width=4) == "    a"
    assert text_tools_ops.tabs_to_spaces("", width=4) == ""


def test_spaces_to_tabs() -> None:
    assert text_tools_ops.spaces_to_tabs("    a", width=4) == "\ta"
    assert text_tools_ops.spaces_to_tabs("      a", width=4) == "\t  a"
    with pytest.raises(ValueError):
        text_tools_ops.spaces_to_tabs("a", width=0)


def test_normalize_line_endings() -> None:
    assert text_tools_ops.normalize_line_endings("a\r\nb\rc\n", style="lf") == "a\nb\nc\n"
    assert text_tools_ops.normalize_line_endings("a\nb", style="crlf") == "a\r\nb"
    assert text_tools_ops.normalize_line_endings("a\nb", style="cr") == "a\rb"
    with pytest.raises(ValueError):
        text_tools_ops.normalize_line_endings("a\nb", style="bogus")


def test_sort_lines() -> None:
    assert text_tools_ops.sort_lines("banana\napple\ncherry") == "apple\nbanana\ncherry"
    assert text_tools_ops.sort_lines("banana\napple\ncherry", reverse=True) == "cherry\nbanana\napple"
    assert text_tools_ops.sort_lines("") == ""


def test_dedupe_lines() -> None:
    assert text_tools_ops.dedupe_lines("a\nb\na\nc\nb") == "a\nb\nc"
    assert text_tools_ops.dedupe_lines("") == ""


def test_number_lines() -> None:
    assert text_tools_ops.number_lines("a\nb\nc") == "1. a\n2. b\n3. c"
    assert text_tools_ops.number_lines("") == "1. "


def test_add_prefix_suffix() -> None:
    assert text_tools_ops.add_prefix_suffix("a\nb", prefix="[", suffix="]") == "[a]\n[b]"
    assert text_tools_ops.add_prefix_suffix("", prefix="[", suffix="]") == "[]"


def test_join_lines() -> None:
    assert text_tools_ops.join_lines("a\nb\nc", delimiter=",") == "a,b,c"
    assert text_tools_ops.join_lines("", delimiter=",") == ""


def test_split_text() -> None:
    assert text_tools_ops.split_text("a,b,c", delimiter=",") == "a\nb\nc"
    with pytest.raises(ValueError):
        text_tools_ops.split_text("a,b,c", delimiter="")


def test_text_to_code_points() -> None:
    assert text_tools_ops.text_to_code_points("AB") == "65 66"
    assert text_tools_ops.text_to_code_points("") == ""


def test_code_points_to_text() -> None:
    assert text_tools_ops.code_points_to_text("65 66") == "AB"
    with pytest.raises(ValueError):
        text_tools_ops.code_points_to_text("65 notanumber")


def test_text_to_binary() -> None:
    assert text_tools_ops.text_to_binary("A") == "01000001"
    assert text_tools_ops.text_to_binary("") == ""


def test_binary_to_text() -> None:
    assert text_tools_ops.binary_to_text("01000001") == "A"
    with pytest.raises(ValueError):
        text_tools_ops.binary_to_text("101")
    with pytest.raises(ValueError):
        text_tools_ops.binary_to_text("0000000A")


def test_ascii_binary_round_trip() -> None:
    original = "Hello, World! 123"
    assert text_tools_ops.code_points_to_text(text_tools_ops.text_to_code_points(original)) == original
    assert text_tools_ops.binary_to_text(text_tools_ops.text_to_binary(original)) == original


def test_regex_replace() -> None:
    assert text_tools_ops.regex_replace("hello world", r"o", "0") == "hell0 w0rld"
    assert text_tools_ops.regex_replace("HELLO", r"hello", "hi", ignore_case=True) == "hi"
    assert text_tools_ops.regex_replace("a.b.c", r"^.$", "X", multiline=True) == "a.b.c"
    assert text_tools_ops.regex_replace("a\nb", r"a.b", "X", dotall=True) == "X"
    with pytest.raises(ValueError):
        text_tools_ops.regex_replace("abc", r"[", "x")


def test_diff_texts() -> None:
    result = text_tools_ops.diff_texts("a\nb\nc", "a\nx\nc")
    assert result["changed"] is True
    assert result["added"] == 1
    assert result["removed"] == 1

    same = text_tools_ops.diff_texts("a\nb", "a\nb")
    assert same["changed"] is False
    assert same["added"] == 0
    assert same["removed"] == 0
