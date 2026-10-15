from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
from psycopg.types.json import Jsonb

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind TEXT NOT NULL,
    amount_usd NUMERIC(12,4),
    experiment_id TEXT,
    agent_id TEXT NOT NULL DEFAULT 'primary',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""

MIGRATIONS = [
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'primary'",
]


@dataclass
class Event:
    id: int
    kind: str
    amount_usd: float | None = None
    experiment_id: str | None = None
    payload: dict = None
    ts: datetime | None = None
    agent_id: str = "primary"

    def __post_init__(self):
        if self.ts is None:
            self.ts = datetime.now(tz=UTC)


class Ledger:
    """Append-only event store: spend snapshots (negative), revenue (positive),
    decisions and experiments (amount NULL).."""

    def __init__(self, conn):
        self._conn = conn

    @classmethod
    async def connect(cls, dsn: str) -> Ledger:
        conn = await psycopg.AsyncConnection.connect(dsn)
        return cls(conn)

    async def close(self):
        await self._conn.close()

    async def setup(self):
        await self._conn.execute(SCHEMA)
        for migration in MIGRATIONS:
            await self._conn.execute(migration)
        await self._conn.commit()

    async def clear(self):
        """Wipe ledger contents. Bootstrap/test helper."""
        await self._conn.execute("DELETE FROM events")
        await self._conn.commit()

    async def add(
        self,
        kind: str,
        amount_usd: float | None = None,
        experiment_id: str | None = None,
        payload: dict | None = None,
        agent_id: str = "primary",
    ):
        await self._conn.execute(
            "INSERT INTO events (kind, amount_usd, experiment_id, payload, agent_id)"
            " VALUES (%s, %s, %s, %s, %s)",
            (kind, amount_usd, experiment_id, Jsonb(payload or {}), agent_id),
        )
        await self._conn.commit()

    async def events(
        self,
        kind: str | None = None,
        kinds: list[str] | None = None,
        limit: int = 50,
        agent_id: str | None = None,
    ) -> list[Event]:
        sql = "SELECT id, kind, amount_usd, experiment_id, payload, ts, agent_id FROM events"
        params: list = []
        where = []
        if kind:
            where.append("kind = %s")
            params.append(kind)
        elif kinds:
            where.append("kind = ANY(%s)")
            params.append(kinds)
        if agent_id:
            where.append("agent_id = %s")
            params.append(agent_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)
        cur = await self._conn.execute(sql, tuple(params))
        rows = await cur.fetchall()
        return [
            Event(
                id=r[0],
                kind=r[1],
                amount_usd=float(r[2]) if r[2] is not None else None,
                experiment_id=r[3],
                payload=r[4] if isinstance(r[4], dict) else json.loads(r[4]),
                ts=r[5],
                agent_id=r[6],
            )
            for r in rows
        ]

    async def treasury(self, initial_usd: float, agent_id: str | None = None) -> float:
        sql = "SELECT COALESCE(SUM(amount_usd), 0) FROM events WHERE kind IN ('spend', 'revenue')"
        params: tuple = ()
        if agent_id:
            sql += " AND agent_id = %s"
            params = (agent_id,)
        cur = await self._conn.execute(sql, params)
        (total,) = await cur.fetchone()
        return initial_usd + float(total or 0)

    async def totals(self, agent_id: str | None = None) -> dict:
        sql = (
            "SELECT"
            " COALESCE(SUM(amount_usd) FILTER (WHERE kind = 'spend'), 0),"
            " COALESCE(SUM(amount_usd) FILTER (WHERE kind = 'revenue'), 0)"
            " FROM events WHERE kind IN ('spend', 'revenue')"
        )
        params: tuple = ()
        if agent_id:
            sql += " AND agent_id = %s"
            params = (agent_id,)
        cur = await self._conn.execute(sql, params)
        spend, revenue = await cur.fetchone()
        return {
            "spend_total_usd": float(spend or 0),
            "revenue_total_usd": float(revenue or 0),
            "net_usd": float(revenue or 0) - abs(float(spend or 0)),
        }

    async def summary(self, initial_usd: float, agent_id: str | None = None) -> dict:
        totals = await self.totals(agent_id)
        tail = await self.events(limit=10, agent_id=agent_id)
        return {
            "treasury_usd": round(await self.treasury(initial_usd, agent_id), 4),
            **totals,
            "recent_events": [
                {
                    "ts": e.ts.isoformat() if e.ts else None,
                    "kind": e.kind,
                    "amount_usd": e.amount_usd,
                    "experiment_id": e.experiment_id,
                    "payload": e.payload,
                }
                for e in reversed(tail)
            ],
        }


def to_float(value) -> float | None:
    return float(value) if isinstance(value, Decimal) else value
