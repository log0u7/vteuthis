from __future__ import annotations

import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool

DDG = "https://html.duckduckgo.com/html/"


def validate_tool_url(url: str) -> None:
    """Block SSRF: only http/https to publicly-routable addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"scheme must be http/https: {url!r}")
    host = parsed.hostname
    if not host:
        raise ValueError(f"no host in url: {url!r}")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"cannot resolve host {host!r}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or ip.is_multicast
        ):
            raise ValueError(f"private/internal address blocked: {host} -> {ip}")


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
    validate_tool_url(url)
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


@tool("web_search")
def _web_search_spec(query: str, limit: int = 5) -> dict:
    """Search the public web via DuckDuckGo for demand, competitors and research.
    query: the search terms."""
    raise NotImplementedError("LLM-facing spec only; execute via the TOOLS registry")


@tool("fetch_json")
def _fetch_json_spec(query: str) -> dict:
    """Fetch a public JSON API (prices, markets, filings). query: the full URL to GET."""
    raise NotImplementedError("LLM-facing spec only; execute via the TOOLS registry")


_SPECS = [_fetch_json_spec, _web_search_spec]


def tool_schemas() -> list[dict]:
    """OpenAI function schemas (langchain-core), single source for the prompt."""
    return [convert_to_openai_tool(spec) for spec in _SPECS]


def tools_prompt_block() -> str:
    lines = []
    for schema in tool_schemas():
        fn = schema["function"]
        args = ", ".join(f"{n}: {p['type']}" for n, p in fn["parameters"]["properties"].items())
        lines.append(f"- {fn['name']}({args}): {fn['description']}")
    return "\n".join(lines)
