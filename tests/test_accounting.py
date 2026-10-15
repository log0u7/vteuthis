import asyncio
import os

import psycopg
import pytest

from vteuthis.accounting import Event, Ledger

# Tests NEVER touch the live ledger: pytest would wipe the running population.
DSN = os.environ.get(
    "VTEUTHIS_TEST_DB_DSN", "postgresql://temporal:temporal@localhost:5432/vteuthis_test"
)
pytestmark = pytest.mark.db


def postgres_reachable() -> bool:
    try:
        psycopg.connect(DSN, connect_timeout=2).close()
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not postgres_reachable(), reason="postgres not reachable")


def run(coro_fn):
    async def go():
        ledger = await Ledger.connect(DSN)
        try:
            await ledger.setup()
            await ledger.clear()
            return await coro_fn(ledger)
        finally:
            await ledger.close()

    return asyncio.run(go())


@needs_db
def test_setup_idempotent():
    async def go(ledger: Ledger):
        await ledger.setup()  # second call must not raise
        return True

    assert run(go)


@needs_db
def test_add_and_roundtrip():
    async def go(ledger: Ledger):
        await ledger.add("spend", amount_usd=-0.42, payload={"note": "tick"})
        await ledger.add("revenue", amount_usd=5.0, experiment_id="exp-1")
        rows = await ledger.events()
        return rows

    rows = run(go)
    assert any(r.kind == "spend" and r.amount_usd == -0.42 for r in rows)
    assert any(
        r.kind == "revenue" and r.amount_usd == 5.0 and r.experiment_id == "exp-1" for r in rows
    )


@needs_db
def test_treasury_math():
    async def go(ledger: Ledger):
        before = await ledger.treasury(initial_usd=100.0)
        await ledger.add("spend", amount_usd=-1.50)
        await ledger.add("revenue", amount_usd=3.0)
        after = await ledger.treasury(initial_usd=100.0)
        return after - before

    assert abs(run(go) - 1.5) < 1e-9


@needs_db
def test_summary_totals():
    async def go(ledger: Ledger):
        await ledger.add("spend", amount_usd=-0.2)
        await ledger.add("revenue", amount_usd=2.0)
        return await ledger.summary(initial_usd=100.0)

    s = run(go)
    assert abs(s["revenue_total_usd"] - 2.0) < 1e-9
    assert abs(s["spend_total_usd"] + 0.2) < 1e-9
    assert abs(s["net_usd"] - 1.8) < 1e-9
    assert abs(s["treasury_usd"] - 101.8) < 1e-9


@needs_db
def test_event_from_row():
    async def go(ledger: Ledger):
        await ledger.add("decision", payload={"gate": "run"})
        rows = await ledger.events(kind="decision", limit=1)
        return rows[0]

    e: Event = run(go)
    assert e.kind == "decision"
    assert e.payload == {"gate": "run"}
    assert e.amount_usd is None


@needs_db
def test_events_kinds_filter():
    async def go(ledger: Ledger):
        await ledger.add("spend", amount_usd=-1.0)
        await ledger.add("revenue", amount_usd=5.0)
        await ledger.add("decision", payload={"gate": "run"})
        money = await ledger.events(kinds=["spend", "revenue"])
        dec = await ledger.events(kind="decision")
        return money, dec

    money, dec = run(go)
    assert {e.kind for e in money} == {"spend", "revenue"}
    assert len(money) == 2
    assert len(dec) == 1
    assert dec[0].payload == {"gate": "run"}


@needs_db
def test_agent_id_scopes_events_and_summary():
    async def go(ledger: Ledger):
        await ledger.add("spend", amount_usd=-1.0, agent_id="a")
        await ledger.add("spend", amount_usd=-2.0, agent_id="b")
        await ledger.add("revenue", amount_usd=9.0, agent_id="b")
        a_spend = await ledger.events(kind="spend", agent_id="a")
        b_sum = await ledger.summary(initial_usd=100.0, agent_id="b")
        return a_spend, b_sum

    a_spend, b_sum = run(go)
    assert [e.amount_usd for e in a_spend] == [-1.0]
    assert b_sum["spend_total_usd"] == -2.0
    assert b_sum["revenue_total_usd"] == 9.0
    assert b_sum["treasury_usd"] == 107.0


@needs_db
def test_agent_id_defaults_to_primary():
    async def go(ledger: Ledger):
        await ledger.add("decision", payload={"gate": "run"})
        rows = await ledger.events()
        return rows[0].agent_id

    assert run(go) == "primary"
