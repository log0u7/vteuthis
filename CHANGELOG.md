# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-10-18

First public release of the POC: agent loop, deterministic controller, multi-agent
population, append-only ledger, Docker sandbox, CI, and the round 9-10 CI and
langchain-core fixes.

### Security

- `tools.fetch_json` validates URLs (scheme + public IP) before streaming: SSRF to
  localhost, private ranges, link-local, and cloud metadata is blocked.
- Sandbox containers hardened: `--cap-drop ALL`, `no-new-privileges`, `--pids-limit`,
  `--memory-swap`, and a `noexec/nosuid` `/tmp` tmpfs.
- Untrusted tool/sandbox output is wrapped in `<untrusted>` delimiters and capped
  before it can reach the agent prompt (prompt-injection channel).
- `Config.load` no longer lets a local `.env` override the real environment.
- `docker-compose.yml` binds postgres/temporal/ui to `127.0.0.1` (was `0.0.0.0`).

### Fixed

- `publish` without a Stripe key now fails gracefully instead of crashing the activity.
- Empty or oversized (60k chars) artifacts rejected before burning a sandbox run.
- Payment links carry `experiment_id` metadata, so polled revenue attaches to its experiment.
- Retrying a failed `build_task` now feeds `previous_failure` back into the agent prompt.
- C1: the shared OpenRouter account burn was written once per agent (N x). It is now
  recorded once as `agent_id=account` and distributed across agents in `Ledger.summary`.
- C2: one failing child workflow no longer aborts the whole population tick.
- C3: `controller_gate` is evaluated exactly once per tick (was twice, writing duplicate
  decision/death events); `agent_tick` reuses the workflow's gate plan.
