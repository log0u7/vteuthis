from __future__ import annotations

"""Multi-agent population economics. N individuals share one hard budget; when
an agent dies (floor), its remaining treasury is redistributed to survivors:
economic natural selection, no top-up allowed."""


def partition(total_usd: float, agent_ids: list[str]) -> dict[str, float]:
    """Split the treasury into per-agent slices, cent-exact (remainder to first)."""
    if not agent_ids:
        return {}
    cents = round(total_usd * 100)
    base, extra = divmod(cents, len(agent_ids))
    return {
        agent_id: round((base + (1 if i < extra else 0)) / 100, 2)
        for i, agent_id in enumerate(agent_ids)
    }


def reallocate(slices: dict[str, float], dead: list[str]) -> dict[str, float]:
    """Dead agents' balance splits equally among survivors; total conserved."""
    alive = {k: v for k, v in slices.items() if k not in dead}
    if not alive:
        return {}
    released = sum(v for k, v in slices.items() if k in dead)
    cents = round(released * 100)
    ids = sorted(alive)  # deterministic order for the remainder
    base, extra = divmod(cents, len(ids))
    for i, agent_id in enumerate(ids):
        alive[agent_id] = round(alive[agent_id] + (base + (1 if i < extra else 0)) / 100, 2)
    return alive
