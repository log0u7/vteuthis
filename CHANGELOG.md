# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- `publish` without a Stripe key now fails gracefully instead of crashing the activity.
- Empty or oversized (60k chars) artifacts rejected before burning a sandbox run.
- Payment links carry `experiment_id` metadata, so polled revenue attaches to its experiment.
- Retrying a failed `build_task` now feeds `previous_failure` back into the agent prompt.

### Added

- Worker logging: tick results visible in worker output; `activity.logger` per tick.
- `vteuthis status` shows live OpenRouter treasury when the key is available.
- `vteuthis tick` prints a hint when no worker is running.

### Changed

- Removed unused `controller.propose_budget` (cap enforced at publish/price level).

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
