from __future__ import annotations

from typing import Any

import httpx

from .base import ChatMessage, ProviderResponse
from .config import LLMConfig


class OpenAICompatibleProvider:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        self.config.require_valid()
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [message.to_openai() for message in messages],
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_output_tokens is not None:
            body["max_tokens"] = self.config.max_output_tokens
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        body.update(self.config.extra_body)
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.headers,
        }
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        message = data["choices"][0]["message"]
        return ProviderResponse(
            text=message.get("content") or "",
            tool_calls=message.get("tool_calls") or [],
            raw=data,
        )
