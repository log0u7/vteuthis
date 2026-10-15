import shutil
import subprocess

import pytest

from vteuthis.sandbox import run_sync

IMAGE = "python:3.12-slim"


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not docker_available(), reason="docker not available"),
]


def test_run_prints_and_succeeds():
    result = run_sync("print('vteuthis-hello')", "smoke-test", image=IMAGE, timeout_s=60)
    assert result.ok, f"stderr: {result.stderr}"
    assert "vteuthis-hello" in result.stdout


def test_run_failing_script_reports_error():
    result = run_sync("raise SystemExit('boom')", "smoke-fail", image=IMAGE, timeout_s=60)
    assert not result.ok
    assert "boom" in result.stderr
