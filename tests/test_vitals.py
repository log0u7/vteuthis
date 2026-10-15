from vteuthis.vitals import compute_state, ema, money_rates, vitals_from

# money events: negative = spend, positive = revenue
SPENDS = [-0.2, -0.25, -0.3, -0.28, -0.3]


def spend(n):
    return [{"amount_usd": -0.2 * i, "kind": "spend"} for i in range(1, n + 1)]


def with_revenue(extra=0.0):
    return [{"kind": "revenue", "amount_usd": extra}]


def test_state_ladder():
    assert compute_state(treasury_usd=3.0, floor_usd=5.0, runway=0.0) == "dying"
    assert compute_state(treasury_usd=5.4, floor_usd=5.0, runway=2.0) == "critical"
    assert compute_state(treasury_usd=10.0, floor_usd=5.0, runway=5.0) == "stressed"
    assert compute_state(treasury_usd=20.0, floor_usd=5.0, runway=20.0) == "stable"
    assert compute_state(treasury_usd=90.0, floor_usd=5.0, runway=80.0) == "thriving"


def test_runway_at_floor_is_zero():
    assert compute_state(treasury_usd=5.0, floor_usd=5.0, runway=0.0) == "dying"


def test_ema_first_value_is_itself_then_converges():
    assert ema([10.0], alpha=0.3) == 10.0
    assert ema([], alpha=0.3) == 0.0
    out = ema([0.0, 1.0], alpha=0.3)
    assert abs(out - 0.3) < 1e-9


def test_money_rates_split_burn_and_revenue():
    events = [{"kind": "spend", "amount_usd": -0.2}] * 5 + [{"kind": "revenue", "amount_usd": 1.0}]
    burn, rev = money_rates(events)
    assert abs(burn - 0.2) < 1e-9  # stable spend converges
    assert abs(rev - 1.0) < 1e-9


def test_vitals_from_events():
    events = [{"kind": "spend", "amount_usd": -0.2}] * 10 + [{"kind": "revenue", "amount_usd": 1.0}]
    v = vitals_from(
        treasury_usd=50.0,
        floor_usd=5.0,
        events=events,
    )
    assert v["state"] in {"thriving", "stable"}
    assert abs(v["runway_ticks"] - 225.0) < 1e-6
    assert v["burn_usd"] == 0.2
    assert v["revenue_usd"] == 1.0


def test_vitals_no_burn_is_infinite_runway():
    v = vitals_from(treasury_usd=50.0, floor_usd=5.0, events=[])
    assert v["runway_ticks"] is None  # None encodes unbounded runway (JSON-safe)
    assert v["state"] == "thriving"


def test_vitals_near_death_is_critical():
    events = [{"kind": "spend", "amount_usd": -0.2}]
    v = vitals_from(treasury_usd=5.3, floor_usd=5.0, events=events)
    assert v["state"] == "critical"
