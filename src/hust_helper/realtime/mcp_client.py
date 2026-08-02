from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from .config import MCPServerConfig


class MCPDependencyError(RuntimeError):
    pass


@dataclass(slots=True)
class MCPToolDescriptor:
    server_name: str
    name: str
    llm_name: str
    description: str
    input_schema: dict[str, Any]

    def as_llm_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.llm_name,
                "description": f"[{self.server_name}] {self.description or self.name}",
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


@dataclass(slots=True)
class MCPToolResult:
    server_name: str
    tool_name: str
    text: str
    structured: Any = None
    is_error: bool = False
    raw_content: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class MCPServerStatus:
    name: str
    connected: bool
    tool_count: int = 0
    error: str = ""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return slug or "tool"


def _llm_tool_name(server: str, tool: str) -> str:
    value = f"mcp__{_slug(server)}__{_slug(tool)}"
    return value[:64]


@asynccontextmanager
async def _open_client_v2(config: MCPServerConfig) -> AsyncIterator[Any]:
    from mcp import Client, StdioServerParameters
    from mcp.client.stdio import stdio_client

    if config.transport == "stdio":
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )
        async with Client(stdio_client(params)) as client:
            yield client
        return

    if not config.headers:
        async with Client(config.url) as client:
            yield client
        return

    try:
        import httpx2
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as exc:
        raise MCPDependencyError(
            "当前 MCP SDK 缺少带自定义 HTTP headers 的 Streamable HTTP 依赖"
        ) from exc

    timeout = httpx2.Timeout(config.timeout, read=max(config.timeout, 300.0))
    async with httpx2.AsyncClient(
        headers=config.headers,
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client(config.url, http_client=http_client)
        async with Client(transport) as client:
            yield client


@asynccontextmanager
async def _open_client_v1(config: MCPServerConfig) -> AsyncIterator[Any]:
    import httpx
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client

    if config.transport == "stdio":
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )
        async with stdio_client(params) as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
        return

    timeout = httpx.Timeout(config.timeout, read=max(config.timeout, 300.0))
    async with httpx.AsyncClient(
        headers=config.headers,
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        async with streamable_http_client(config.url, http_client=http_client) as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session


@asynccontextmanager
async def _open_client(config: MCPServerConfig) -> AsyncIterator[Any]:
    try:
        import mcp
    except ImportError as exc:
        raise MCPDependencyError(
            '实时 MCP 功能需要额外依赖：pip install "hust_helper[realtime]"'
        ) from exc

    config.validate()
    if hasattr(mcp, "Client"):
        async with _open_client_v2(config) as client:
            yield client
    else:
        async with _open_client_v1(config) as client:
            yield client


def _tool_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(mode="json")
    return schema if isinstance(schema, dict) else {"type": "object", "properties": {}}


def _result_text(result: Any, max_chars: int = 24000) -> tuple[str, Any, list[Any]]:
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    content = list(getattr(result, "content", None) or [])
    text_parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            text_parts.append(str(text))
    if structured is not None:
        try:
            structured_text = json.dumps(structured, ensure_ascii=False, default=str)
        except TypeError:
            structured_text = str(structured)
        if structured_text not in text_parts:
            text_parts.append(structured_text)
    text = "\n".join(text_parts).strip() or "（工具未返回文本内容）"
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…（结果过长，已截断）"
    return text, structured, content


class MCPHub:
    """Connect to multiple MCP servers without coupling them to the local guide."""

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        self.servers = [server for server in servers if server.enabled]
        self._descriptor_cache: list[MCPToolDescriptor] | None = None
        self._status_cache: list[MCPServerStatus] | None = None

    async def _list_server_tools(
        self, config: MCPServerConfig
    ) -> tuple[list[MCPToolDescriptor], MCPServerStatus]:
        try:
            async with _open_client(config) as client:
                descriptors: list[MCPToolDescriptor] = []
                cursor = None
                while True:
                    result = await client.list_tools(cursor=cursor)
                    for tool in result.tools:
                        name = str(tool.name)
                        if config.allowed_tools and name not in config.allowed_tools:
                            continue
                        descriptors.append(
                            MCPToolDescriptor(
                                server_name=config.name,
                                name=name,
                                llm_name=_llm_tool_name(config.name, name),
                                description=str(getattr(tool, "description", "") or ""),
                                input_schema=_tool_schema(tool),
                            )
                        )
                    cursor = getattr(result, "next_cursor", None) or getattr(result, "nextCursor", None)
                    if not cursor:
                        break
                return descriptors, MCPServerStatus(config.name, True, len(descriptors))
        except Exception as exc:
            return [], MCPServerStatus(config.name, False, error=str(exc))

    async def list_tools(
        self, *, refresh: bool = False
    ) -> tuple[list[MCPToolDescriptor], list[MCPServerStatus]]:
        if self._descriptor_cache is not None and self._status_cache is not None and not refresh:
            return list(self._descriptor_cache), list(self._status_cache)
        if not self.servers:
            return [], []
        pairs = await asyncio.gather(*(self._list_server_tools(server) for server in self.servers))
        descriptors = [descriptor for tools, _ in pairs for descriptor in tools]
        statuses = [status for _, status in pairs]
        self._descriptor_cache = descriptors
        self._status_cache = statuses
        return list(descriptors), list(statuses)

    async def call_tool(self, descriptor: MCPToolDescriptor, arguments: dict[str, Any]) -> MCPToolResult:
        server = next(
            (item for item in self.servers if item.name == descriptor.server_name),
            None,
        )
        if server is None:
            raise KeyError(f"Unknown MCP server: {descriptor.server_name}")
        async with _open_client(server) as client:
            result = await client.call_tool(descriptor.name, arguments)
        text, structured, content = _result_text(result)
        return MCPToolResult(
            server_name=descriptor.server_name,
            tool_name=descriptor.name,
            text=text,
            structured=structured,
            is_error=bool(getattr(result, "is_error", False) or getattr(result, "isError", False)),
            raw_content=content,
        )

    def list_tools_sync(
        self, *, refresh: bool = False
    ) -> tuple[list[MCPToolDescriptor], list[MCPServerStatus]]:
        return asyncio.run(self.list_tools(refresh=refresh))
