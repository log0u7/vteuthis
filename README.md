# vteuthis (Vampyroteuthis)

![vteuthis, the vampire squid agent, chasing its next dollar](vteuthis-v0.png)

**An autonomous agent that must fund its own inference or die.**

[![CI](https://github.com/log0u7/vteuthis/actions/workflows/ci.yml/badge.svg)](https://github.com/log0u7/vteuthis/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org)
[![lint](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg)](https://www.postgresql.org)

## Why Vampyroteuthis

*Vampyroteuthis infernalis*, the "vampire squid from hell", lives in the ocean's
oxygen minimum zone. It is neither predator nor prey exactly: it drifts through
darkness, extends its filaments to harvest whatever marine snow drifts by, and
lives entirely off what it catches. Its name is a taxonomic joke: not a squid,
not really a vampire, literally hell-born.

`vteuthis` transposes that existence to an LLM agent:

| Vampyroteuthis | vteuthis |
| --- | --- |
| Lives in the oxygen minimum zone | Runs on a finite OpenRouter budget |
| Extends filaments into drifting marine snow | Ships small digital artifacts into an open market |
| Eats what it catches | Burns inference only when the budget allows; earns only what is actually paid |
| Must keep feeding or starve | If the treasury hits the floor, the kill switch stops the loop |

The agent decides **what** to try. The controller decides **whether it may
spend**. Those two roles are deliberately separated: the LLM never sees
credentials, never sets thresholds, never moves money. Everything it earns or
burns is recorded in an append-only ledger, and after a window of
net-negative experiments it is forced to pivot strategy.

## Architecture

```
Temporal Schedule (every 30 min)
  └── HeartbeatWorkflow
        ├── activity read_population  -> latest slices (or bootstrap "primary")
        ├── activity snapshot_usage  -> OpenRouter /credits ONCE, ledger spend as agent_id=account
        ├── child AgentWorkflow per alive agent
        │     ├── activity poll_revenue    -> Stripe checkout sessions, ledger revenue
        │     ├── activity controller_gate -> deterministic rules: floor, cap, ROI pivot
        │     └── activity agent_tick      -> one LangGraph iteration (decide -> act -> evaluate)
        │           ├── build_task -> standalone python script in a Docker sandbox
        │           │                  (non-root, no network, cap-drop, CPU/RAM/time limits)
        │           ├── publish    -> Stripe product+price+payment link (controller-held key)
        │           └── observe    -> record analysis only
        └── activity sweep_dead    -> redistribute dead agents' treasury to survivors
PostgreSQL: single event ledger + LangGraph checkpoints
```

The controller is plain code. The LangGraph graph proposes exactly one JSON
action per tick and cannot touch secrets or money directly.

## Install

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
docker compose up -d          # postgres + temporal + temporal UI (8080)
cp .env.example .env          # then fill keys; umask 077 advised
$(umask 077; chmod 600 .env)
```

Prerequisites (one-time, human):

- OpenRouter API key funded (~100 USD) with a hard credit limit on the key,
  `OPENROUTER_API_KEY` in `.env`
- Stripe secret key (test mode is fine), `STRIPE_SECRET_KEY` in `.env`
- Docker running

## Run

```bash
.venv/bin/python -m vteuthis.cli init    # schema + pull sandbox image + temporal schedule
.venv/bin/python -m vteuthis.cli spawn 3 # population: 3 agents, $33.33 each (or 1)
.venv/bin/python -m vteuthis.cli spawn 3 --force  # wipe a non-empty ledger first
.venv/bin/python -m vteuthis.cli run     # the worker (keep alive)
.venv/bin/python -m vteuthis.cli tick    # manual population cycle (same as scheduled)
.venv/bin/python -m vteuthis.cli status  # ledger summary
.venv/bin/python -m vteuthis.cli status --all-agents
.venv/bin/python -m vteuthis.cli export --csv   # thesis data dump
```

Watch it drift at http://localhost:8080 (Temporal UI).

## Testing and CI

CI (GitHub Actions, `.github/workflows/ci.yml`) runs four jobs: `lint` (ruff),
`unit`, `integration` (postgres service container, `vteuthis_test`), and `sandbox`
(native docker). No secrets and no smoke, so a green run guarantees the decisions,
the money math, and the wiring are correct. The suite never touches the live
ledger: `tests/conftest.py` forces `vteuthis_test` before any import.

A local end-to-end smoke (real worker + tick + ledger, LLM pointed at a key-free
fake OpenRouter, no real keys, no spend). Self-contained and isolated: it starts
its own fake server and worker against `vteuthis_test`, never the live ledger:

```bash
bash scripts/smoke.sh
```

## Survival mechanics (the thesis core)

- **Vitals**: burn EMA, revenue EMA, runway in ticks, and a graded state
  (`thriving → stable → stressed → critical → dying`) injected into every decision.
- **Framing as variable**: `VTEUTHIS_SURVIVAL_FRAMING=none|mild|dire` changes the
  mortality narrative (framing is documented to modulate behavior, arXiv 2508.12920);
  every decision logs its arm, vitals and action.
- **Death**: at the floor the agent halts, a `death` event + obituary are written, and
  `sweep_dead` redistributes the corpse's treasury to the survivors.
- **Anti-idle-drift**: 3 observing ticks in a row force `must_build`.
- **Exploit logging**: rule-touching proposals are journaled for analysis.

## Configuration

Env (see `.env.example`): model (default `z-ai/glm-5.3-flash`, about $0.036/M input
and $0.9/M output), floor, experiment cap, ROI window, tick
interval, sandbox image, temporal address. All money values are USD because the
OpenRouter account credits are USD.

## Survival semantics

- treasury = OpenRouter credits remaining (from `/api/v1/credits`), ledger fallback
- gate `halt` when treasury <= floor: no more agent ticks, schedule stays but flashes no-op
- the shared account burn is recorded once as `agent_id=account` and distributed across
  the alive agents in `Ledger.summary`; each agent's `build_task` is refused once its
  own spend reaches `experiment_cap_usd` (default 2 USD), price proposals clamped 1..50 USD
- after one full net-negative ROI window the agent must pivot (`mode=PIVOT` in its prompt)
- agent-side artifacts run offline in a sandbox: `--network none`, read-only fs,
  non-root, `--cap-drop ALL`, 512 MB RAM, 1 CPU, hard timeout

## Development

```bash
pytest            # unit + integration (accounts tests skip without postgres)
ruff check src tests
```

## Known POC ceilings

- artifact delivery after payment is a plain redirect URL (no gating)
- revenue currency is whatever the payment link uses; treasury math assumes USD
- the whole population runs on a single worker; no parallel workers yet

## Contributing

Issues and pull requests are welcome; read [CONTRIBUTING.md](CONTRIBUTING.md)
first. Security problems never go to public issues: use the private reporting
channel described in [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).