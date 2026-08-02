from __future__ import annotations

from pathlib import Path
from typing import Any

from hust_helper.core.models import FoodEntry

from .service import HustEaterService


class HustEaterEditor:
    """Explicit editing facade for GUIs and external integrations."""

    def __init__(self, service: HustEaterService | None = None) -> None:
        self.service = service or HustEaterService()

    def create(self, name: str, **fields: Any) -> FoodEntry:
        return self.service.add(name=name, **fields)

    def patch(self, entry_id: str, **changes: Any) -> FoodEntry:
        return self.service.update(entry_id, **changes)

    def delete(self, entry_id: str) -> None:
        self.service.delete(entry_id)

    def restore(self, entry_id: str) -> FoodEntry:
        return self.service.restore(entry_id)

    def attach_image(self, entry_id: str, file: str | Path, caption: str = "") -> str:
        return self.service.add_image(entry_id, file, caption)

    def update_image_caption(self, media_id: str, caption: str) -> dict[str, Any]:
        return self.service.update_image_caption(media_id, caption)

    def replace_image(self, media_id: str, file: str | Path, caption: str | None = None) -> dict[str, Any]:
        return self.service.replace_image(media_id, file, caption)

    def detach_image(self, entry_id: str, media_id: str) -> FoodEntry:
        return self.service.remove_image(entry_id, media_id)
