"""Repo hygiene guards: the test suite must never threaten the live ledger,
and secrets/artifacts must never be committable."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from vteuthis.config import Config

ROOT = Path(__file__).resolve().parent.parent
LIVE_DSN = re.compile(r"5432/vteuthis(?!_)")


def test_db_dsn_points_at_test_database():
    dsn = Config.load().db_dsn
    assert "vteuthis_test" in dsn, f"refusing to run tests against a live DB: {dsn}"


def test_no_live_dsn_in_test_sources():
    self_name = Path(__file__).name
    offenders = []
    for path in (ROOT / "tests").rglob("*.py"):
        if path.name == self_name:
            continue  # this file legitimately names the live-DSN pattern
        if LIVE_DSN.search(path.read_text()):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"tests reference the live DB DSN: {offenders}"


def test_sensitive_paths_are_gitignored():
    for rel in (".env", "events.csv", "experiments"):
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel], cwd=ROOT, capture_output=True
        )
        assert result.returncode == 0, f"{rel} is not git-ignored"
