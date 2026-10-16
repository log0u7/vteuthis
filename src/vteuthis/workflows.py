"""Population heartbeat. The schedule fires ONE parent; the parent fans out to
one child workflow per alive agent. Budget partitioning and death redistribution
live in the parent and in controller (deterministic), never in the LLM."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    pass

RETRY = RetryPolicy(maximum_attempts=3)


@workflow.defn
class HeartbeatWorkflow:
    @workflow.run
    async def run(self, tick: int = 0) -> dict:
        population = await workflow.execute_activity(
            "read_population",
            tick,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )
        usage = await workflow.execute_activity(
            "snapshot_usage",
            "account",
            tick,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RETRY,
        )
        out: dict = {"agents": {}, "usage": usage}
        if not population.get("slices"):
            return {"error": "population empty, run: vteuthis spawn N"}
        for agent_id in population["slices"]:
            try:
                child = await workflow.execute_child_workflow(
                    "AgentWorkflow",
                    agent_id,
                    id=f"agent-{agent_id}-{workflow.uuid4().hex[:8]}",
                    task_queue="vteuthis",
                    retry_policy=RETRY,
                )
                out["agents"][agent_id] = child
            except Exception as exc:  # one sick agent must not kill the population
                out["agents"][agent_id] = {"error": f"{exc.__class__.__name__}: {exc}"}
        release = await workflow.execute_activity(
            "sweep_dead",
            tick,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )
        out["released"] = release
        return out


@workflow.defn(name="AgentWorkflow")
class AgentWorkflow:
    @workflow.run
    async def run(self, agent_id: str) -> dict:
        out: dict = {"agent_id": agent_id}
        sales = await workflow.execute_activity(
            "poll_revenue",
            agent_id,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RETRY,
        )
        gate = await workflow.execute_activity(
            "controller_gate",
            agent_id,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RETRY,
        )
        out.update({"sales": sales.get("new_sales", 0), "gate": gate})
        if gate.get("gate") == "halt":
            return out
        out["tick"] = await workflow.execute_activity(
            "agent_tick",
            agent_id,
            gate,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RETRY,
        )
        return out
