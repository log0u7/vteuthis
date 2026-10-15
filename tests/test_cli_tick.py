import asyncio

from vteuthis.cli import run_tick


class FakeHandle:
    def __init__(self, terminated: list):
        self.terminated = terminated

    async def terminate(self, reason):
        self.terminated.append(reason)


class FakeClient:
    def __init__(self, delay: float):
        self.delay = delay
        self.terminated: list[str] = []

    async def execute_workflow(self, workflow, tick, id, task_queue):
        await asyncio.sleep(self.delay)
        return {"result": "OK: done", "gate": "run"}

    def get_workflow_handle(self, wf_id):
        return FakeHandle(self.terminated)


async def test_run_tick_returns_result_within_timeout():
    out = await run_tick(FakeClient(delay=0.01), tick_timeout_s=5)
    assert out == {"ok": True, "result": {"result": "OK: done", "gate": "run"}}


async def test_run_tick_terminates_workflow_on_timeout():
    client = FakeClient(delay=10)
    out = await run_tick(client, tick_timeout_s=0)
    assert out["ok"] is False
    assert "timed out" in out["error"]
    assert client.terminated == ["tick CLI timeout"]


async def test_run_tick_reports_failure_error():
    from temporalio.exceptions import FailureError

    class Failing:
        async def execute_workflow(self, workflow, tick, id, task_queue):
            raise FailureError("boom")

    out = await run_tick(Failing(), tick_timeout_s=5)
    assert out["ok"] is False
    assert "boom" in out["error"]
