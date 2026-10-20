# Contributing to vteuthis

Thanks for contributing. This repository follows one workflow: issues first,
one branch per topic, Conventional Commits, pull requests only, `main` always
green.

## Setup

Requirements: Python 3.12 and Docker (the compose stack provides Postgres and
Temporal).

```bash
git clone git@github.com:log0u7/vteuthis.git
cd vteuthis
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
docker compose up -d              # postgres + temporal + temporal UI (8080)
cp .env.example .env
(umask 077; chmod 600 .env)       # fill OPENROUTER_API_KEY / STRIPE_SECRET_KEY
.venv/bin/python -m vteuthis.cli init
.venv/bin/python -m pytest -q     # green baseline
```

Never commit `.env`, `experiments/`, or `events.csv`. Tests run against the
`vteuthis_test` database only: `tests/conftest.py` forces it before any import,
so the live ledger is never touched.

## Issues

- Open issues through the templates: **Bug report** or **Feature request**
  (search for duplicates first).
- Bug reports should include reproduction steps, the version tested, and the
  relevant logs (never API keys or tokens).
- **Security problems never go to public issues.** Use GitHub private
  vulnerability reporting (see `SECURITY.md`).
- Inactive issues may be marked stale after 23 days and closed 7 days later
  without updates.

## Branching

- One branch per topic, cut from `main`:
  `feat|fix|chore|docs|test/<scope>`.
- `main` stays green at all times.
- Keep branch scope small: one topic, one review, one merge.

## Commits

Conventional Commits, atomic, English:

```text
feat(controller): clamp experiment cap per tick
fix(sandbox): pass --network none on every build
test(ledger): cover death redistribution
docs(readme): clarify treasury polling
chore(ci): bump actions group
```

- Types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`.
- Subject <= 50 characters, imperative mood; the body explains *why*.
- One commit = one change **plus its test**.
- `CHANGELOG.md` `[Unreleased]` is updated in the same commit for `feat`/`fix`.

## Pull requests

Every change lands through a pull request.

1. Branch off `main`, implement, keep the suite green.
2. Open the PR: Conventional Commit title, `Fixes #N` when an issue exists,
   complete the template checklist honestly.
3. CI must be green: `lint` (ruff), `unit`, `integration` (postgres
   `vteuthis_test`), `sandbox` (docker).
4. Merge with a merge commit, delete the branch.

Any change to `src/vteuthis/workflows.py` also requires
`bash scripts/smoke.sh` locally: it is the only real workflow-wiring check
(fake OpenRouter, isolated test DB, own worker).

## Quality bar

- **TDD, no exceptions**: the failing test first, then the minimal change.
  Bug fixes ship a regression test that fails on `main` before the fix.
- The controller stays deterministic: never move gate decisions into prompts
  or LLM output.
- Secrets stay in `.env` and `activities.py`; they never enter prompts, LLM
  messages, or the ledger payload.
- The sandbox never gets looser: non-root, `--network none`, read-only fs,
  resource caps.
- The ledger is append-only outside `Ledger.clear()`.
- Lint clean (`ruff check src tests`); docs updated when behavior changes.

## Releases

1. Move `CHANGELOG.md` `[Unreleased]` to a dated section.
2. Bump the project version.
3. Tag `vX.Y.Z` on `main` **after** the merge, on the exact merge commit,
   one tag at a time.
