import httpx
import pytest

from vteuthis.revenue import Sale, filter_new, paid_sales, poll

SECRET = "sk_test_123"

PAGE = {
    "data": [
        {
            "id": "cs_paid",
            "payment_status": "paid",
            "amount_total": 500,
            "currency": "eur",
            "created": 1729000000,
            "metadata": {"experiment_id": "exp-1"},
        },
        {
            "id": "cs_unpaid",
            "payment_status": "unpaid",
            "amount_total": 500,
            "currency": "eur",
            "created": 1729000100,
            "metadata": {},
        },
        {
            "id": "cs_refunded_at_seller_request",
            "payment_status": "paid",
            "amount_total": 999,
            "currency": "usd",
            "created": 1729000200,
            "metadata": {},
        },
    ],
    "has_more": False,
}


def handler_factory():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.stripe.com"
        assert request.url.path == "/v1/checkout/sessions"
        assert request.headers["Authorization"] == f"Bearer {SECRET}"
        assert request.url.params.get("status") == "complete"
        return httpx.Response(200, json=PAGE)

    return handler


async def test_poll_returns_only_paid_with_eur_amount():
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_factory()))
    sales = await poll(client, SECRET)
    ids = [s.session_id for s in sales]
    assert ids == ["cs_paid", "cs_refunded_at_seller_request"]
    assert sales[0] == Sale(
        session_id="cs_paid",
        amount=5.0,
        currency="eur",
        created=1729000000,
        metadata={"experiment_id": "exp-1"},
    )


async def test_filter_new_dedupes_on_session_id():
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler_factory()))
    sales = await poll(client, SECRET)
    fresh = filter_new(sales, known={"cs_paid"})
    assert [s.session_id for s in fresh] == ["cs_refunded_at_seller_request"]


def test_paid_sales_parses_money():
    sales = paid_sales(PAGE["data"])
    assert sales[0].amount == 5.0
    assert sales[1].amount == 9.99
    assert [s.session_id for s in sales] == ["cs_paid", "cs_refunded_at_seller_request"]


@pytest.mark.parametrize("bad", [{"id": "x", "payment_status": "unpaid"}])
def test_unpaid_ignored(bad):
    assert paid_sales([bad]) == []


async def test_poll_empty_first_page_with_has_more_does_not_indexerror():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [], "has_more": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sales = await poll(client, SECRET)
    assert sales == []


async def test_poll_paginates_with_starting_after():
    pages = {
        "/v1/checkout/sessions": httpx.Response(
            200, json={"data": [{"id": "cs_1", "payment_status": "paid"}], "has_more": False}
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return pages[request.url.path]

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sales = await poll(client, SECRET)
    assert [s.session_id for s in sales] == ["cs_1"]
