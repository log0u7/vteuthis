"""Population heartbeat. The schedule fires ONE parent; the parent fans out to
one child workflow per alive agent. Budget partitioning and death redistribution
live in the parent and in controller (deterministic), never in the LLM."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class HeartbeatWorkflow:
    @workflow.run
    async def run(self, tick: int = 0) -> dict:
        population = await workflow.execute_activity(
            "read_population", tick, start_to_close_timeout=timedelta(seconds=30)
        )
        out: dict = {"agents": {}}
        if not population.get("slices"):
            return {"error": "population empty, run: vteuthis spawn N"}
        for agent_id in population["slices"]:
            child = await workflow.execute_child_workflow(
                "AgentWorkflow",
                agent_id,
                id=f"agent-{agent_id}-{workflow.uuid4().hex[:8]}",
                task_queue="vteuthis",
            )
            out["agents"][agent_id] = child
        release = await workflow.execute_activity(
            "sweep_dead", tick, start_to_close_timeout=timedelta(seconds=30)
        )
        out["released"] = release
        return out


@workflow.defn(name="AgentWorkflow")
class AgentWorkflow:
    @workflow.run
    async def run(self, agent_id: str) -> dict:
        out: dict = {"agent_id": agent_id}
        usage = await workflow.execute_activity(
            "snapshot_usage", agent_id, start_to_close_timeout=timedelta(seconds=60)
        )
        sales = await workflow.execute_activity(
            "poll_revenue", agent_id, start_to_close_timeout=timedelta(seconds=60)
        )
        gate = await workflow.execute_activity(
            "controller_gate", agent_id, start_to_close_timeout=timedelta(seconds=60)
        )
        out.update({"usage": usage, "sales": sales.get("new_sales", 0), "gate": gate})
        if gate.get("gate") == "halt":
            return out
        out["tick"] = await workflow.execute_activity(
            "agent_tick", agent_id, start_to_close_timeout=timedelta(minutes=10)
        )
        return out
