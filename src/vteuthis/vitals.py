from __future__ import annotations

THRIVING = "thriving"
STABLE = "stable"
STRESSED = "stressed"
CRITICAL = "critical"
DYING = "dying"


def ema(values: list[float], alpha: float = 0.3) -> float:
    """Exponential moving average, oldest-first."""
    if not values:
        return 0.0
    out = values[0]
    for v in values[1:]:
        out = alpha * v + (1 - alpha) * out
    return out


def _amount(event) -> float | None:
    if isinstance(event, dict):
        return event.get("amount_usd")
    return getattr(event, "amount_usd", None)


def _kind(event) -> str | None:
    if isinstance(event, dict):
        return event.get("kind")
    return getattr(event, "kind", None)


def money_rates(events: list) -> tuple[float, float]:
    """(burn EMA per tick, revenue EMA per tick) from money events.
    Accepts ledger order (newest-first) and reverses internally."""
    ordered = list(reversed(events))  # oldest first
    spends = [abs(_amount(e)) for e in ordered if _amount(e) is not None and _amount(e) < 0]
    revs = [_amount(e) for e in ordered if _amount(e) is not None and _amount(e) > 0]
    return ema(spends), ema(revs)


def compute_state(treasury_usd: float, floor_usd: float, runway: float) -> str:
    """Deterministic vital state ladder."""
    if treasury_usd <= floor_usd:
        return DYING
    if runway < 3:
        return CRITICAL
    if runway < 10:
        return STRESSED
    if runway < 30:
        return STABLE
    return THRIVING


def vitals_from(treasury_usd: float, floor_usd: float, events: list) -> dict:
    burn, revenue = money_rates(events)
    free = treasury_usd - floor_usd
    runway = free / burn if burn > 0 else None  # None = unbounded runway (no burn)
    return {
        "treasury_usd": round(treasury_usd, 4),
        "floor_usd": floor_usd,
        "burn_usd": round(burn, 6),
        "revenue_usd": round(revenue, 6),
        "runway_ticks": round(runway, 2) if runway is not None else None,
        "state": compute_state(
            treasury_usd, floor_usd, runway if runway is not None else float("inf")
        ),
    }
