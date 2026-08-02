from __future__ import annotations

from pathlib import Path
from typing import Any

from hust_helper.core.models import FoodEntry

from .service import HustEaterService


class HustEaterAPI:
    """Notebook-friendly facade returning entries instead of internal score wrappers."""

    def __init__(self, service: HustEaterService | None = None) -> None:
        self.service = service or HustEaterService()

    def search(self, query: str = "", **filters: Any) -> list[FoodEntry]:
        return [result.entry for result in self.service.search(query, **filters)]

    def search_with_scores(self, query: str = "", **filters: Any):
        return self.service.search(query, **filters)

    def all(self) -> list[FoodEntry]:
        return self.service.entries()

    def get(self, entry_id: str) -> FoodEntry:
        return self.service.get(entry_id)

    def stats(self) -> dict[str, int]:
        return self.service.stats()

    def catalog(self) -> dict[str, Any]:
        return self.service.repository.catalog()

    def page(self, page_number: int) -> dict[str, Any]:
        return self.service.repository.page(page_number)

    def page_markdown(self, page_number: int) -> str:
        return self.service.repository.page_markdown(page_number)

    def image_bytes(self, media_id: str) -> bytes:
        return self.service.repository.image_bytes(media_id)

    def add(self, **fields: Any) -> FoodEntry:
        return self.service.add(**fields)

    def update(self, entry_id: str, **changes: Any) -> FoodEntry:
        return self.service.update(entry_id, **changes)

    def delete(self, entry_id: str) -> None:
        self.service.delete(entry_id)

    def restore(self, entry_id: str) -> FoodEntry:
        return self.service.restore(entry_id)

    def add_image(self, entry_id: str, path: str | Path, caption: str = "") -> str:
        return self.service.add_image(entry_id, path, caption)

    def update_image_caption(self, media_id: str, caption: str) -> dict[str, Any]:
        return self.service.update_image_caption(media_id, caption)

    def replace_image(self, media_id: str, path: str | Path, caption: str | None = None) -> dict[str, Any]:
        return self.service.replace_image(media_id, path, caption)

    def remove_image(self, entry_id: str, media_id: str) -> FoodEntry:
        return self.service.remove_image(entry_id, media_id)

    def export(self, path: str | Path, format: str = "json") -> Path:
        return self.service.repository.export(path, format)


eater = HustEaterAPI()
