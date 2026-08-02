from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderPreset(str, Enum):
    OPENAI = "openai"
    SILICONFLOW = "siliconflow"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    DASHSCOPE = "dashscope"
    CUSTOM = "custom"
    LITELLM = "litellm"


_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "provider": "openai_responses",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-5.6",
    },
    "siliconflow": {
        "provider": "openai_compatible",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "default_model": "",
    },
    "openrouter": {
        "provider": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "openai/gpt-5.6",
    },
    "deepseek": {
        "provider": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "dashscope": {
        "provider": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "default_model": "",
    },
}


@dataclass(slots=True)
class LLMConfig:
    provider: str = "openai_responses"
    model: str = "gpt-5.6"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 90.0
    temperature: float | None = None
    max_output_tokens: int | None = 1600
    headers: dict[str, str] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_preset(
        cls,
        preset: str | ProviderPreset,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> "LLMConfig":
        key = preset.value if isinstance(preset, ProviderPreset) else str(preset).lower()
        if key == "custom":
            return cls(
                provider="openai_compatible",
                model=model or "",
                api_key=api_key,
                base_url=base_url or "",
                **kwargs,
            )
        if key == "litellm":
            return cls(
                provider="litellm",
                model=model or "",
                api_key=api_key,
                base_url=base_url or "",
                **kwargs,
            )
        if key not in _PRESETS:
            raise ValueError(f"Unknown provider preset: {key}")
        preset_data = _PRESETS[key]
        return cls(
            provider=preset_data["provider"],
            model=model if model is not None else preset_data["default_model"],
            api_key=api_key or os.environ.get(preset_data["api_key_env"]),
            base_url=base_url or preset_data["base_url"],
            **kwargs,
        )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        preset = os.environ.get("HUST_HELPER_PROVIDER", "openai")
        return cls.from_preset(
            preset,
            model=os.environ.get("HUST_HELPER_MODEL") or None,
            api_key=os.environ.get("HUST_HELPER_API_KEY") or None,
            base_url=os.environ.get("HUST_HELPER_BASE_URL") or None,
        )

    def require_valid(self) -> None:
        if not self.model:
            raise ValueError("A model ID is required")
        if self.provider != "litellm" and not self.base_url:
            raise ValueError("base_url is required")
        if not self.api_key:
            raise ValueError("An API key is required. Use an environment variable or runtime input.")
