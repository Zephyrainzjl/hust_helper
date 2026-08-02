from __future__ import annotations

from typing import Any

from .base import ChatMessage, ProviderResponse
from .config import LLMConfig


class LiteLLMProvider:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        try:
            from litellm import completion
        except ImportError as exc:
            raise RuntimeError('Install broad provider support with: pip install "hust_helper[llm]"') from exc
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": [message.to_openai() for message in messages],
            "timeout": self.config.timeout,
        }
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            kwargs["api_base"] = self.config.base_url
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if self.config.max_output_tokens is not None:
            kwargs["max_tokens"] = self.config.max_output_tokens
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        kwargs.update(self.config.extra_body)
        response = completion(**kwargs)
        message = response.choices[0].message
        tool_calls = []
        for call in getattr(message, "tool_calls", None) or []:
            tool_calls.append(call.model_dump() if hasattr(call, "model_dump") else dict(call))
        raw = response.model_dump() if hasattr(response, "model_dump") else {}
        return ProviderResponse(text=getattr(message, "content", "") or "", tool_calls=tool_calls, raw=raw)
