import httpx

from vteuthis.revenue import create_payment_link

SECRET = "sk_test_123"
CALLS: list[tuple[str, dict]] = []


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    body = httpx.QueryParams(request.content.decode()) if request.method == "POST" else {}
    if path == "/v1/products":
        CALLS.append(("product", {"name": body.get("name")}))
        return httpx.Response(200, json={"id": "prod_1"})
    if path == "/v1/prices":
        CALLS.append(
            ("price", {"unit_amount": body.get("unit_amount"), "product": body.get("product")})
        )
        return httpx.Response(200, json={"id": "price_1"})
    if path == "/v1/payment_links":
        CALLS.append(
            (
                "link",
                {
                    "line_items[0][price]": body.get("line_items[0][price]"),
                    "metadata[experiment_id]": body.get("metadata[experiment_id]"),
                },
            )
        )
        return httpx.Response(
            200, json={"id": "plink_1", "url": "https://pay.example/link/plink_1"}
        )
    return httpx.Response(404, json={"error": {"message": "unknown path"}})


async def test_create_payment_link_three_step_flow():
    CALLS.clear()
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    url = await create_payment_link(
        client,
        SECRET,
        "tiny-clipper",
        5.0,
        description="a tool",
        metadata={"experiment_id": "exp-42"},
    )
    assert url == "https://pay.example/link/plink_1"
    assert CALLS[0] == ("product", {"name": "tiny-clipper"})
    assert CALLS[1] == ("price", {"unit_amount": "500", "product": "prod_1"})
    assert CALLS[2] == (
        "link",
        {"line_items[0][price]": "price_1", "metadata[experiment_id]": "exp-42"},
    )
