from __future__ import annotations

import json
import re

import httpx

DDG = "https://html.duckduckgo.com/html/"


async def web_search(client: httpx.AsyncClient, query: str, limit: int = 5) -> dict:
    """Key-free web search via DuckDuckGo HTML endpoint."""
    r = await client.get(DDG, params={"q": query}, headers={"User-Agent": "vteuthis/0.0"})
    r.raise_for_status()
    results = _parse_ddg(r.text)[:limit]
    return {"query": query, "results": results}


def _parse_ddg(html: str) -> list[dict]:
    out = []
    for match in re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL
    ):
        href, title = match.group(1), re.sub(r"<[^>]+>", "", match.group(2)).strip()
        out.append({"title": title, "url": href})
    return out


async def fetch_json(client: httpx.AsyncClient, url: str, max_bytes: int = 2_000_000) -> dict:
    """Fetch a key-free public JSON API (Kalshi, Polymarket, CoinGecko, Binance, EDGAR...)."""
    async with client.stream("GET", url, headers={"User-Agent": "vteuthis/0.0"}) as resp:
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        async for chunk in resp.aiter_bytes():
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"response too large (> {max_bytes} bytes)")

    return json.loads(b"".join(chunks))


TOOLS = {
    "web_search": web_search,
    "fetch_json": fetch_json,
}


def tool_names() -> list[str]:
    return sorted(TOOLS)
