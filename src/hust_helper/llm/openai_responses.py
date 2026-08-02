from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ChatMessage, ProviderResponse
from .config import LLMConfig


class OpenAIResponsesProvider:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @staticmethod
    def _input(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "tool":
                result.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id,
                        "output": message.content or "",
                    }
                )
                continue
            if message.content:
                result.append({"role": message.role, "content": message.content})
            for call in message.tool_calls:
                function = call.get("function", {})
                result.append(
                    {
                        "type": "function_call",
                        "call_id": call.get("id"),
                        "name": function.get("name"),
                        "arguments": function.get("arguments") or "{}",
                    }
                )
        return result

    @staticmethod
    def _response_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        converted = []
        for tool in tools or []:
            function = tool.get("function", tool)
            converted.append(
                {
                    "type": "function",
                    "name": function["name"],
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {"type": "object"}),
                }
            )
        return converted

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        self.config.require_valid()
        body: dict[str, Any] = {
            "model": self.config.model,
            "input": self._input(messages),
        }
        converted = self._response_tools(tools)
        if converted:
            body["tools"] = converted
            body["tool_choice"] = "auto"
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_output_tokens is not None:
            body["max_output_tokens"] = self.config.max_output_tokens
        body.update(self.config.extra_body)
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.headers,
        }
        url = f"{self.config.base_url.rstrip('/')}/responses"
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        text_parts: list[str] = []
        calls: list[dict[str, Any]] = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        text_parts.append(content.get("text", ""))
            elif item.get("type") == "function_call":
                calls.append(
                    {
                        "id": item.get("call_id") or item.get("id"),
                        "type": "function",
                        "function": {
                            "name": item.get("name"),
                            "arguments": item.get("arguments")
                            if isinstance(item.get("arguments"), str)
                            else json.dumps(item.get("arguments", {}), ensure_ascii=False),
                        },
                    }
                )
        return ProviderResponse(text="\n".join(text_parts).strip(), tool_calls=calls, raw=data)
