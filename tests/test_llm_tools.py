from __future__ import annotations

from hust_helper.llm import FoodChatAgent, LLMConfig


def test_no_key_uses_local_search():
    config = LLMConfig.from_preset("openai", api_key=None)
    agent = FoodChatAgent(config)
    reply = agent.ask("热干面")
    assert "本地指南" in reply.text
    assert reply.sources
