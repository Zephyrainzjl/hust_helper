from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any


def discover_tools() -> dict[str, Any]:
    discovered: dict[str, Any] = {}
    selected = entry_points(group="hust_helper.tools")
    for item in selected:
        try:
            discovered[item.name] = item.load()
        except Exception as exc:  # A broken optional plugin must not break the app.
            discovered[item.name] = exc
    return discovered
