from __future__ import annotations

from typing import Any

from hust_helper.core.plugins import discover_tools

_BUILTINS: dict[str, str] = {"hust_eater": "hust_helper.tools.hust_eater:HustEaterTool"}


def _load(spec: str) -> Any:
    module_name, attribute = spec.split(":", 1)
    module = __import__(module_name, fromlist=[attribute])
    return getattr(module, attribute)


def list_tools() -> dict[str, Any]:
    tools = {name: _load(spec) for name, spec in _BUILTINS.items()}
    for name, value in discover_tools().items():
        if not isinstance(value, Exception):
            tools[name] = value
    return tools


def get_tool(name: str) -> Any:
    tools = list_tools()
    if name not in tools:
        raise KeyError(f"Unknown tool: {name}. Available: {sorted(tools)}")
    return tools[name]
