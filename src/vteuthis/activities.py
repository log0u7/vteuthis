"""Temporal activities. Thin wrappers: every real decision lives in
vteuthis.controller (deterministic) or vteuthis.agent/graph (LLM proposals).
Secrets stay here, never in agent context."""

from __future__ import annotations

from dataclasses import dataclass, replace

import httpx
from temporalio import activity

from vteuthis import accounting, controller, openrouter, revenue, sandbox
from vteuthis import tools as tools_mod
from vteuthis import vitals as vitals_mod
from vteuthis.config import Config
from vteuthis.population import partition, reallocate

THREAD_PREFIX = "vteuthis"


@dataclass
class Runtime:
    cfg: Config


_runtime: Runtime | None = None


def init_runtime(cfg: Config) -> None:
    global _runtime
    _runtime = Runtime(cfg=cfg)


def rt() -> Runtime:
    if _runtime is None:
        init_runtime(Config.load())
    assert _runtime is not None
    return _runtime


async def _agent_slices(cfg: Config, ledger: accounting.Ledger) -> dict[str, float]:
    """Latest population snapshot from the ledger; bootstrap 'primary' if none."""
    pop = await ledger.events(kind="population", limit=1)
    if pop:
        return pop[0].payload.get("slices", {})
    slices = partition(cfg.initial_usd, ["primary"])
    await ledger.add("population", payload={"slices": slices, "dead": [], "generation": 0})
    return slices


def agent_floor(cfg: Config, slice_usd: float) -> float:
    """Each agent's floor is its share of the global floor: proportional risk."""
    if cfg.initial_usd <= 0:
        return cfg.floor_usd
    return round(cfg.floor_usd * slice_usd / cfg.initial_usd, 4)


@activity.defn(name="read_population")
async def read_population(tick: int) -> dict:
    cfg = rt().cfg
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        slices = await _agent_slices(cfg, ledger)
        return {"slices": slices}
    finally:
        await ledger.close()


@activity.defn(name="snapshot_usage")
async def snapshot_usage(agent_id: str, tick: int = 0) -> dict:
    cfg = rt().cfg
    if not cfg.openrouter_api_key:
        return {"skipped": "OPENROUTER_API_KEY missing"}
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        async with httpx.AsyncClient() as client:
            try:
                total, used = await openrouter.credits(client, cfg.openrouter_api_key)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                return {"skipped": f"openrouter unreachable: {exc.__class__.__name__}"}
        spend_events = await ledger.events(kind="spend", limit=50)
        prev_usage = max((e.payload.get("total_usage", 0.0) for e in spend_events), default=0.0)
        burn = max(used - float(prev_usage), 0.0)
        await ledger.add(
            "spend",
            amount_usd=-round(burn, 4),
            payload={"source": "openrouter-credits", "total_credits": total, "total_usage": used},
            agent_id=agent_id,
        )
        return {"total_credits": total, "total_usage": used, "burn_this_tick": round(burn, 4)}
    finally:
        await ledger.close()


@activity.defn(name="poll_revenue")
async def poll_revenue(agent_id: str, tick: int = 0) -> dict:
    cfg = rt().cfg
    if not cfg.stripe_secret_key:
        return {"skipped": "STRIPE_SECRET_KEY missing", "new_sales": 0}
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        known = {
            e.payload.get("sale_id")
            for e in await ledger.events(kind="revenue", limit=500, agent_id=agent_id)
        }
        async with httpx.AsyncClient() as client:
            try:
                sales = await revenue.poll(client, cfg.stripe_secret_key)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                return {"skipped": f"stripe unreachable: {exc.__class__.__name__}", "new_sales": 0}
        fresh = revenue.filter_new(sales, {k for k in known if k})
        for s in fresh:
            await ledger.add(
                "revenue",
                amount_usd=s.amount,
                experiment_id=s.metadata.get("experiment_id"),
                payload={"sale_id": s.session_id, "currency": s.currency, "created": s.created},
                agent_id=agent_id,
            )
        return {"new_sales": len(fresh)}
    finally:
        await ledger.close()


@activity.defn(name="sweep_dead")
async def sweep_dead(tick: int = 0) -> dict:
    """Redistribute the dead's remaining treasury to the survivors."""
    cfg = rt().cfg
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        slices = await _agent_slices(cfg, ledger)
        dead = [
            e.agent_id for e in await ledger.events(kind="death", limit=50) if e.agent_id in slices
        ]
        dead = sorted(set(dead))
        if not dead:
            return {"redistributed": []}
        fresh = reallocate(slices, dead)
        pops = await ledger.events(kind="population", limit=1)
        generation = (pops[0].payload.get("generation", 0) if pops else 0) + 1
        await ledger.add(
            "population",
            payload={"slices": fresh, "dead": dead, "generation": generation},
        )
        return {"redistributed": dead, "slices": fresh}
    finally:
        await ledger.close()


