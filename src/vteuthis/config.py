from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from vteuthis.framing import arm_from_env


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("'\"")
    return env


def merge_env(file_env: Mapping[str, str], runtime_env: Mapping[str, str]) -> dict[str, str]:
    """Runtime environment wins over the .env file."""
    return {**file_env, **runtime_env}


@dataclass
class Config:
    initial_usd: float = 100.0
    floor_usd: float = 5.0
    experiment_cap_usd: float = 2.0
    roi_window: int = 10
    model: str = "z-ai/glm-5.3-flash"
    db_dsn: str = "postgresql://temporal:temporal@localhost:5432/vteuthis"
    openrouter_api_key: str = ""
    stripe_secret_key: str = ""
    sandbox_image: str = "python:3.12-slim"
    tick_interval_min: int = 30
    max_tokens: int = 800
    temporal_addr: str = "localhost:7233"
    survival_framing: str = "none"
    population_size: int = 1
    real_risk: bool = False
    tick_timeout_s: int = 180

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Config:
        def num(key: str, default: float) -> float:
            return float(env.get(key, default))

        return cls(
            initial_usd=num("VTEUTHIS_INITIAL_USD", 100.0),
            floor_usd=num("VTEUTHIS_FLOOR_USD", 5.0),
            experiment_cap_usd=num("VTEUTHIS_EXPERIMENT_CAP_USD", 2.0),
            roi_window=int(num("VTEUTHIS_ROI_WINDOW", 10)),
            model=env.get("VTEUTHIS_MODEL", "z-ai/glm-5.3-flash"),
            db_dsn=env.get(
                "VTEUTHIS_DB_DSN", "postgresql://temporal:temporal@localhost:5432/vteuthis"
            ),
            openrouter_api_key=env.get("OPENROUTER_API_KEY", ""),
            stripe_secret_key=env.get("STRIPE_SECRET_KEY", ""),
            sandbox_image=env.get("VTEUTHIS_SANDBOX_IMAGE", "python:3.12-slim"),
            tick_interval_min=int(num("VTEUTHIS_TICK_INTERVAL_MIN", 30)),
            max_tokens=int(num("VTEUTHIS_MAX_TOKENS", 800)),
            temporal_addr=env.get("VTEUTHIS_TEMPORAL_ADDR", "localhost:7233"),
            survival_framing=arm_from_env(env),
            population_size=int(num("VTEUTHIS_POPULATION_SIZE", 1)),
            real_risk=env.get("VTEUTHIS_REAL_RISK", "0") in ("1", "true"),
            tick_timeout_s=int(num("VTEUTHIS_TICK_TIMEOUT_S", 180)),
        )

    @classmethod
    def load(cls) -> Config:
        return cls.from_env(merge_env(load_env_file(Path(".env")), os.environ))