- C4: LangGraph `attempts`/`result`/`proposal` reset every tick via `initial_tick_state`.
- C5: `publish` is scoped to the acting agent (an agent can no longer sell another's build).
- C6: `build_task` refuses once the agent's spend reaches `experiment_cap_usd`.
- C7: `spawn` refuses to wipe a non-empty ledger without `--force` (agent count capped at 50).
- C8: activities and child workflows carry a `RetryPolicy` and bounded timeouts.
- H1: a failing `sweep_dead` no longer fails the whole tick.
- H2: `roi_verdict` pivots only when the window is net-negative (break-even continues).
- H3: `idle_drift` no longer overwrites `pivot` mode.
- H4: the framing arm is logged on every decision.
- H5: the publish experiment window was 20; raised to 200.
- H6/H7: activities catch `HTTPError`/`ValueError`/`KeyError`, not just `HTTPStatusError`.
- H8: `revenue.poll` no longer raises `IndexError` on an empty first page with `has_more`.

### Added

- CI (GitHub Actions): `lint`, `unit`, `integration` (postgres service), `sandbox`
  (native docker). No secrets, no smoke. Green CI guarantees decisions + money + wiring.
- `tests/conftest.py` forces `vteuthis_test` before any import and neutralizes the local
  `.env`; `test_repo_hygiene.py` fails the suite if the live DB is targeted.
- Local smoke harness: `tests/fake_openrouter.py` + `scripts/smoke.sh` run the real
  worker + tick + ledger against a key-free fake OpenRouter (no real keys, no spend).
- `openrouter` accepts `base_url` (`VTEUTHIS_OPENROUTER_BASE_URL`) for the fake.
- Worker logging: tick results visible in worker output; `activity.logger` per tick.
- `vteuthis status` shows live OpenRouter treasury when the key is available.
- `vteuthis tick` prints a hint when no worker is running.

### Changed

- README: CI/Python/lint badges and hero banner art (`vteuthis-v0.png`); the smoke
  harness description and the POC ceilings now match the multi-agent population.
- Removed unused `controller.propose_budget` (cap enforced at publish/price level).
- CI actions pinned to v7 (`actions/checkout@v7`, `actions/setup-python@v7`, Node 24)
  and runners pinned to `ubuntu-24.04`; the Node 20 deprecation and Ubuntu 26
  migration annotations on every job are gone.
- The agent graph speaks langchain-core messages (`SystemMessage`/`HumanMessage`/
  `AIMessage`); `openrouter.LLM` converts them to OpenAI dicts at the boundary via
  `convert_to_openai_messages`. No new dependency (langchain-core ships with langgraph).
- Tool documentation in the system prompt is generated from the `@tool` specs in
  `tools.py` via `convert_to_openai_tool`, so the prompt cannot drift from the registry.

### Fixed

- `workflows.py` passed multiple positional args to `execute_activity`, which
  temporalio 1.34 rejects (one positional max, rest via `args=[...]`): every tick
  died with a workflow-task TypeError since the retry-policy refactor. `AgentWorkflow`
  now receives `tick` so `agent_tick` gets the full `(agent_id, tick, gate_plan)`
  triple instead of `gate` silently landing in `tick`.
- `scripts/smoke.sh` is now self-contained and isolated: it starts its own worker and
  fake OpenRouter against `vteuthis_test` (no live ledger, no `--force` on live data)
  and is the real workflow-wiring check (the Temporal test server hangs on this stack).
- `snapshot_usage` and the treasury probe polled the real openrouter.ai regardless of
  `VTEUTHIS_OPENROUTER_BASE_URL` (always `401`/skipped when pointed at the fake server);
  both now honor the configured base URL like the LLM client does.
- `docs/markets-note.md` listed dependencies the code never had (`langchain-openai`,
  `typer`, `docker`, `pydantic`); the layout sketch now matches the implementation.

### Added (round 1)

- Temporal heartbeat workflow firing one agent tick every 30 minutes.
- LangGraph decide/act/evaluate graph with Postgres checkpointing.
- Deterministic economic controller: stop-loss floor, experiment burn cap, ROI pivot rule.
- OpenRouter integration: credits endpoint for real treasury, chat completions for inference.
- Stripe integration: polling of completed checkout sessions, payment link creation.
- Docker sandbox runner for agent artifacts (non-root, offline, resource limits).
- PostgreSQL append-only ledger (spend snapshots, revenue, experiments, decisions).
- CLI: `init`, `run`, `tick`, `status`.
- Docker compose stack: postgres, temporal (auto-setup), temporal UI.

[0.1.0]: https://github.com/log0u7/vteuthis/releases/tag/v0.1.0
[0.0.0]: unreleased
## Rounds 3-7 (survival mechanics, population, tooling)

### Added

- `vitals.py`: derived survival signals (burn EMA, revenue EMA, runway ticks,
  `thriving/stable/stressed/critical/dying` state ladder).
- `framing.py`: survival framing arms `none|mild|dire` (arXiv 2508.12920: framing
  modulates behavior) as the thesis experimental variable, plus per-state directives.
- Death = terminal `death` event with a deterministic obituary (ticks alive, earned,
  spent, net, reason).
- Anti-idle-drift guard (CoffeeBench arXiv 2606.16613): 3 consecutive observes force
  `mode=must_build`.
- Exploit-attempt logging: proposals touching controller rules are journaled
  (`kind=exploit_attempt`), never auto-blocked.
- Publish now requires a validated build of the same name.
- Invalid-JSON fallback is a flagged `forced_observe`, visible in analytics.
- `tools.py`: open action surface `use_tool` with `web_search` / `fetch_json`
  (key-free public sources, controller-side execution).
- Population: N agents share the treasury (`population.py` partition/reallocate),
  per-agent ledger (`agent_id`), per-agent floors, heartbeat fans out to child
  workflows; dead agents' balance is redistributed to survivors.
- CLI: `spawn N`, `status --all-agents`, `export [--csv]`.
- Tests run against a dedicated `vteuthis_test` database (never the live ledger).
- Notes: `docs/markets-note.md`, `docs/agents-survival-note.md` (blog-ready).

### Fixed

- ROI pivot rule never fired (money events were drowned by decision events in the
  window fetch); money-only fetch added.
- Unbounded LangGraph thread memory; threads are now per-agent.
- Zombie hangs: `vteuthis tick` now has a bounded timeout and terminates stuck
  workflows; workflow ids carry a unique suffix (no reuse collisions).
- Child workflow id collisions across population ticks.
- `Infinity` crashed JSON ledger writes (runway is now `None` when unbounded).
- Missing API keys degrade gracefully (skip / FAIL decision) instead of infinite
  activity retries; `AsyncConnectionPool` min_size and autocommit fixes for
  `AsyncPostgresSaver`.
- Death events now written on halt, enabling redistribution.
- Test suite no longer wipes the live ledger population (dedicated test DB).
