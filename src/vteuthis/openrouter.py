from __future__ import annotations

from dataclasses import dataclass

import httpx

BASE = "https://openrouter.ai/api/v1"


@dataclass
class LLM:
    """Callable wrapper the agent graph uses as its `llm` dependency."""

    api_key: str
    model: str
    max_tokens: int = 800

    async def __call__(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient() as client:
            return await complete(client, self.api_key, self.model, messages, self.max_tokens)


async def credits(client: httpx.AsyncClient, api_key: str) -> tuple[float, float]:
    r = await client.get(f"{BASE}/credits", headers={"Authorization": f"Bearer {api_key}"})
    r.raise_for_status()
    data = r.json()["data"]
    return float(data["total_credits"]), float(data["total_usage"])


async def complete(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 800,
) -> str:
    r = await client.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
