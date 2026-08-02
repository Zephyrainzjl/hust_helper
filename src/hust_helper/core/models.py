from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class FoodEntry:
    id: str
    name: str
    ordinal: int = 0
    category: str = ""
    heading: str = ""
    chapter_id: str = ""
    section_id: str = ""
    chapter_title: str = ""
    section_title: str = ""
    source_pages: list[int] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    highlighted_text: list[str] = field(default_factory=list)
    media_ids: list[str] = field(default_factory=list)
    description: str = ""
    highlighted_segments: list[dict[str, Any]] = field(default_factory=list)
    recommended_items: list[str] = field(default_factory=list)
    author_visit_status: str = "unspecified"
    venue_type: str = "restaurant"
    meal_periods: list[str] = field(default_factory=list)
    spice_notes: list[str] = field(default_factory=list)
    price_notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    user_editable: bool = True
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FoodEntry":
        fields = cls.__dataclass_fields__
        known = {key: value[key] for key in fields if key in value}
        unknown = {key: val for key, val in value.items() if key not in fields}
        obj = cls(**known)
        if unknown:
            obj.extensions = {**obj.extensions, "unknown_fields": unknown}
        return obj

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def searchable_text(self) -> str:
        values = [
            self.name,
            self.category,
            self.heading,
            self.chapter_title,
            self.section_title,
            self.description,
            " ".join(self.recommended_items),
            " ".join(self.highlighted_text),
            " ".join(self.tags),
            " ".join(self.spice_notes),
            " ".join(self.price_notes),
        ]
        return "\n".join(value for value in values if value).lower()


@dataclass(slots=True)
class SearchResult:
    entry: FoodEntry
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "reasons": self.reasons,
            "entry": self.entry.to_dict(),
        }
