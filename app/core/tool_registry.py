"""Offline search and registration for FOSSEverything capabilities.

The search implementation is deliberately independent of Qt and individual
workspaces. A future PDF, media, data, or resume tool only needs to register a
definition with plain-language keywords to become globally discoverable.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
import re


_WORD_RE = re.compile(r"[a-z0-9]+")

# These are intent aliases, not a hidden cloud/AI dependency. Keep the list
# small and understandable; each new workspace can add clear user language.
_TERM_ALIASES = {
    "combine": {"combine", "merge", "join", "append"},
    "convert": {"convert", "conversion", "format", "export", "transcode"},
    "crop": {"crop", "trim", "cut"},
    "image": {"image", "photo", "picture", "graphic"},
    "open": {"open", "view", "viewer", "preview"},
    "reduce": {"reduce", "shrink", "compress", "compression"},
    "resize": {"resize", "scale", "dimensions", "dimension"},
    "save": {"save", "export", "write", "download"},
    "split": {"split", "separate", "extract", "divide"},
}


def _tokens(value: str) -> tuple[str, ...]:
    """Normalize user-facing text into searchable lower-case words."""
    return tuple(_WORD_RE.findall(value.lower()))


def _aliases(word: str) -> set[str]:
    """Return the synonym group containing *word*, including itself."""
    for aliases in _TERM_ALIASES.values():
        if word in aliases:
            return aliases
    return {word}


def text_matches(text: str, query: str) -> bool:
    """Alias- and prefix-aware check that every query word appears in *text*."""
    words = _tokens(query)
    if not words:
        return True
    tokens = _tokens(text)
    for word in words:
        aliases = _aliases(word)
        if not any(token in aliases or any(token.startswith(alias) for alias in aliases) for token in tokens):
            return False
    return True


@dataclass(frozen=True)
class ToolDefinition:
    """A user-invokable capability exposed by one FOSSEverything workspace."""

    id: str
    title: str
    category: str
    keywords: tuple[str, ...]
    activate: Callable[[], None]
    description: str = ""

    @property
    def search_text(self) -> str:
        return " ".join((self.title, self.category, self.description, *self.keywords)).lower()


@dataclass(frozen=True)
class SearchResult:
    """A ranked match returned by :class:`ToolRegistry`."""

    tool: ToolDefinition
    score: int


class ToolRegistry:
    """Register capabilities and find them with local intent-aware search."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.id in self._tools:
            raise ValueError(f"A tool is already registered as {tool.id!r}")
        self._tools[tool.id] = tool

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        """Search registered tools without network calls.

        Queries match title, category, keywords, and description. Words are
        ANDed so a search like ``convert image`` stays useful. Exact title and
        keyword matches rank above description matches; close spellings are
        accepted for words of four or more characters. Prefix a query with a
        workspace name (``pdf:`` or ``images:``) to limit that category.
        """
        category, words = self._parse_query(query)
        if not words:
            results = [SearchResult(tool, 0) for tool in self.all() if self._in_category(tool, category)]
            return results[:limit] if limit else results

        results = []
        for tool in self.all():
            if not self._in_category(tool, category):
                continue
            result = self._score(tool, words)
            if result is not None:
                results.append(result)
        results.sort(key=lambda item: (-item.score, item.tool.title.lower(), item.tool.id))
        return results[:limit] if limit else results

    @staticmethod
    def _parse_query(query: str) -> tuple[str | None, tuple[str, ...]]:
        raw_words = query.lower().split()
        category = None
        words = []
        for raw_word in raw_words:
            if raw_word.endswith(":"):
                candidate = raw_word[:-1]
                if candidate in {"pdf", "image", "images", "media", "data", "text", "resume"}:
                    category = "Images" if candidate == "image" else candidate.title()
                    continue
            words.extend(_tokens(raw_word))
        return category, tuple(words)

    @staticmethod
    def _in_category(tool: ToolDefinition, category: str | None) -> bool:
        return category is None or tool.category.lower() == category.lower()

    def _score(self, tool: ToolDefinition, words: tuple[str, ...]) -> SearchResult | None:
        title_tokens = _tokens(tool.title)
        keyword_tokens = _tokens(" ".join(tool.keywords))
        category_tokens = _tokens(tool.category)
        description_tokens = _tokens(tool.description)
        all_tokens = title_tokens + keyword_tokens + category_tokens + description_tokens
        score = 0
        for word in words:
            match_score = self._word_score(word, title_tokens, keyword_tokens, category_tokens, description_tokens)
            if match_score == 0:
                return None
            score += match_score

        normalized_query = " ".join(words)
        if normalized_query == tool.title.lower():
            score += 250
        elif normalized_query in tool.title.lower():
            score += 100
        # A small deterministic tie-breaker rewards compact, focused tool names.
        score += max(0, 20 - len(all_tokens))
        return SearchResult(tool=tool, score=score)

    @staticmethod
    def _word_score(
        word: str,
        title_tokens: tuple[str, ...],
        keyword_tokens: tuple[str, ...],
        category_tokens: tuple[str, ...],
        description_tokens: tuple[str, ...],
    ) -> int:
        aliases = _aliases(word)
        fields = ((title_tokens, 80), (keyword_tokens, 55), (category_tokens, 35), (description_tokens, 20))
        for tokens, weight in fields:
            if any(token in aliases for token in tokens):
                return weight
            if any(any(token.startswith(alias) for alias in aliases) for token in tokens):
                return weight - 10

        # Typo tolerance: only for words >= 4 chars, after exact/synonym/prefix matches.
        # Avoids noisy matches like "p" or "to".
        if len(word) >= 4:
            best = max((SequenceMatcher(None, word, token).ratio() for token in (*title_tokens, *keyword_tokens)), default=0)
            if best >= 0.78:
                return 25
        return 0
