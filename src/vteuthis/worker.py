from __future__ import annotations

import logging

from temporalio.client import Client
from temporalio.worker import Worker

from vteuthis.activities import (
    agent_tick,
    controller_gate,
    poll_revenue,
    read_population,
    snapshot_usage,
    sweep_dead,
)
from vteuthis.workflows import AgentWorkflow, HeartbeatWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def run_worker(address: str) -> None:
    client = await Client.connect(address)
    w = Worker(
        client,
        task_queue="vteuthis",
        workflows=[HeartbeatWorkflow, AgentWorkflow],
        activities=[
            read_population,
            snapshot_usage,
            poll_revenue,
            controller_gate,
            agent_tick,
            sweep_dead,
        ],
        max_concurrent_activities=4,
    )
    await w.run()
