from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from hust_helper.llm.base import ChatMessage, LLMProvider
from hust_helper.llm.config import LLMConfig
from hust_helper.llm.providers import create_provider

from .mcp_client import MCPHub, MCPToolDescriptor, MCPToolResult

_REALTIME_SYSTEM = """你是 HUST Helper 的实时探店助手。你与内置 PDF 指南助手彼此独立。
你必须优先使用 MCP 工具获取当前地点、周边、路线、营业信息和平台返回的商户数据。
只有工具明确返回“营业中/营业时间/评分/价格/团购/排队”等字段时，才可以把它们当作实时事实；否则必须写明“工具未提供，需在对应平台再次确认”。
每个结论标明数据来源服务器，例如“高德 MCP”“已授权的美团连接器”。不要把不同平台的评分直接混为同一尺度。
不得绕过登录、风控或平台授权，不得声称抓取了大众点评/美团私有数据。回答应先给可执行推荐，再说明数据时间性和不确定性。"""


@dataclass(slots=True)
class RealtimeReply:
    text: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    server_status: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class RealtimeFoodAgent:
    def __init__(
        self,
        config: LLMConfig,
        hub: MCPHub,
        *,
        max_tool_rounds: int = 4,
        provider: LLMProvider | None = None,
    ) -> None:
        self.config = config
        self.hub = hub
        self.provider = provider or create_provider(config)
        self.max_tool_rounds = max(1, max_tool_rounds)
        self.history: list[ChatMessage] = [ChatMessage(role="system", content=_REALTIME_SYSTEM)]

    @staticmethod
    def _deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for source in sources:
            key = (str(source.get("server")), str(source.get("tool")))
            if key not in seen:
                seen.add(key)
                result.append(source)
        return result

    async def ask_async(self, question: str) -> RealtimeReply:
        self.config.require_valid()
        descriptors, statuses = await self.hub.list_tools()
        status_payload = [
            {
                "name": status.name,
                "connected": status.connected,
                "tool_count": status.tool_count,
                "error": status.error,
            }
            for status in statuses
        ]
        if not descriptors:
            details = "；".join(
                f"{status.name}: {status.error or '没有可用工具'}" for status in statuses
            ) or "没有配置 MCP server"
            return RealtimeReply(
                f"实时 MCP 未发现可用工具。{details}",
                server_status=status_payload,
            )

        by_llm_name = {descriptor.llm_name: descriptor for descriptor in descriptors}
        llm_tools = [descriptor.as_llm_tool() for descriptor in descriptors]
        self.history.append(ChatMessage(role="user", content=question))
        collected_sources: list[dict[str, Any]] = []
        seen_calls: set[str] = set()
        raw: dict[str, Any] = {}

        for _round in range(self.max_tool_rounds):
            response = await asyncio.to_thread(self.provider.complete, self.history, llm_tools)
            raw = response.raw
            if not response.tool_calls:
                self.history.append(ChatMessage(role="assistant", content=response.text))
                return RealtimeReply(
                    response.text,
                    self._deduplicate_sources(collected_sources),
                    status_payload,
                    raw,
                )

            self.history.append(
                ChatMessage(
                    role="assistant",
                    content=response.text or None,
                    tool_calls=response.tool_calls,
                )
            )
            for call in response.tool_calls:
                function = call.get("function", {})
                llm_name = str(function.get("name") or "")
                descriptor = by_llm_name.get(llm_name)
                if descriptor is None:
                    self.history.append(
                        ChatMessage(
                            role="tool",
                            tool_call_id=call.get("id"),
                            name=llm_name,
                            content="未知 MCP 工具，无法调用。",
                        )
                    )
                    continue
                raw_arguments = function.get("arguments") or "{}"
                try:
                    arguments = (
                        json.loads(raw_arguments)
                        if isinstance(raw_arguments, str)
                        else dict(raw_arguments)
                    )
                except (json.JSONDecodeError, TypeError, ValueError):
                    arguments = {}
                signature = json.dumps(
                    [descriptor.server_name, descriptor.name, arguments],
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                if signature in seen_calls:
                    tool_result = MCPToolResult(
                        server_name=descriptor.server_name,
                        tool_name=descriptor.name,
                        text="重复工具调用已阻止。请基于已有结果给出结论。",
                        is_error=True,
                    )
                else:
                    seen_calls.add(signature)
                    try:
                        tool_result = await self.hub.call_tool(descriptor, arguments)
                    except Exception as exc:
                        tool_result = MCPToolResult(
                            server_name=descriptor.server_name,
                            tool_name=descriptor.name,
                            text=f"MCP 工具调用失败：{exc}",
                            is_error=True,
                        )
                collected_sources.append(
                    {
                        "server": descriptor.server_name,
                        "tool": descriptor.name,
                        "arguments": arguments,
                        "is_error": tool_result.is_error,
                    }
                )
                self.history.append(
                    ChatMessage(
                        role="tool",
                        name=llm_name,
                        tool_call_id=call.get("id"),
                        content=tool_result.text,
                    )
                )

        # Tool budget exhausted: disable tools and require a final answer instead
        # of falling back to the unrelated local PDF search.
        final_instruction = ChatMessage(
            role="user",
            content=(
                "工具调用预算已经用完。请停止调用工具，仅基于已经返回的 MCP 结果给出最终回答；"
                "明确哪些实时字段缺失。"
            ),
        )
        self.history.append(final_instruction)
        response = await asyncio.to_thread(self.provider.complete, self.history, None)
        self.history.append(ChatMessage(role="assistant", content=response.text))
        return RealtimeReply(
            response.text,
            self._deduplicate_sources(collected_sources),
            status_payload,
            response.raw,
        )

    def ask(self, question: str) -> RealtimeReply:
        return asyncio.run(self.ask_async(question))

    def reset(self) -> None:
        self.history = [ChatMessage(role="system", content=_REALTIME_SYSTEM)]
