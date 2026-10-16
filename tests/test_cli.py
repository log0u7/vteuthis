import pytest

from vteuthis.cli import cmd_spawn
from vteuthis.config import Config


class FakeLedger:
    existing: list = []
    cleared: bool = False
    added: tuple | None = None

    @classmethod
    async def connect(cls, dsn):
        return cls()

    async def setup(self):
        pass

    async def events(self, limit=50):
        return list(self.existing)

    async def clear(self):
        self.cleared = True

    async def add(self, kind, payload=None, **kw):
        self.added = (kind, payload)

    async def close(self):
        pass


@pytest.fixture
def fake_ledger(monkeypatch):
    inst = FakeLedger()

    async def _connect(cls, dsn):
        return inst

    monkeypatch.setattr("vteuthis.accounting.Ledger.connect", classmethod(_connect))
    return inst


async def test_spawn_refuses_non_empty_without_force(fake_ledger):
    fake_ledger.existing = [object()]
    with pytest.raises(SystemExit):
        await cmd_spawn(Config(initial_usd=100.0), 2, force=False)
    assert fake_ledger.cleared is False


async def test_spawn_force_wipes(fake_ledger):
    fake_ledger.existing = [object()]
    await cmd_spawn(Config(initial_usd=100.0), 2, force=True)
    assert fake_ledger.cleared is True
    assert fake_ledger.added[0] == "population"


async def test_spawn_empty_ok_without_force(fake_ledger):
    await cmd_spawn(Config(initial_usd=100.0), 2, force=False)
    assert fake_ledger.cleared is True


async def test_spawn_caps_agent_count(fake_ledger):
    await cmd_spawn(Config(initial_usd=100.0), 999, force=True)
    assert len(fake_ledger.added[1]["slices"]) == 50
