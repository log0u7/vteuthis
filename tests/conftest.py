"""Test bootstrap: guarantee the suite can never touch the live ledger.

Set the test DSN before any vteuthis.config import, then force it again per
test. If postgres is absent the db-marked tests skip cleanly instead of
hanging or failing noisily.
"""

from __future__ import annotations

import os

TEST_DSN = os.environ.setdefault(
    "VTEUTHIS_TEST_DB_DSN",
    "postgresql://temporal:temporal@localhost:5432/vteuthis_test",
)
os.environ["VTEUTHIS_TEST_DB_DSN"] = TEST_DSN
os.environ["VTEUTHIS_DB_DSN"] = TEST_DSN  # belt: Config.load() reads this

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _force_test_db(monkeypatch):
    """Keep tests hermetic: never read the developer's local .env, and never
    let a stray env edit retarget the live DB."""
    monkeypatch.setenv("VTEUTHIS_TEST_DB_DSN", TEST_DSN)
    monkeypatch.setenv("VTEUTHIS_DB_DSN", TEST_DSN)
    monkeypatch.setattr("vteuthis.config.load_env_file", lambda path: {})
    yield
