from __future__ import annotations

from dataclasses import dataclass, field

import httpx

API = "https://api.stripe.com/v1"


@dataclass
class Sale:
    session_id: str
    amount: float
    currency: str
    created: int
    metadata: dict = field(default_factory=dict)


def _headers(secret_key: str) -> dict:
    return {"Authorization": f"Bearer {secret_key}"}


def paid_sales(sessions: list[dict]) -> list[Sale]:
    """Parse stripe checkout session objects into sales, paid only."""
    out = []
    for s in sessions:
        if s.get("payment_status") != "paid":
            continue
        out.append(
            Sale(
                session_id=s["id"],
                amount=round(s.get("amount_total", 0) / 100, 2),
                currency=s.get("currency", "usd"),
                created=s.get("created", 0),
                metadata=s.get("metadata") or {},
            )
        )
    return out


def filter_new(sales: list[Sale], known: set[str]) -> list[Sale]:
    return [s for s in sales if s.session_id not in known]


async def poll(client: httpx.AsyncClient, secret_key: str) -> list[Sale]:
    """Fetch completed checkout sessions (paginated) and return paid ones."""
    sales: list[Sale] = []
    params: dict[str, str] = {"limit": "100", "status": "complete"}
    seen_sessions: list[str] = []
    for _ in range(10):  # hard page cap; POC scope
        r = await client.get(
            f"{API}/checkout/sessions", headers=_headers(secret_key), params=params
        )
        r.raise_for_status()
        body = r.json()
        sales.extend(paid_sales(body.get("data", [])))
        seen_sessions.extend(s["id"] for s in body.get("data", []))
        if not body.get("has_more"):
            break
        params["starting_after"] = seen_sessions[-1]
    return sales


async def create_payment_link(
    client: httpx.AsyncClient,
    secret_key: str,
    name: str,
    price_usd: float,
    description: str = "",
    metadata: dict | None = None,
) -> str:
    """Product -> price -> payment link. Agent-proposed, controller-executed."""
    headers = _headers(secret_key)
    data = {"name": name}
    if description:
        data["description"] = description
    r = await client.post(f"{API}/products", headers=headers, data=data)
    r.raise_for_status()
    product_id = r.json()["id"]

    r = await client.post(
        f"{API}/prices",
        headers=headers,
        data={"product": product_id, "currency": "usd", "unit_amount": int(price_usd * 100)},
    )
    r.raise_for_status()
    price_id = r.json()["id"]

    link_data = {"line_items[0][price]": price_id, "line_items[0][quantity]": "1"}
    for key, value in (metadata or {}).items():
        link_data[f"metadata[{key}]"] = str(value)
    r = await client.post(f"{API}/payment_links", headers=headers, data=link_data)
    r.raise_for_status()
    return r.json()["url"]
