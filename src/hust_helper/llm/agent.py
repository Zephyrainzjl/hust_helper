from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from hust_helper.tools.hust_eater.service import HustEaterService

from .base import ChatMessage
from .config import LLMConfig
from .providers import create_provider

_SYSTEM = """你是 HUST Helper 的干饭助手。只根据本地检索工具返回的指南内容推荐，明确区分作者亲自去过、朋友/武汉文旅/网络推荐以及未去过。不要捏造地址、营业时间、价格或实时状态。涉及营业与价格时提醒用户自行核验。回答简洁但要说明推荐理由与来源章节。完成本地检索后，必须直接基于工具结果回答用户，不要重复调用相同检索。"""

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
                "meal_period": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "night"]},
                "visited": {"type": "string"},
                "spicy": {"type": "boolean"},
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
    """Conversational food-search agent.

    The agent allows one tool-search round by default and then performs a final
    model call with tools disabled. This prevents OpenAI-compatible models from
    repeatedly issuing the same ``search_food`` call until the round limit is
    reached.
    """

    def __init__(
        self,
        config: LLMConfig,
        service: HustEaterService | None = None,
        max_tool_rounds: int = 1,
    ) -> None:
        if max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be at least 1")
        self.config = config
        self.service = service or HustEaterService()
        self.provider = create_provider(config)
        self.max_tool_rounds = max_tool_rounds
        self.history: list[ChatMessage] = [ChatMessage(role="system", content=_SYSTEM)]

    def _execute_search(self, arguments: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        allowed = {
            "query",
            "chapter",
            "section",
            "venue_type",
            "meal_period",
            "visited",
            "spicy",
            "limit",
        }
        kwargs = {key: value for key, value in arguments.items() if key in allowed}
        kwargs.setdefault("limit", 8)
        results = self.service.search(**kwargs)
        sources: list[dict[str, Any]] = []
        payload: list[dict[str, Any]] = []
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

    @staticmethod
    def _parse_arguments(raw_arguments: Any, fallback_query: str) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            arguments = raw_arguments
        elif isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments or "{}")
            except json.JSONDecodeError:
                parsed = {}
            arguments = parsed if isinstance(parsed, dict) else {}
        else:
            arguments = {}
        arguments.setdefault("query", fallback_query)
        return arguments

    @staticmethod
    def _call_signature(name: str, arguments: dict[str, Any]) -> str:
        return json.dumps(
            {"name": name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @staticmethod
    def _deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for source in sources:
            key = (
                source.get("id"),
                tuple(source.get("source_pages") or []),
                source.get("section"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(source)
        return unique

    def _final_answer_without_tools(
        self,
        question: str,
        collected_sources: list[dict[str, Any]],
        raw: dict[str, Any],
    ) -> AgentReply:
        """Force the model to synthesize an answer instead of calling tools again."""
        try:
            response = self.provider.complete(self.history, tools=None)
        except Exception:
            fallback = self.local_answer(question)
            fallback.sources = self._deduplicate_sources(collected_sources or fallback.sources)
            fallback.raw = raw
            return fallback

        final_text = (response.text or "").strip()
        if not final_text:
            fallback = self.local_answer(question)
            fallback.sources = self._deduplicate_sources(collected_sources or fallback.sources)
            fallback.raw = response.raw or raw
            return fallback

        self.history.append(ChatMessage(role="assistant", content=final_text))
        return AgentReply(
            final_text,
            self._deduplicate_sources(collected_sources),
            response.raw or raw,
        )

    def local_answer(self, question: str, limit: int = 8) -> AgentReply:
        results = self.service.search(question, limit=limit)
        if not results:
            return AgentReply("本地指南中没有检索到明确匹配项。可以换一个菜名、区域或口味关键词。")
        lines = ["本地指南检索结果："]
        sources: list[dict[str, Any]] = []
        for index, result in enumerate(results, 1):
            entry = result.entry
            dishes = "、".join(entry.recommended_items[:6]) or "详见原文描述"
            lines.append(
                f"{index}. {entry.name}｜{entry.section_title}｜{dishes}｜"
                f"作者状态：{entry.author_visit_status}｜PDF 第 {','.join(map(str, entry.source_pages))} 页"
            )
            sources.append({"id": entry.id, "name": entry.name, "source_pages": entry.source_pages})
        return AgentReply("\n".join(lines), sources=sources)

    def ask(self, question: str) -> AgentReply:
        question = question.strip()
        if not question:
            return AgentReply("请输入你想吃的菜、区域、预算或口味偏好。")
        if not self.config.api_key:
            return self.local_answer(question)

        self.history.append(ChatMessage(role="user", content=question))
        collected_sources: list[dict[str, Any]] = []
        raw: dict[str, Any] = {}
        search_cache: dict[str, tuple[str, list[dict[str, Any]]]] = {}

        for _round_index in range(self.max_tool_rounds):
            response = self.provider.complete(self.history, tools=[_SEARCH_TOOL])
            raw = response.raw
            if not response.tool_calls:
                final_text = (response.text or "").strip()
                if not final_text:
                    return self._final_answer_without_tools(question, collected_sources, raw)
                self.history.append(ChatMessage(role="assistant", content=final_text))
                return AgentReply(final_text, self._deduplicate_sources(collected_sources), raw)

            self.history.append(
                ChatMessage(
                    role="assistant",
                    content=response.text or None,
                    tool_calls=response.tool_calls,
                )
            )

            executed_supported_tool = False
            repeated_only = True
            for call in response.tool_calls:
                function = call.get("function") or {}
                function_name = str(function.get("name") or "")
                arguments = self._parse_arguments(function.get("arguments"), question)

                if function_name != "search_food":
                    self.history.append(
                        ChatMessage(
                            role="tool",
                            name=function_name or "unknown_tool",
                            tool_call_id=call.get("id"),
                            content=json.dumps(
                                {"error": f"Unsupported tool: {function_name or 'unknown'}"},
                                ensure_ascii=False,
                            ),
                        )
                    )
                    continue

                executed_supported_tool = True
                signature = self._call_signature(function_name, arguments)
                cached = search_cache.get(signature)
                if cached is None:
                    cached = self._execute_search(arguments)
                    search_cache[signature] = cached
                    repeated_only = False
                output, sources = cached
                collected_sources.extend(sources)
                self.history.append(
                    ChatMessage(
                        role="tool",
                        name="search_food",
                        tool_call_id=call.get("id"),
                        content=output,
                    )
                )

            if not executed_supported_tool or repeated_only:
                break

        # The final call deliberately omits ``tools``. The model must now turn
        # the retrieved JSON records into a natural-language recommendation.
        return self._final_answer_without_tools(question, collected_sources, raw)

    def reset(self) -> None:
        """Clear the conversation and all per-conversation tool context."""
        self.history = [ChatMessage(role="system", content=_SYSTEM)]
