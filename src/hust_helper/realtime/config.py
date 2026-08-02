from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: str) -> str:
    return _ENV_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)


@dataclass(slots=True)
class MCPServerConfig:
    """Configuration for one independent MCP data source.

    ``transport`` can be ``streamable_http`` or ``stdio``.  HTTP is preferred
    for hosted services.  Credentials may be provided in the URL, headers, or
    process environment, depending on the server's official integration model.
    """

    name: str
    transport: str = "streamable_http"
    url: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    allowed_tools: list[str] = field(default_factory=list)
    timeout: float = 60.0

    @classmethod
    def amap(cls, api_key: str, *, name: str = "amap") -> "MCPServerConfig":
        key = api_key.strip()
        if not key:
            raise ValueError("高德 MCP Key 不能为空")
        return cls(name=name, url=f"https://mcp.amap.com/mcp?key={key}")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MCPServerConfig":
        data = dict(value)
        for field_name in ("url", "command"):
            if isinstance(data.get(field_name), str):
                data[field_name] = _expand_env(data[field_name])
        data["args"] = [_expand_env(str(item)) for item in data.get("args", [])]
        data["env"] = {str(k): _expand_env(str(v)) for k, v in data.get("env", {}).items()}
        data["headers"] = {
            str(k): _expand_env(str(v)) for k, v in data.get("headers", {}).items()
        }
        return cls(**data)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("MCP server name is required")
        if self.transport == "streamable_http":
            if not self.url:
                raise ValueError(f"MCP server {self.name!r} requires url")
            if not self.url.startswith(("https://", "http://")):
                raise ValueError(f"MCP server {self.name!r} has an invalid URL")
        elif self.transport == "stdio":
            if not self.command:
                raise ValueError(f"MCP server {self.name!r} requires command")
        else:
            raise ValueError(f"Unsupported MCP transport: {self.transport}")


def parse_server_configs(text: str) -> list[MCPServerConfig]:
    """Parse a JSON array of extra MCP servers used by the live-search UI."""

    if not text.strip():
        return []
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError("额外 MCP 配置必须是 JSON 数组")
    servers = [MCPServerConfig.from_mapping(item) for item in payload]
    for server in servers:
        if server.enabled:
            server.validate()
    names = [server.name for server in servers]
    if len(names) != len(set(names)):
        raise ValueError("MCP server name 不能重复")
    return servers
