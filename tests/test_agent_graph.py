import json

from langgraph.checkpoint.memory import MemorySaver

from vteuthis import agent
from vteuthis.agent import build_graph, initial_tick_state
from vteuthis.config import Config

from .test_agent_smoke import (
    CFG,
    PROPOSAL_BUILD,
    PROPOSAL_PUBLISH,
    SUMMARY,
    FakeLinker,
    FakeLLM,
    FakeSandbox,
    FakeTools,
    run_graph,
)


class FakeEventOwn:
    def __init__(self, name, ok=True, agent_id="primary"):
        self.kind = "experiment"
        self.payload = {"name": name, "ok": ok}
        self.agent_id = agent_id


class FakeLedgerOwn:
    def __init__(self):
        self.journal: list[dict] = []
        self.experiments: list[FakeEventOwn] = []

    async def add(
        self, kind, amount_usd=None, experiment_id=None, payload=None, agent_id="primary"
    ):
        self.journal.append(
            {
                "kind": kind,
                "amount_usd": amount_usd,
                "experiment_id": experiment_id,
                "payload": payload or {},
                "agent_id": agent_id,
            }
        )

    async def events(self, kind=None, kinds=None, limit=50, agent_id=None):
        out = []
        for e in self.experiments:
            if kind and e.kind != kind:
                continue
            if agent_id is not None and e.agent_id != agent_id:
                continue
            out.append(e)
        return out

    async def totals(self, agent_id=None):
        def _sum(kind):
            return sum(
                e["amount_usd"]
                for e in self.journal
                if e["kind"] == kind
                and e["amount_usd"] is not None
                and (agent_id is None or e["agent_id"] == agent_id)
            )

        spend = _sum("spend")
        revenue = _sum("revenue")
        return {
            "spend_total_usd": spend,
            "revenue_total_usd": revenue,
            "net_usd": revenue - abs(spend),
        }


def test_initial_state_resets_attempts_and_result():
    state = initial_tick_state(
        summary={"treasury_usd": 100.0},
        mode="",
        framing="none",
        vital_state="stable",
        vitals={},
        tools_used_recently=[],
    )
    assert state["attempts"] == 0
    assert state["result"] == ""
    assert state["proposal"] == {}


async def test_attempts_reset_across_ticks_same_thread():
    sandbox = FakeSandbox(ok=False, stdout="")

    async def llm(messages, cfg=None):
        return json.dumps({**PROPOSAL_BUILD, "artifact": "raise SystemExit('x')"})

    compiled = build_graph(
        llm, agent.Actions(
            ledger=FakeLedgerOwn(), cfg=CFG, sandbox=sandbox,
            payment_linker=FakeLinker(), tools=FakeTools(), agent_id="a0",
        ),
        checkpointer=MemorySaver(),
    )
    cfg = {"configurable": {"thread_id": "t-reset"}}

    s1 = await compiled.ainvoke({"summary": dict(SUMMARY), "mode": ""}, config=cfg)
    assert s1["attempts"] == 2

    s2 = await compiled.ainvoke(
        {"summary": dict(SUMMARY), "mode": "", "attempts": 0}, config=cfg
    )
    assert s2["attempts"] == 2


def _cfg_with_key():
    return Config(
        initial_usd=100.0, floor_usd=5.0, experiment_cap_usd=2.0, stripe_secret_key="sk_test"
    )


async def test_publish_scoped_to_own_agent():
    ledger = FakeLedgerOwn()
    ledger.experiments = [FakeEventOwn("tiny-clipper", ok=True, agent_id="a0")]

    acts_b = agent.Actions(
        ledger=ledger, cfg=_cfg_with_key(), sandbox=FakeSandbox(),
        payment_linker=FakeLinker(), tools=FakeTools(), agent_id="a1",
    )
    state = await run_graph(FakeLLM.responder(PROPOSAL_PUBLISH), acts_b)
    assert state["result"].startswith("FAIL")

    acts_a = agent.Actions(
        ledger=ledger, cfg=_cfg_with_key(), sandbox=FakeSandbox(),
        payment_linker=FakeLinker(), tools=FakeTools(), agent_id="a0",
    )
    state = await run_graph(FakeLLM.responder(PROPOSAL_PUBLISH), acts_a)
    assert state["result"].startswith("OK")


async def test_build_refused_once_cap_reached():
    ledger = FakeLedgerOwn()
    await ledger.add("spend", amount_usd=-2.0, agent_id="a0")
    acts = agent.Actions(
        ledger=ledger, cfg=CFG, sandbox=FakeSandbox(ok=True, stdout="hi"),
        payment_linker=FakeLinker(), tools=FakeTools(), agent_id="a0",
    )
    state = await run_graph(FakeLLM.responder(PROPOSAL_BUILD), acts)
    assert state["result"].startswith("FAIL")
    assert "experiment cap" in state["result"]


async def test_build_allowed_below_cap():
    ledger = FakeLedgerOwn()
    await ledger.add("spend", amount_usd=-1.0, agent_id="a0")
    acts = agent.Actions(
        ledger=ledger, cfg=CFG, sandbox=FakeSandbox(ok=True, stdout="hi"),
        payment_linker=FakeLinker(), tools=FakeTools(), agent_id="a0",
    )
    state = await run_graph(FakeLLM.responder(PROPOSAL_BUILD), acts)
    assert state["result"].startswith("OK")
