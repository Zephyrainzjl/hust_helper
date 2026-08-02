from __future__ import annotations

from pathlib import Path
from typing import Any

from hust_helper.core.models import FoodEntry, SearchResult
from hust_helper.core.repository import HustEaterRepository
from hust_helper.core.search import FoodSearchEngine, SearchFilters


class HustEaterService:
    def __init__(self, repository: HustEaterRepository | None = None) -> None:
        self.repository = repository or HustEaterRepository()

    def search(
        self,
        query: str = "",
        *,
        chapter: str | None = None,
        section: str | None = None,
        category: str | None = None,
        venue_type: str | None = None,
        meal_period: str | None = None,
        visited: str | None = None,
        has_images: bool | None = None,
        spicy: bool | None = None,
        avoid_spicy: bool = False,
        recommended_only: bool = False,
        has_price_notes: bool | None = None,
        external_recommended: bool | None = None,
        min_recommendations: int = 0,
        tags: list[str] | None = None,
        exclude_terms: list[str] | None = None,
        query_mode: str = "smart",
        sort_by: str = "relevance",
        limit: int = 20,
    ) -> list[SearchResult]:
        engine = FoodSearchEngine(self.repository.list_entries())
        filters = SearchFilters(
            chapter=chapter,
            section=section,
            category=category,
            venue_type=venue_type,
            meal_period=meal_period,
            visited=visited,
            has_images=has_images,
            spicy=spicy,
            avoid_spicy=avoid_spicy,
            recommended_only=recommended_only,
            has_price_notes=has_price_notes,
            external_recommended=external_recommended,
            min_recommendations=min_recommendations,
            tags=tags or [],
            exclude_terms=exclude_terms or [],
        )
        return engine.search(
            query,
            filters=filters,
            limit=limit,
            query_mode=query_mode,
            sort_by=sort_by,
        )

    def entries(self) -> list[FoodEntry]:
        return self.repository.list_entries()

    def get(self, entry_id: str) -> FoodEntry:
        return self.repository.get(entry_id)

    def add(self, **fields: Any) -> FoodEntry:
        fields.setdefault("id", "")
        fields.setdefault("name", "未命名地点")
        return self.repository.add(fields)

    def update(self, entry_id: str, **changes: Any) -> FoodEntry:
        return self.repository.update(entry_id, **changes)

    def delete(self, entry_id: str) -> None:
        self.repository.delete(entry_id)

    def restore(self, entry_id: str) -> FoodEntry:
        return self.repository.restore(entry_id)

    def add_image(self, entry_id: str, path: str | Path, caption: str = "") -> str:
        return self.repository.add_image(entry_id, path, caption)

    def update_image_caption(self, media_id: str, caption: str) -> dict[str, Any]:
        return self.repository.update_image_caption(media_id, caption)

    def replace_image(self, media_id: str, path: str | Path, caption: str | None = None) -> dict[str, Any]:
        return self.repository.replace_image(media_id, path, caption)

    def remove_image(self, entry_id: str, media_id: str) -> FoodEntry:
        return self.repository.remove_image(entry_id, media_id)

    def stats(self) -> dict[str, int]:
        catalog = self.repository.catalog()
        return {
            **catalog["counts"],
            "active_entries": len(self.repository.list_entries()),
        }
