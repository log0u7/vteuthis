import httpx

from vteuthis.tools import fetch_json, tool_names, web_search

DDG_HTML = """
<html><body>
<a class="result__a" href="https://x.test/one">First result</a>
<a class="result__a" href="https://x.test/two">Second <b>bold</b> result</a>
</body></html>
"""


def test_tool_names_lists_both():
    assert tool_names() == ["fetch_json", "web_search"]


async def test_web_search_parses_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("q") == "btc"
        return httpx.Response(200, text=DDG_HTML)

    out = await web_search(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "btc")
    assert out["results"] == [
        {"title": "First result", "url": "https://x.test/one"},
        {"title": "Second bold result", "url": "https://x.test/two"},
    ]


async def test_fetch_json_returns_parsed_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.coingecko.com"
        return httpx.Response(200, json={"bitcoin": {"usd": 63000}})

    out = await fetch_json(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        "https://api.coingecko.com/prices",
    )
    assert out["bitcoin"]["usd"] == 63000


async def test_fetch_json_rejects_oversize():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"blob": "x" * 100})

    try:
        await fetch_json(
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            "https://x.test/big",
            max_bytes=10,
        )
        raise AssertionError("should raise")
    except ValueError as exc:
        assert "too large" in str(exc)
