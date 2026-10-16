import json

import pytest

from vteuthis.activities import agent_tick, init_runtime
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
