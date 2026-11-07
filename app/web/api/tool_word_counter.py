from typing import Any

from app.features.word_counter.ops import analyze_text, extract_text_from_file, generate_report
from app.web.api.result import api_method, ok, require


def _normalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
    # Augment stats with convenience aliases for frontend cards.
    res = dict(stats)
    res["char_count"] = res.get("characters", 0)
    res["char_no_spaces"] = res.get("characters_no_spaces", 0)
    r_secs = int(res.get("reading_time_secs", 0))
    s_secs = int(res.get("speaking_time_secs", 0))
    res["reading_time_min"] = round(r_secs / 60.0, 1) if r_secs >= 60 else round(r_secs / 60.0, 2)
    res["speaking_time_min"] = round(s_secs / 60.0, 1) if s_secs >= 60 else round(s_secs / 60.0, 2)
    res["flesch_ease"] = res.get("flesch_reading_ease", 100.0)
    res["fk_grade"] = res.get("flesch_kincaid_grade", 0.0)
    res["keywords"] = res.get("top_keywords", [])
    return res


class WordCounterApiMixin:
    @api_method
    def word_counter_analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        # Analyze input text and calculate comprehensive word and readability metrics.
        text = str(params.get("text", ""))
        stats = _normalize_stats(analyze_text(text))
        return ok(**stats)

    @api_method
    def word_counter_analyze_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Read text from file and compute analytical statistics.
        require(params, "file_path")
        file_path = str(params["file_path"])
        text = extract_text_from_file(file_path)
        stats = _normalize_stats(analyze_text(text))
        return ok(text=text, **stats)

    @api_method
    def word_counter_generate_report(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate summary text report of document metrics.
        text = str(params.get("text", ""))
        raw_stats = analyze_text(text)
        stats = _normalize_stats(raw_stats)
        report_text = generate_report(raw_stats)
        return ok(report=report_text, **stats)
