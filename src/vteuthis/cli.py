"""vteuthis CLI: init | run | tick | status | spawn | export."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time

from vteuthis.config import Config

TASK_QUEUE = "vteuthis"
SCHEDULE_ID = "vteuthis-heartbeat"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vteuthis")
    parser.add_argument(
        "command",
        choices=["init", "run", "tick", "status", "spawn", "export"],
    )
    parser.add_argument("count", nargs="?", type=int, default=1, help="spawn: agent count")
    parser.add_argument("--all-agents", action="store_true", help="status: per-agent rows")
    parser.add_argument("--csv", action="store_true", help="export: also write events.csv")
    parser.add_argument("--force", action="store_true", help="spawn: wipe a non-empty ledger")
    args = parser.parse_args(argv)

    cfg = Config.load()
    if not cfg.openrouter_api_key:
        print(
            "OPENROUTER_API_KEY missing (.env) - circle is blind, controller will halt",
            file=sys.stderr,
        )

    dispatch = {
        "init": lambda: cmd_init(cfg),
        "run": lambda: cmd_run(cfg),
        "tick": lambda: cmd_tick(cfg),
        "status": lambda: cmd_status(cfg, all_agents=args.all_agents),
        "spawn": lambda: cmd_spawn(cfg, n=max(args.count, 1), force=args.force),
        "export": lambda: cmd_export(cfg, write_csv=args.csv),
    }
    return asyncio.run(dispatch[args.command]()) or 0


async def cmd_init(cfg: Config) -> None:
    from datetime import timedelta

    from temporalio.client import (
        Client,
        Schedule,
        ScheduleActionStartWorkflow,
        ScheduleAlreadyRunningError,
        ScheduleIntervalSpec,
        ScheduleSpec,
    )

    from vteuthis import accounting
    from vteuthis.activities import init_runtime
    from vteuthis.workflows import HeartbeatWorkflow

    init_runtime(cfg)

    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    await ledger.setup()
    await ledger.close()

    subprocess.run(["docker", "pull", "-q", cfg.sandbox_image], check=False, capture_output=True)

    client = await Client.connect(cfg.temporal_addr)
    try:
        await client.create_schedule(
            SCHEDULE_ID,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    HeartbeatWorkflow.run,
                    0,
                    id="vteuthis-heartbeat",
                    task_queue=TASK_QUEUE,
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(every=timedelta(minutes=cfg.tick_interval_min))]
                ),
            ),
        )
        print(f"schedule {SCHEDULE_ID} created (every {cfg.tick_interval_min} min)")
    except ScheduleAlreadyRunningError:
        print(f"schedule {SCHEDULE_ID} already running")


async def cmd_run(cfg: Config) -> None:
    from vteuthis.activities import init_runtime
    from vteuthis.worker import run_worker

    init_runtime(cfg)
    await run_worker(cfg.temporal_addr)


async def run_tick(client, tick_timeout_s: int) -> dict:
    """Start one population tick and WAIT, but never forever: on timeout the
    workflow is terminated so no zombie retries keep burning the queue."""
    import uuid

    from temporalio.exceptions import FailureError

    from vteuthis.workflows import HeartbeatWorkflow

    wf_id = f"manual-tick-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    try:
        result = await asyncio.wait_for(
            client.execute_workflow(HeartbeatWorkflow.run, 0, id=wf_id, task_queue=TASK_QUEUE),
            timeout=tick_timeout_s,
        )
        return {"ok": True, "result": result}
    except TimeoutError:
        await client.get_workflow_handle(wf_id).terminate(reason="tick CLI timeout")
        return {
            "ok": False,
            "error": f"tick timed out after {tick_timeout_s}s (workflow terminated)",
        }
    except FailureError as exc:
        return {"ok": False, "error": f"workflow failed: {exc}"}


async def cmd_tick(cfg: Config) -> None:
    from temporalio.client import Client

    from vteuthis.activities import init_runtime

    init_runtime(cfg)
    client = await Client.connect(cfg.temporal_addr)
    print("waiting for a running worker (start one with: vteuthis run)...", file=sys.stderr)
    out = await run_tick(client, cfg.tick_timeout_s)
    if not out["ok"]:
        print(out["error"], file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(out["result"], indent=2, default=str))


async def cmd_spawn(cfg: Config, n: int, force: bool = False) -> None:
    """Create/reset the population: n agents, honest treasury partition.
    Destructive: refuses to wipe a non-empty ledger unless --force is passed."""
    from vteuthis import accounting
    from vteuthis.population import partition

    n = max(1, min(n, 50))
    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        await ledger.setup()
        existing = await ledger.events(limit=1)
        if existing and not force:
            print("ledger not empty; pass --force to wipe it", file=sys.stderr)
            raise SystemExit(1)
        ids = [f"a{i}" for i in range(n)]
        slices = partition(cfg.initial_usd, ids)
        await ledger.clear()
        await ledger.add("population", payload={"slices": slices, "dead": [], "generation": 0})
        print(json.dumps(slices, indent=2))
    finally:
        await ledger.close()


async def cmd_status(cfg: Config, all_agents: bool = False) -> None:
    from vteuthis import accounting

    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        slices = await _slices(cfg, ledger)
        if all_agents:
            rows = {}
            for agent_id in slices:
                summary = await ledger.summary(slices[agent_id], agent_id=agent_id)
                rows[agent_id] = summary
            print(json.dumps({"slices": slices, "agents": rows}, indent=2, default=str))
            return
        summary = await ledger.summary(cfg.initial_usd)
        print(json.dumps(summary, indent=2, default=str))
    finally:
        await ledger.close()


async def cmd_export(cfg: Config, write_csv: bool = False) -> None:
    """Full ledger dump (thesis data): JSON to stdout, optional CSV on disk."""
    import csv

    from vteuthis import accounting

    ledger = await accounting.Ledger.connect(cfg.db_dsn)
    try:
        events = await ledger.events(limit=10_000)
        print(json.dumps([e.__dict__ for e in events], indent=2, default=str))
        if write_csv:
            with open("events.csv", "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    ["id", "ts", "kind", "amount_usd", "experiment_id", "agent_id", "payload"]
                )
                for e in events:
                    writer.writerow(
                        [
                            e.id,
                            e.ts.isoformat() if e.ts else "",
                            e.kind,
                            e.amount_usd,
                            e.experiment_id,
                            e.agent_id,
                            json.dumps(e.payload),
                        ]
                    )
            print("wrote events.csv")
    finally:
        await ledger.close()


async def _slices(cfg: Config, ledger) -> dict[str, float]:
    pop = await ledger.events(kind="population", limit=1)
    if pop:
        return pop[0].payload.get("slices", {})
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
