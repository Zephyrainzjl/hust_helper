from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

from .models import FoodEntry, SearchResult

_CJK = re.compile(r"[㐀-鿿]")
_WORD = re.compile(r"[a-zA-Z0-9_+.-]+|[㐀-鿿]")
_SPICY_MARKERS = (
    "微辣",
    "中辣",
    "重辣",
    "很辣",
    "巨辣",
    "麻辣",
    "香辣",
    "辣子",
    "泡椒",
    "红油",
    "辣椒",
    "辣白菜",
    "变态辣",
    "辣个半死",
    "辣够呛",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def tokens(text: str) -> list[str]:
    normalized = normalize(text)
    base = _WORD.findall(normalized)
    cjk = "".join(char for char in normalized if _CJK.match(char))
    bigrams = [cjk[i : i + 2] for i in range(max(0, len(cjk) - 1))]
    return list(dict.fromkeys([*base, *bigrams]))


def looks_spicy(entry: FoodEntry) -> bool:
    """Conservatively identify entries with explicit spicy-food evidence.

    The extracted PDF occasionally places phrases such as "口味偏清淡" in
    ``spice_notes`` because the source paragraph discusses spice tolerance.  We
    therefore do not treat the mere existence of spice notes as proof that a
    venue is spicy; an explicit marker must be present.
    """

    haystack = normalize(
        " ".join(
            [
                *entry.spice_notes,
                *entry.recommended_items,
                entry.description,
                entry.category,
            ]
        )
    )
    return any(marker in haystack for marker in _SPICY_MARKERS)


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
    avoid_spicy: bool = False
    recommended_only: bool = False
    has_price_notes: bool | None = None
    external_recommended: bool | None = None
    min_recommendations: int = 0
    tags: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)

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
        if self.avoid_spicy and looks_spicy(entry):
            return False
        if self.recommended_only and not (entry.recommended_items or entry.highlighted_text):
            return False
        if self.has_price_notes is not None and bool(entry.price_notes) is not self.has_price_notes:
            return False
        if self.external_recommended is not None:
            is_external = "外部推荐" in entry.tags or entry.author_visit_status == "not_visited_by_author"
            if is_external is not self.external_recommended:
                return False
        if len(entry.recommended_items) < max(0, self.min_recommendations):
            return False
        if self.tags:
            haystack = normalize(" ".join(entry.tags))
            if not all(normalize(tag) in haystack for tag in self.tags):
                return False
        if self.exclude_terms:
            searchable = normalize(entry.searchable_text())
            if any(normalize(term) in searchable for term in self.exclude_terms if term.strip()):
                return False
        return True


class FoodSearchEngine:
    def __init__(self, entries: Iterable[FoodEntry]) -> None:
        self.entries = list(entries)
        self._index = {entry.id: entry.searchable_text() for entry in self.entries}

    @staticmethod
    def _sort(results: list[SearchResult], sort_by: str) -> None:
        if sort_by == "name":
            results.sort(key=lambda result: result.entry.name)
        elif sort_by == "source_page":
            results.sort(
                key=lambda result: (
                    result.entry.source_pages[0] if result.entry.source_pages else 10**9,
                    result.entry.name,
                )
            )
        elif sort_by == "visited":
            rank = {"visited_by_author": 0, "unspecified": 1, "not_visited_by_author": 2}
            results.sort(
                key=lambda result: (
                    rank.get(result.entry.author_visit_status, 3),
                    -result.score,
                    result.entry.name,
                )
            )
        elif sort_by == "recommendations":
            results.sort(
                key=lambda result: (
                    -len(result.entry.recommended_items),
                    -result.score,
                    result.entry.name,
                )
            )
        else:
            results.sort(key=lambda result: (-result.score, result.entry.name))

    def search(
        self,
        query: str = "",
        *,
        filters: SearchFilters | None = None,
        limit: int = 20,
        min_score: float = 0.0,
        sort_by: str = "relevance",
        query_mode: str = "smart",
    ) -> list[SearchResult]:
        filters = filters or SearchFilters()
        query_n = normalize(query)
        query_tokens = tokens(query_n)
        required_terms = [term for term in re.split(r"\s+", query_n) if term]
        results: list[SearchResult] = []
        for entry in self.entries:
            if not filters.matches(entry):
                continue
            if not query_n:
                score = 1.0 + (0.2 if entry.recommended_items else 0.0)
                if entry.author_visit_status == "visited_by_author":
                    score += 0.1
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

            if query_mode == "all" and required_terms and not all(term in text for term in required_terms):
                continue
            if query_mode == "exact" and query_n not in text:
                continue
            if score >= min_score and (matched or query_n in text or ratio >= 0.42):
                results.append(SearchResult(entry, score, reasons))
        self._sort(results, sort_by)
        return results[: max(0, limit)]