@activity.defn(name="controller_gate")
async def controller_gate(agent_id: str, tick: int = 0) -> dict:
    cfg = rt().cfg
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        slices = await _agent_slices(cfg, ledger)
        slice_usd = slices.get(agent_id, 0.0)
        summary = await ledger.summary(slice_usd, agent_id=agent_id)
        money = await ledger.events(kinds=["spend", "revenue"], limit=50, agent_id=agent_id)
        plan = controller.tick_plan(
            summary, money, replace(cfg, floor_usd=agent_floor(cfg, slice_usd))
        )
        vitals = vitals_mod.vitals_from(summary["treasury_usd"], agent_floor(cfg, slice_usd), money)
        plan["vitals"] = vitals
        plan["agent_id"] = agent_id
        plan["slice_usd"] = slice_usd

        if plan["gate"] == "halt":
            decisions = await ledger.events(kind="decision", limit=1000, agent_id=agent_id)
            plan["obituary"] = controller.obituary(len(decisions), summary, plan.get("reason", ""))
            await ledger.add("death", payload=plan["obituary"], agent_id=agent_id)
            await ledger.add(
                "decision", payload={"agent": agent_id, "gate": "halt"}, agent_id=agent_id
            )
            return plan

        recent = await ledger.events(kind="decision", limit=10, agent_id=agent_id)
        actions = [(e.payload or {}).get("action") for e in recent]
        actions = [a for a in actions if a]
        plan["tools_used_recently"] = actions
        if controller.idle_drift(actions) and plan.get("mode") != "pivot":
            plan["mode"] = "must_build"
        await ledger.add(
            "decision",
            payload={
                "gate": plan["gate"],
                "mode": plan["mode"],
                "vitals": vitals,
                "framing": cfg.survival_framing,
            },
            agent_id=agent_id,
        )
        return plan
    finally:
        await ledger.close()


class _SandboxRunner:
    def __init__(self, image: str):
        self.image = image

    async def run(self, source: str, name: str):
        return await sandbox.run(source, name, image=self.image)


class _PaymentLinker:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    async def create(
        self, name: str, price_usd: float, description: str = "", metadata=None
    ) -> str:
        async with httpx.AsyncClient() as client:
            return await revenue.create_payment_link(
                client, self.secret_key, name, price_usd, description, metadata
            )


class _ToolsRunner:
    """Controller-side tool executor: network stays outside the agent sandbox."""

    async def run(self, tool: str, args: dict):
        if tool not in tools_mod.TOOLS:
            raise ValueError(f"unknown tool {tool!r}")
        target = args.get("query") or args.get("url") or ""
        async with httpx.AsyncClient() as client:
            fn = tools_mod.TOOLS[tool]
            if tool == "web_search":
                return await fn(client, target)
            return await fn(client, target)


@activity.defn(name="agent_tick")
async def agent_tick(agent_id: str, tick: int = 0, gate_plan: dict | None = None) -> dict:
    """One LangGraph iteration. Money-gated by the workflow, never by the LLM.

    The workflow already ran controller_gate; reuse its plan so the gate is
    evaluated exactly once per tick (no duplicate decision/death events)."""
    cfg = rt().cfg
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    from vteuthis import agent

    if gate_plan is None:
        gate_plan = await controller_gate(agent_id, tick)
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        slices = await _agent_slices(cfg, ledger)
        slice_usd = slices.get(agent_id, 0.0)
        summary = await ledger.summary(slice_usd, agent_id=agent_id)
        summary["pivot"] = gate_plan.get("mode") == "pivot"
        vitals = gate_plan.get("vitals") or {}
        initial_state = agent.initial_tick_state(
            summary=summary,
            mode=gate_plan.get("mode") or "",
            framing=cfg.survival_framing,
            vital_state=vitals.get("state", "stable"),
            vitals=vitals,
            tools_used_recently=gate_plan.get("tools_used_recently") or [],
        )

        if not cfg.openrouter_api_key:
            result = "FAIL: OPENROUTER_API_KEY missing, brain offline"
            await ledger.add(
                "decision", payload={"tick_result": result, "vitals": vitals}, agent_id=agent_id
            )
            return {"result": result, "attempts": 0}

        async with AsyncConnectionPool(
            conninfo=cfg.db_dsn,
            min_size=1,
            max_size=1,
            open=False,
            kwargs={"autocommit": True},  # CREATE INDEX CONCURRENTLY hates transactions
        ) as pool:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()

            llm = openrouter.LLM(
                api_key=cfg.openrouter_api_key,
                model=cfg.model,
                max_tokens=cfg.max_tokens,
                base_url=cfg.openrouter_base_url or openrouter.BASE,
            )
            actions = agent.Actions(
                ledger=ledger,
                cfg=cfg,
                sandbox=_SandboxRunner(cfg.sandbox_image),
                payment_linker=_PaymentLinker(cfg.stripe_secret_key),
                tools=_ToolsRunner(),
                agent_id=agent_id,
            )
            graph = agent.build_graph(llm, actions, checkpointer=saver)
            try:
                state = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": f"{THREAD_PREFIX}-{agent_id}"}},
                )
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                result = f"FAIL: provider rejected the call ({exc.__class__.__name__})"
                await ledger.add(
                    "decision", payload={"tick_result": result, "vitals": vitals}, agent_id=agent_id
                )
                return {"result": result, "attempts": 0}
        result = state.get("result") or "FAIL: no result"
        proposal = state.get("proposal") or {}
        await ledger.add(
            "decision",
            payload={
                "tick_result": result,
                "attempts": state.get("attempts"),
                "action": proposal.get("action"),
                "forced_observe": proposal.get("forced_observe", False),
                "vital_state": initial_state["vital_state"],
                "framing": cfg.survival_framing,
                "vitals": vitals,
            },
            agent_id=agent_id,
        )
        activity.logger.info("agent %s tick: %s", agent_id, result)
        return {"result": result, "attempts": state.get("attempts")}
    finally:
        await ledger.close()


async def _openrouter_treasury(cfg: Config) -> float | None:
    if not cfg.openrouter_api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            total, used = await openrouter.credits(client, cfg.openrouter_api_key)
        return round(total - used, 4)
    except Exception:
        return None
