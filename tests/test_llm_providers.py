from __future__ import annotations

from types import SimpleNamespace

import pytest

from mdcx.llm import OpenAICompatibleProvider, OpenAIResponsesProvider


@pytest.mark.asyncio
async def test_openai_compatible_provider_uses_chat_completions():
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        message = SimpleNamespace(content="translated")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider = OpenAICompatibleProvider(client)

    result = await provider.complete(
        model="compatible-model",
        system_prompt="system",
        user_prompt="user",
        temperature=0.2,
        extra_body=None,
    )

    assert result == "translated"
    assert captured["messages"][0] == {"role": "system", "content": "system"}


@pytest.mark.asyncio
async def test_openai_provider_uses_responses_api():
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text="translated")

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider = OpenAIResponsesProvider(client)

    result = await provider.complete(
        model="gpt-model",
        system_prompt="system",
        user_prompt="user",
        temperature=0.2,
        extra_body=None,
    )

    assert result == "translated"
    assert captured["instructions"] == "system"
    assert captured["input"] == "user"
