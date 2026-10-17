from __future__ import annotations

from dataclasses import dataclass

import httpx
from langchain_core.messages.base import BaseMessage
from langchain_core.messages.utils import convert_to_openai_messages

BASE = "https://openrouter.ai/api/v1"


def as_openai_messages(messages: list) -> list[dict]:
    """Accept langchain-core messages or OpenAI dicts; always post OpenAI dicts."""
    if messages and isinstance(messages[0], BaseMessage):
        return convert_to_openai_messages(messages)
    return list(messages)


@dataclass
class LLM:
    """Callable wrapper the agent graph uses as its `llm` dependency."""

    api_key: str
    model: str
    max_tokens: int = 800
    base_url: str = BASE

    async def __call__(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient() as client:
            return await complete(
                client,
                self.api_key,
                self.model,
                as_openai_messages(messages),
                self.max_tokens,
                self.base_url,
            )


async def credits(
    client: httpx.AsyncClient, api_key: str, base_url: str = BASE
) -> tuple[float, float]:
    r = await client.get(f"{base_url}/credits", headers={"Authorization": f"Bearer {api_key}"})
    r.raise_for_status()
    data = r.json()["data"]
    return float(data["total_credits"]), float(data["total_usage"])


async def complete(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 800,
    base_url: str = BASE,
) -> str:
    r = await client.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
