import pytest

from vteuthis.activities import init_runtime, snapshot_usage
from vteuthis.config import Config

TEST_DSN = "postgresql://temporal:temporal@localhost:5432/vteuthis_test"


@pytest.mark.db
async def test_account_burn_recorded_once_and_distributed(db_ledger, monkeypatch):
    cfg = Config(initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, openrouter_api_key="x")
    init_runtime(cfg)
    await db_ledger.add(
        "population", payload={"slices": {"a0": 50.0, "a1": 50.0}, "dead": [], "generation": 0}
    )

    async def fake_credits(client, key, *, base_url=None):
        return (100.0, 1.0)  # account delta of 1.0 this tick

    monkeypatch.setattr("vteuthis.openrouter.credits", fake_credits)

    await snapshot_usage("account", 0)

    spends = await db_ledger.events(kind="spend", limit=10)
    assert len(spends) == 1
    assert spends[0].agent_id == "account"
    assert abs(spends[0].amount_usd - (-1.0)) < 0.01

    s0 = await db_ledger.summary(50.0, agent_id="a0")
    assert abs(s0["treasury_usd"] - 49.5) < 0.01


@pytest.mark.db
async def test_snapshot_usage_malformed_200_does_not_crash(db_ledger, monkeypatch):
    cfg = Config(initial_usd=100.0, floor_usd=5.0, db_dsn=TEST_DSN, openrouter_api_key="x")
    init_runtime(cfg)

    async def bad_credits(client, key, *, base_url=None):
        raise KeyError("data")

    monkeypatch.setattr("vteuthis.openrouter.credits", bad_credits)

    out = await snapshot_usage("a0", 0)
    assert isinstance(out, dict)
    assert "skipped" in out or "error" in out


@pytest.mark.db
async def test_snapshot_usage_uses_configured_base_url(db_ledger, monkeypatch):
    cfg = Config(
        initial_usd=100.0,
        floor_usd=5.0,
        db_dsn=TEST_DSN,
        openrouter_api_key="x",
        openrouter_base_url="http://fake.test/api/v1",
    )
    init_runtime(cfg)
    seen = {}

    async def fake_credits(client, key, *, base_url=None):
        seen["base_url"] = base_url
        return (100.0, 0.0)

    monkeypatch.setattr("vteuthis.openrouter.credits", fake_credits)

    await snapshot_usage("account", 0)
    assert seen["base_url"] == "http://fake.test/api/v1"
