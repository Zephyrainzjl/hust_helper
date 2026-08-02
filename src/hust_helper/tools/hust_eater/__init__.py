from __future__ import annotations

from .api import HustEaterAPI, eater
from .service import HustEaterService


class HustEaterTool:
    name = "hust_eater"
    description = "Searchable and editable HUST/Wuhan food guide"

    @staticmethod
    def service() -> HustEaterService:
        return HustEaterService()


__all__ = ["HustEaterAPI", "HustEaterService", "HustEaterTool", "eater"]
