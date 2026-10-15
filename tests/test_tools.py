import httpx
import pytest

from vteuthis.tools import fetch_json, tool_names, validate_tool_url, web_search

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
        assert request.url.host == "93.184.216.34"
        return httpx.Response(200, json={"bitcoin": {"usd": 63000}})

    out = await fetch_json(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        "http://93.184.216.34/prices",
    )
    assert out["bitcoin"]["usd"] == 63000


async def test_fetch_json_rejects_oversize():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"blob": "x" * 100})

    try:
        await fetch_json(
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            "http://93.184.216.34/big",
            max_bytes=10,
        )
        raise AssertionError("should raise")
    except ValueError as exc:
        assert "too large" in str(exc)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "file:///etc/passwd",
        "http://localhost/x",
        "http://127.0.0.1/x",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/x",
        "http://172.16.0.5/x",
        "http://192.168.1.1/x",
        "http://0.0.0.0/x",
        "http://[::1]/x",
    ],
)
def test_validate_tool_url_blocks_bad(url):
    with pytest.raises(ValueError):
        validate_tool_url(url)


def test_validate_tool_url_allows_public_ip():
    validate_tool_url("https://93.184.216.34/data")
    validate_tool_url("http://93.184.216.34/data")
