import httpx

from vteuthis.openrouter import complete, credits

API_KEY = "sk-or-test"


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_credits_reads_balance_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/credits"
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        return httpx.Response(200, json={"data": {"total_credits": 100.0, "total_usage": 2.5}})

    total, used = await credits(mock_client(handler), API_KEY)
    assert total == 100.0
    assert used == 2.5


async def test_complete_returns_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/chat/completions"
        body = request.read()
        import json

        parsed = json.loads(body)
        assert parsed["model"] == "some/model"
        assert parsed["max_tokens"] == 800
        assert parsed["messages"] == [{"role": "user", "content": "hi"}]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "hello there"}}]},
        )

    out = await complete(
        mock_client(handler),
        API_KEY,
        model="some/model",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "hello there"
