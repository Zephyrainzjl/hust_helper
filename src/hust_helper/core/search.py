from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

from .models import FoodEntry, SearchResult

_CJK = re.compile(r"[㐀-鿿]")
_WORD = re.compile(r"[a-zA-Z0-9_+.-]+|[㐀-鿿]")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def tokens(text: str) -> list[str]:
    normalized = normalize(text)
    base = _WORD.findall(normalized)
    cjk = "".join(char for char in normalized if _CJK.match(char))
    bigrams = [cjk[i : i + 2] for i in range(max(0, len(cjk) - 1))]
    return list(dict.fromkeys([*base, *bigrams]))


@dataclass(slots=True)
class SearchFilters:
    chapter: str | None = None
    section: str | None = None
    category: str | None = None
    venue_type: str | None = None
    meal_period: str | None = None
    visited: str | None = None
    has_images: bool | None = None
    spicy: bool | None = None
    tags: list[str] = field(default_factory=list)

    def matches(self, entry: FoodEntry) -> bool:
        checks = [
            (self.chapter, entry.chapter_title),
            (self.section, entry.section_title),
            (self.category, entry.category),
            (self.venue_type, entry.venue_type),
            (self.visited, entry.author_visit_status),
        ]
        for expected, actual in checks:
            if expected and normalize(expected) not in normalize(actual):
                return False
        if self.meal_period and self.meal_period not in entry.meal_periods:
            return False
        if self.has_images is not None and bool(entry.media_ids) is not self.has_images:
            return False
        if self.spicy is not None and bool(entry.spice_notes) is not self.spicy:
            return False
        if self.tags:
            haystack = normalize(" ".join(entry.tags))
            if not all(normalize(tag) in haystack for tag in self.tags):
                return False
        return True


class FoodSearchEngine:
    def __init__(self, entries: Iterable[FoodEntry]) -> None:
        self.entries = list(entries)
        self._index = {entry.id: entry.searchable_text() for entry in self.entries}

    def search(
        self,
        query: str = "",
        *,
        filters: SearchFilters | None = None,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        filters = filters or SearchFilters()
        query_n = normalize(query)
        query_tokens = tokens(query_n)
        results: list[SearchResult] = []
        for entry in self.entries:
            if not filters.matches(entry):
                continue
            if not query_n:
                score = 1.0 + (0.2 if entry.recommended_items else 0.0)
                results.append(SearchResult(entry, score, ["filter match"]))
                continue
            text = self._index[entry.id]
            name = normalize(entry.name)
            recommendations = normalize(" ".join(entry.recommended_items))
            score = 0.0
            reasons: list[str] = []
            if query_n == name:
                score += 100
                reasons.append("exact name")
            elif query_n in name:
                score += 60
                reasons.append("name contains query")
            if query_n in recommendations:
                score += 45
                reasons.append("recommended dish match")
            if query_n in text:
                score += 25
                reasons.append("exact text match")
            matched = sum(1 for token in query_tokens if token and token in text)
            if query_tokens:
                score += 30 * matched / len(query_tokens)
                if matched:
                    reasons.append(f"{matched}/{len(query_tokens)} token match")
            ratio = max(
                SequenceMatcher(None, query_n, name).ratio(),
                SequenceMatcher(None, query_n, recommendations[:200]).ratio(),
            )
            if ratio >= 0.42:
                score += 20 * ratio
                reasons.append("fuzzy match")
            if entry.highlighted_text or entry.recommended_items:
                score += 2
            if score >= min_score and (matched or query_n in text or ratio >= 0.42):
                results.append(SearchResult(entry, score, reasons))
        results.sort(key=lambda result: (-result.score, result.entry.name))
        return results[: max(0, limit)]
