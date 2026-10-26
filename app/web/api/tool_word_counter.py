from typing import Any

from app.features.word_counter.ops import analyze_text, extract_text_from_file
from app.web.api.result import api_method, ok, require


class WordCounterApiMixin:
    @api_method
    def word_counter_analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        # Analyze input text and calculate comprehensive word and readability metrics.
        text = str(params.get("text", ""))
        stats = analyze_text(text)
        return ok(**stats)

    @api_method
    def word_counter_analyze_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Read text from file and compute analytical statistics.
        require(params, "file_path")
        file_path = str(params["file_path"])
        text = extract_text_from_file(file_path)
        stats = analyze_text(text)
        return ok(text=text, **stats)

    @api_method
    def word_counter_generate_report(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate summary text report of document metrics.
        text = str(params.get("text", ""))
        stats = analyze_text(text)
        lines = [
            f"Words: {stats.get('words', 0)}",
            f"Characters (no spaces): {stats.get('characters_no_spaces', 0)}",
            f"Characters (with spaces): {stats.get('characters_with_spaces', 0)}",
            f"Sentences: {stats.get('sentences', 0)}",
            f"Paragraphs: {stats.get('paragraphs', 0)}",
            f"Reading Time (min): {stats.get('reading_time_minutes', 0)}",
        ]
        return ok(report="\n".join(lines), **stats)
