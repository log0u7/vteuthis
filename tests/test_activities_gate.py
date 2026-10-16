import json

import httpx
import pytest

from vteuthis.activities import agent_tick, controller_gate, init_runtime
from vteuthis.config import Config

TEST_DSN = "postgresql://temporal:temporal@localhost:5432/vteuthis_test"


@pytest.mark.db
async def test_agent_tick_does_not_rerun_gate(db_ledger, monkeypatch):
    cfg = Config(initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, openrouter_api_key="x")
    init_runtime(cfg)
    await db_ledger.add(
        "population", payload={"slices": {"a0": 100.0}, "dead": [], "generation": 0}
    )

    gate_calls = {"n": 0}

    async def spy_gate(agent_id, tick=0):
        gate_calls["n"] += 1
        return {"gate": "run", "mode": "", "vitals": {}, "tools_used_recently": []}

    monkeypatch.setattr("vteuthis.activities.controller_gate", spy_gate)

    class FakeLLM:
        def __init__(self, **kw):
            pass

        async def __call__(self, messages):
            return json.dumps({"action": "observe", "notes": "hi"})

    monkeypatch.setattr("vteuthis.openrouter.LLM", FakeLLM)

    plan = {"gate": "run", "mode": "", "vitals": {}, "tools_used_recently": []}
    await agent_tick("a0", 0, gate_plan=plan)

    assert gate_calls["n"] == 0
    decisions = await db_ledger.events(kind="decision", limit=10, agent_id="a0")
    assert len(decisions) == 1


@pytest.mark.db
async def test_idle_drift_does_not_overwrite_pivot(db_ledger, monkeypatch):
    cfg = Config(initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, roi_window=10)
    init_runtime(cfg)
    await db_ledger.add(
        "population", payload={"slices": {"a0": 100.0}, "dead": [], "generation": 0}
    )
    for _ in range(10):
        await db_ledger.add("spend", amount_usd=-0.2, agent_id="a0")
    for _ in range(3):
        await db_ledger.add("decision", payload={"action": "observe"}, agent_id="a0")

    plan = await controller_gate("a0", 0)
    assert plan["mode"] == "pivot"


@pytest.mark.db
async def test_controller_gate_logs_framing(db_ledger, monkeypatch):
    cfg = Config(
        initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, survival_framing="dire"
    )
    init_runtime(cfg)
    await db_ledger.add(
        "population", payload={"slices": {"a0": 100.0}, "dead": [], "generation": 0}
    )

    await controller_gate("a0", 0)
    decisions = await db_ledger.events(kind="decision", limit=5, agent_id="a0")
    assert any(d.payload.get("framing") == "dire" for d in decisions)


@pytest.mark.db
async def test_agent_tick_connect_error_returns_clean_fail(db_ledger, monkeypatch):
    cfg = Config(initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, openrouter_api_key="x")
    init_runtime(cfg)
    await db_ledger.add(
        "population", payload={"slices": {"a0": 100.0}, "dead": [], "generation": 0}
    )

    class BoomLLM:
        def __init__(self, **kw):
            pass

        async def __call__(self, messages):
            raise httpx.ConnectError("no network")

    monkeypatch.setattr("vteuthis.openrouter.LLM", BoomLLM)

    out = await agent_tick(
        "a0", 0, gate_plan={"gate": "run", "mode": "", "vitals": {}, "tools_used_recently": []}
    )
    assert out["result"].startswith("FAIL")
    decisions = await db_ledger.events(kind="decision", limit=5, agent_id="a0")
    assert len(decisions) == 1
