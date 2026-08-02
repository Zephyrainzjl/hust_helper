from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(slots=True)
class Settings:
    app_name: str = "hust_helper"
    app_author: str = "Jialiu Zeng"
    data_dir: Path | None = None

    def resolved_data_dir(self) -> Path:
        configured = self.data_dir
        if configured is None and os.environ.get("HUST_HELPER_DATA_DIR"):
            configured = Path(os.environ["HUST_HELPER_DATA_DIR"])
        if configured is None and os.environ.get("FLET_APP_STORAGE_DATA"):
            configured = Path(os.environ["FLET_APP_STORAGE_DATA"]) / self.app_name
        path = configured or user_data_path(self.app_name, self.app_author)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
