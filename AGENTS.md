# AGENTS.md

Scope: this repository only.

## Stack pins

- Python: system 3.12.x (no mise pin); deps in `pyproject.toml`
- Temporal server images pinned in `docker-compose.yml` (auto-setup 1.29.7, ui 2.56.0)
- Never bump dependency majors silently; CHANGELOG first

## Commands

```bash
.venv/bin/python -m pytest tests/ -q   # full suite; db tests use vteuthis_test DB
.venv/bin/ruff check src tests          # must pass
.venv/bin/python -m vteuthis.cli status # quick live read
.venv/bin/python -m vteuthis.cli status --all-agents
.venv/bin/python -m vteuthis.cli tick   # manual population tick (worker must be alive)
.venv/bin/python -m vteuthis.cli spawn 3 # (re)create the population
.venv/bin/python -m vteuthis.cli spawn 3 --force  # wipe a non-empty ledger first
.venv/bin/python -m vteuthis.cli export --csv
bash scripts/smoke.sh                  # local e2e smoke (fake OpenRouter, no real keys)
```

## Runtime facts learned the hard way

- Tests MUST run on `vteuthis_test` (schema via `docker/initdb.sql`), never the live DB:
  `Ledger.clear()` in tests would wipe the running population.
- Temporal `AsyncPostgresSaver` needs autocommit connections (`CREATE INDEX CONCURRENTLY`).
- Child workflow ids must be unique per tick (`workflow.uuid4()`), not per agent name.
- temporalio 1.34+ `execute_activity`/`execute_child_workflow` take ONE positional
  arg; everything else goes in `args=[...]`. Multiple positionals = workflow-task
  TypeError only visible on a real server. `agent_tick` is `(agent_id, tick,
  gate_plan)`; pass all three via `args=[agent_id, tick, gate]` (a positional
  `(agent_id, gate)` silently lands `gate` in `tick`).
- Blocking CLI calls always get a bounded timeout (`run_tick` terminates on timeout).
- psycopg async connections MUST be closed (`try/finally`): a leaked one wedges the
  next test's event loop (2026-10-15 hang).
- The shared OpenRouter burn is recorded ONCE as `agent_id=account` (parent workflow)
  and distributed across agents in `Ledger.summary`; never write it per-agent (N x).
- `controller_gate` is evaluated ONCE per tick in the workflow; `agent_tick` receives
  the plan as `gate_plan` and must not re-run it.
- The Temporal Python test server (`WorkflowEnvironment`) HANGS against this stack
  (worker + postgres pool deadlock). Do not add W-layer tests; cover workflow wiring
  with `scripts/smoke.sh` (self-contained: compose temporal + fake OpenRouter +
  `vteuthis_test` DB + its own worker). Run it after ANY change to `workflows.py`:
  it is the only real check (it caught the temporalio `args=[...]` break, 2026-10-18).
- `Config.load` merges `.env` UNDER the real environment (runtime wins); tests
  neutralize `.env` via conftest.
- The agent graph passes langchain-core messages (`SystemMessage`/`HumanMessage`/
  `AIMessage`); `LLM.__call__` converts them to OpenAI dicts
  (`convert_to_openai_messages`), dicts pass through. Test fakes still capture
  the message objects, not dicts (`m.content`).
- The framing prompt's tool docs are generated from the `@tool` specs in `tools.py`
  (`convert_to_openai_tool`); keep spec names in sync with the `TOOLS` registry
  (drift test in `test_tools.py`).
- CI pins `actions/*@v7` (Node 24) + `ubuntu-24.04`; job annotations must stay
  empty (Node 20 deprecation and Ubuntu 26 migration notices).

## Hard rules

- Money: currency is USD everywhere; `amount_usd` negative = spend, positive = revenue.
- The controller (`vteuthis/controller.py`) is deterministic code. Never move gate
  decisions into prompts or LLM output.
- Secrets live only in `.env` and in `activities.py`. They must never enter LLM
  messages, prompts, or the ledger payload.
- Ledger is append-only: no UPDATE/DELETE outside `Ledger.clear()` (bootstrap/test).
- Artifacts execute only through `vteuthis/sandbox.py`: non-root, `--network none`,
  read-only fs, resource caps. Never loosen to "just make it work".
- Tests first (red -> green). Every new pure function gets a test before its implementation.
- Temporal worker: construct `Worker(...)` then `await worker.run()`. Do NOT use the
  async context manager form (panics TaskLocals on this stack, see worker.py).
- Do not commit `.env`, `experiments/`, or anything containing keys.