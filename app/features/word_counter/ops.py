"""Word count, document statistics, readability scores, and keyword density analytics."""
from __future__ import annotations

import re
import os
from collections import Counter
from typing import Any

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's",
    "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves"
}


def count_syllables_in_word(word: str) -> int:
    """Heuristic syllable counter for English words."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove non-alpha
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0

    # Common suffixes that don't add syllables
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel sequences
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel

    return max(1, count)


def analyze_text(text: str, reading_wpm: int = 225, speaking_wpm: int = 135) -> dict:
    """Compute comprehensive word count, readability, and structural stats."""
    raw = text or ""
    trimmed = raw.strip()

    if not trimmed:
        return {
            "words": 0,
            "characters": len(raw),
            "characters_no_spaces": 0,
            "sentences": 0,
            "paragraphs": 0,
            "lines": 0,
            "pages_est": 0.0,
            "reading_time_secs": 0,
            "speaking_time_secs": 0,
            "flesch_reading_ease": 100.0,
            "flesch_kincaid_grade": 0.0,
            "readability_label": "N/A",
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "top_keywords": [],
        }

    # Words
    word_tokens = re.findall(r"\b[\w'-]+\b", trimmed)
    word_count = len(word_tokens)

    # Characters
    char_count = len(raw)
    char_no_spaces = len(re.sub(r"\s", "", raw))

    # Paragraphs (non-empty blocks)
    paragraphs = [p for p in re.split(r"\n\s*\n", trimmed) if p.strip()]
    para_count = max(1, len(paragraphs))

    # Lines
    lines = raw.splitlines()
    line_count = len(lines)

    # Sentences
    sentence_tokens = [s for s in re.split(r"[.!?]+(\s+|$)", trimmed) if s.strip()]
    sentence_count = max(1, len(sentence_tokens))

    # Syllables
    total_syllables = sum(count_syllables_in_word(w) for w in word_tokens)

    # Reading & Speaking Time
    reading_mins = word_count / max(50, reading_wpm)
    speaking_mins = word_count / max(50, speaking_wpm)
    reading_secs = int(reading_mins * 60)
    speaking_secs = int(speaking_mins * 60)

    # Page estimate (~275 words per standard single-spaced page)
    pages_est = round(word_count / 275.0, 1)

    # Averages
    avg_word_len = round(char_no_spaces / max(1, word_count), 1)
    avg_sent_len = round(word_count / sentence_count, 1)

    # Flesch-Kincaid & Reading Ease
    if word_count > 0:
        words_per_sent = word_count / sentence_count
        syll_per_word = total_syllables / word_count

        fre = 206.835 - (1.015 * words_per_sent) - (84.6 * syll_per_word)
        fre = max(0.0, min(100.0, fre))

        fkgl = (0.39 * words_per_sent) + (11.8 * syll_per_word) - 15.59
        fkgl = max(0.0, round(fkgl, 1))
    else:
        fre = 100.0
        fkgl = 0.0

    if fre >= 90:
        read_label = "Very Easy (5th Grade)"
    elif fre >= 80:
        read_label = "Easy (6th Grade)"
    elif fre >= 70:
        read_label = "Fairly Easy (7th Grade)"
    elif fre >= 60:
        read_label = "Plain English (8th-9th Grade)"
    elif fre >= 50:
        read_label = "Fairly Difficult (10th-12th Grade)"
    elif fre >= 30:
        read_label = "Difficult (College)"
    else:
        read_label = "Very Difficult (Graduate Level)"

    # Top keywords
    clean_words = [w.lower() for w in word_tokens if len(w) > 2 and w.lower() not in STOP_WORDS]
    counts = Counter(clean_words)
    top_kw = []
    for word, cnt in counts.most_common(12):
        density = round((cnt / max(1, word_count)) * 100, 1)
        top_kw.append({"word": word, "count": cnt, "density_pct": density})

    return {
        "words": word_count,
        "characters": char_count,
        "characters_no_spaces": char_no_spaces,
        "sentences": sentence_count,
        "paragraphs": para_count,
        "lines": line_count,
        "pages_est": pages_est,
        "reading_time_secs": reading_secs,
        "speaking_time_secs": speaking_secs,
        "flesch_reading_ease": round(fre, 1),
        "flesch_kincaid_grade": fkgl,
        "readability_label": read_label,
        "avg_word_length": avg_word_len,
        "avg_sentence_length": avg_sent_len,
        "top_keywords": top_kw,
    }


def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from any document: PDF, Office, or text format."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        import pymupdf  # noqa: 13 (deferred: only needed for .pdf input)
        text_parts = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n\n".join(text_parts)

    from app.features.office import ops as office_ops
    if ext in office_ops.OFFICE_EXTENSIONS:
        return office_ops.extract_text_from_office(file_path)

    # Text / Code / Markdown
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def generate_report(stats: dict[str, Any]) -> str:
    """Generate human-readable text report from document analysis statistics."""
    r_secs = int(stats.get("reading_time_secs", 0))
    s_secs = int(stats.get("speaking_time_secs", 0))
    r_str = f"{r_secs // 60}m {r_secs % 60}s" if r_secs >= 60 else f"{r_secs}s"
    s_str = f"{s_secs // 60}m {s_secs % 60}s" if s_secs >= 60 else f"{s_secs}s"
    lines = [
        "--- Word Counter & Text Analytics Report ---",
        f"Words:                  {stats.get('words', 0):,}",
        f"Characters:             {stats.get('characters', 0):,}",
        f"Characters (no spaces): {stats.get('characters_no_spaces', 0):,}",
        f"Sentences:              {stats.get('sentences', 0):,}",
        f"Paragraphs:             {stats.get('paragraphs', 0):,}",
        f"Lines:                  {stats.get('lines', 0):,}",
        f"Estimated Pages:        ~{stats.get('pages_est', 0.0)}",
        f"Reading Time:           {r_str}",
        f"Speaking Time:          {s_str}",
        f"Flesch Reading Ease:    {stats.get('flesch_reading_ease', 0.0)} / 100",
        f"Reading Level:          Grade {stats.get('flesch_kincaid_grade', 0.0)} ({stats.get('readability_label', 'N/A')})",
        f"Avg. Word Length:       {stats.get('avg_word_length', 0.0)} chars",
        f"Avg. Sentence Length:   {stats.get('avg_sentence_length', 0.0)} words",
        "",
        "Top Keywords & Density:",
    ]
    for item in stats.get("top_keywords", []):
        lines.append(f"  - {item['word']}: {item['count']} ({item['density_pct']}%)")
    return "\n".join(lines)
