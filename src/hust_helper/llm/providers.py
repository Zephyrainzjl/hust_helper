from __future__ import annotations

from .base import LLMProvider
from .config import LLMConfig
from .litellm_provider import LiteLLMProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_responses import OpenAIResponsesProvider


def create_provider(config: LLMConfig) -> LLMProvider:
    if config.provider == "openai_responses":
        return OpenAIResponsesProvider(config)
    if config.provider == "openai_compatible":
        return OpenAICompatibleProvider(config)
    if config.provider == "litellm":
        return LiteLLMProvider(config)
    raise ValueError(f"Unknown provider type: {config.provider}")
