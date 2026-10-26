from typing import Any

from app.features.text_tools.ops import (
    add_prefix_suffix,
    binary_to_text,
    code_points_to_text,
    collapse_spaces,
    dedupe_lines,
    diff_texts,
    join_lines,
    normalize_line_endings,
    number_lines,
    regex_replace,
    remove_blank_lines,
    reverse_characters,
    reverse_lines,
    reverse_words,
    sort_lines,
    spaces_to_tabs,
    split_text,
    tabs_to_spaces,
    text_to_binary,
    text_to_code_points,
    to_camel_case,
    to_constant_case,
    to_kebab_case,
    to_lowercase,
    to_sentence_case,
    to_snake_case,
    to_title_case,
    to_uppercase,
    trim_leading_whitespace,
    trim_trailing_whitespace,
)
from app.web.api.result import api_method, fail, ok, require


class TextToolsApiMixin:
    @api_method
    def text_tools_case(self, params: dict[str, Any]) -> dict[str, Any]:
        # Transform letter casing of input string.
        require(params, "text", "mode")
        text = str(params["text"])
        mode = str(params["mode"]).lower()
        if mode in ("upper", "uppercase"):
            res = to_uppercase(text)
        elif mode in ("lower", "lowercase"):
            res = to_lowercase(text)
        elif mode in ("title", "titlecase"):
            res = to_title_case(text)
        elif mode in ("sentence", "sentencecase"):
            res = to_sentence_case(text)
        elif mode in ("camel", "camelcase"):
            res = to_camel_case(text)
        elif mode in ("snake", "snakecase"):
            res = to_snake_case(text)
        elif mode in ("kebab", "kebabcase"):
            res = to_kebab_case(text)
        elif mode in ("constant", "constantcase"):
            res = to_constant_case(text)
        else:
            return fail(f"Unsupported case mode: {mode}", code="InvalidMode")
        return ok(result=res)

    @api_method
    def text_case_transform(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for text casing conversion.
        return self.text_tools_case(params)

    @api_method
    def text_tools_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform line-oriented text operations.
        require(params, "text", "operation")
        text = str(params["text"])
        op = str(params["operation"]).lower()

        if op == "sort_asc":
            res = sort_lines(text, reverse=False)
        elif op == "sort_desc":
            res = sort_lines(text, reverse=True)
        elif op == "reverse":
            res = reverse_lines(text)
        elif op == "dedupe":
            res = dedupe_lines(text)
        elif op == "number":
            res = number_lines(text, start=int(params.get("start", 1)))
        elif op == "prefix_suffix":
            res = add_prefix_suffix(text, prefix=str(params.get("prefix", "")), suffix=str(params.get("suffix", "")))
        elif op == "remove_blank":
            res = remove_blank_lines(text)
        elif op == "join":
            delimiter = str(params.get("delimiter", ","))
            res = join_lines(text, delimiter=delimiter)
        elif op == "split":
            delimiter = str(params.get("delimiter", ","))
            res = split_text(text, delimiter=delimiter)
        else:
            return fail(f"Unsupported line operation: {op}", code="InvalidOperation")
        return ok(result=res)

    @api_method
    def text_line_ops(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for line operations.
        return self.text_tools_lines(params)

    @api_method
    def text_tools_cleanup(self, params: dict[str, Any]) -> dict[str, Any]:
        # Clean up whitespace and line endings in text.
        require(params, "text", "operation")
        text = str(params["text"])
        op = str(params["operation"]).lower()

        if op == "collapse_spaces":
            res = collapse_spaces(text)
        elif op == "trim_leading":
            res = trim_leading_whitespace(text)
        elif op == "trim_trailing":
            res = trim_trailing_whitespace(text)
        elif op == "tabs_to_spaces":
            res = tabs_to_spaces(text, width=int(params.get("width", params.get("tab_size", 4))))
        elif op == "spaces_to_tabs":
            res = spaces_to_tabs(text, width=int(params.get("width", params.get("tab_size", 4))))
        elif op == "normalize_line_endings":
            style_str = str(params.get("style", params.get("ending", "lf"))).lower()
            if style_str == "\r\n":
                style_str = "crlf"
            elif style_str == "\r":
                style_str = "cr"
            elif style_str == "\n":
                style_str = "lf"
            res = normalize_line_endings(text, style=style_str)
        else:
            return fail(f"Unsupported cleanup operation: {op}", code="InvalidOperation")
        return ok(result=res)

    @api_method
    def text_tools_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert text representation formats.
        require(params, "text", "operation")
        text = str(params["text"])
        op = str(params["operation"]).lower()

        if op == "reverse_characters":
            res = reverse_characters(text)
        elif op == "reverse_words":
            res = reverse_words(text)
        elif op == "text_to_binary":
            res = text_to_binary(text)
        elif op == "binary_to_text":
            res = binary_to_text(text)
        elif op == "text_to_code_points":
            res = text_to_code_points(text)
        elif op == "code_points_to_text":
            res = code_points_to_text(text)
        else:
            return fail(f"Unsupported conversion: {op}", code="InvalidOperation")
        return ok(result=res)

    @api_method
    def text_tools_regex_replace(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform regular expression search and replace.
        require(params, "text", "pattern", "replacement")
        res, count = regex_replace(
            str(params["text"]),
            str(params["pattern"]),
            str(params["replacement"]),
            ignore_case=bool(params.get("ignore_case", False)),
            multiline=bool(params.get("multiline", False)),
            dotall=bool(params.get("dotall", False)),
        )
        return ok(result=res, count=count)

    @api_method
    def text_regex_replace(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for regex replace.
        return self.text_tools_regex_replace(params)

    @api_method
    def text_tools_diff(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute differences between two strings.
        require(params, "text1", "text2")
        diff_res = diff_texts(str(params["text1"]), str(params["text2"]))
        return ok(diff=diff_res["diff"], additions=diff_res["added"], deletions=diff_res["removed"])

    @api_method
    def text_diff(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for text diff computation.
        return self.text_tools_diff(params)
