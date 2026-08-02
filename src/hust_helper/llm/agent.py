from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from hust_helper.tools.hust_eater.service import HustEaterService

from .base import ChatMessage
from .config import LLMConfig
from .providers import create_provider

_SYSTEM = """你是 HUST Helper 的本地干饭指南助手。你只根据 bundled PDF 指南检索工具返回的内容推荐，明确区分作者亲自去过、朋友/武汉文旅/网络推荐以及未去过。不要捏造地址、营业时间、价格或实时状态。涉及营业与价格时提醒用户自行核验。回答简洁但要说明推荐理由与来源章节。这个助手不访问实时地图或美团/大众点评；实时查询应使用独立的“实时 MCP”页面。"""

_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_food",
        "description": "Search the bundled HUST/Wuhan food guide with optional filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Food, venue, preference, or keyword"},
                "chapter": {"type": "string"},
                "section": {"type": "string"},
                "venue_type": {"type": "string"},
                "meal_period": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "late_day"],
                },
                "visited": {"type": "string"},
                "avoid_spicy": {"type": "boolean"},
                "recommended_only": {"type": "boolean"},
                "has_images": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


@dataclass(slots=True)
class AgentReply:
    text: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class FoodChatAgent:
    def __init__(
        self,
        config: LLMConfig,
        service: HustEaterService | None = None,
        max_tool_rounds: int = 2,
    ) -> None:
        self.config = config
        self.service = service or HustEaterService()
        self.provider = create_provider(config)
        self.max_tool_rounds = max(1, max_tool_rounds)
        self.history: list[ChatMessage] = [ChatMessage(role="system", content=_SYSTEM)]

    def _execute_search(self, arguments: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        allowed = {
            "query",
            "chapter",
            "section",
            "venue_type",
            "meal_period",
            "visited",
            "avoid_spicy",
            "recommended_only",
            "has_images",
            "limit",
        }
        kwargs = {key: value for key, value in arguments.items() if key in allowed}
        kwargs.setdefault("query", "")
        kwargs.setdefault("limit", 8)
        results = self.service.search(**kwargs)
        sources = []
        payload = []
        for result in results:
            entry = result.entry
            record = {
                "id": entry.id,
                "name": entry.name,
                "chapter": entry.chapter_title,
                "section": entry.section_title,
                "category": entry.category,
                "description": entry.description,
                "recommended_items": entry.recommended_items,
                "visit_status": entry.author_visit_status,
                "spice_notes": entry.spice_notes,
                "price_notes": entry.price_notes,
                "source_pages": entry.source_pages,
                "score": round(result.score, 3),
            }
            payload.append(record)
            sources.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "source_pages": entry.source_pages,
                    "section": entry.section_title,
                }
            )
        return json.dumps(payload, ensure_ascii=False), sources

    def local_answer(self, question: str, limit: int = 8) -> AgentReply:
        results = self.service.search(question, limit=limit)
        if not results:
            return AgentReply("本地指南中没有检索到明确匹配项。可以换一个菜名、区域或口味关键词。")
        lines = ["本地指南检索结果："]
        sources = []
        for index, result in enumerate(results, 1):
            entry = result.entry
            dishes = "、".join(entry.recommended_items[:6]) or "详见原文描述"
            lines.append(
                f"{index}. {entry.name}｜{entry.section_title}｜{dishes}｜"
                f"作者状态：{entry.author_visit_status}｜PDF 第 {','.join(map(str, entry.source_pages))} 页"
            )
            sources.append({"id": entry.id, "name": entry.name, "source_pages": entry.source_pages})
        return AgentReply("\n".join(lines), sources=sources)

    @staticmethod
    def _unique_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for source in sources:
            key = str(source.get("id"))
            if key not in seen:
                seen.add(key)
                result.append(source)
        return result

    def ask(self, question: str) -> AgentReply:
        if not self.config.api_key:
            return self.local_answer(question)
        self.history.append(ChatMessage(role="user", content=question))
        collected_sources: list[dict[str, Any]] = []
        seen_calls: set[str] = set()
        raw: dict[str, Any] = {}
        for _ in range(self.max_tool_rounds):
            response = self.provider.complete(self.history, tools=[_SEARCH_TOOL])
            raw = response.raw
            if not response.tool_calls:
                self.history.append(ChatMessage(role="assistant", content=response.text))
                return AgentReply(response.text, self._unique_sources(collected_sources), raw)
            self.history.append(
                ChatMessage(
                    role="assistant",
                    content=response.text or None,
                    tool_calls=response.tool_calls,
                )
            )
            for call in response.tool_calls:
                function = call.get("function", {})
                if function.get("name") != "search_food":
                    continue
                raw_arguments = function.get("arguments") or "{}"
                try:
                    arguments = (
                        json.loads(raw_arguments)
                        if isinstance(raw_arguments, str)
                        else dict(raw_arguments)
                    )
                except (json.JSONDecodeError, TypeError, ValueError):
                    arguments = {"query": question}
                signature = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
                if signature in seen_calls:
                    output = "重复检索已阻止，请直接基于已有结果回答。"
                    sources = []
                else:
                    seen_calls.add(signature)
                    output, sources = self._execute_search(arguments)
                collected_sources.extend(sources)
                self.history.append(
                    ChatMessage(
                        role="tool",
                        name="search_food",
                        tool_call_id=call.get("id"),
                        content=output,
                    )
                )

        self.history.append(
            ChatMessage(
                role="user",
                content="检索轮次结束。请停止调用工具，仅根据已返回的本地指南结果给出最终回答。",
            )
        )
        response = self.provider.complete(self.history, tools=None)
        self.history.append(ChatMessage(role="assistant", content=response.text))
        return AgentReply(response.text, self._unique_sources(collected_sources), response.raw)

    def reset(self) -> None:
        self.history = [ChatMessage(role="system", content=_SYSTEM)]
