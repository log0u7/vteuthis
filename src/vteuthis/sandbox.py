from __future__ import annotations

import asyncio
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# ponytail: one shared local docker daemon, per-task isolation only
# (no socket into agent processes). Move to dedicated image registry once
# artifacts need richer runtimes.


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")[:40]
    return slug or "task"


def run_sync(source: str, name: str, *, image: str, timeout_s: int = 120) -> RunResult:
    """Run artifact source as a one-shot non-root container with no network."""
    task_dir = Path("experiments") / f"{int(time.time())}-{_slugify(name)}"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task.py").write_text(source)
    cmd = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--network",
        "none",
        "--memory",
        "512m",
        "--cpus",
        "1.0",
        "--read-only",
        "-v",
        f"{task_dir.resolve()}:/task:ro",
        "-w",
        "/task",
        image,
        "python",
        "task.py",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return RunResult(
            ok=proc.returncode == 0, stdout=proc.stdout[-2000:], stderr=proc.stderr[-2000:]
        )
    except subprocess.TimeoutExpired:
        return RunResult(ok=False, stdout="", stderr=f"timeout after {timeout_s}s")


async def run(source: str, name: str, *, image: str, timeout_s: int = 120) -> RunResult:
    return await asyncio.to_thread(run_sync, source, name, image=image, timeout_s=timeout_s)
