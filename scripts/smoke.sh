#!/usr/bin/env bash
# Local end-to-end smoke: real temporal server (compose), real worker, real tick,
# real ledger on vteuthis_test, fake OpenRouter. No real keys, no spend, no live data.
#
# This is the ONLY test of workflow wiring (the Python Temporal test server hangs
# on this stack, see AGENTS.md). Run it after ANY change to workflows.py.
#
# Prereq: docker compose stack up (postgres + temporal).
set -euo pipefail
cd "$(dirname "$0")/.."

export VTEUTHIS_DB_DSN="postgresql://temporal:temporal@localhost:5432/vteuthis_test"
export VTEUTHIS_OPENROUTER_BASE_URL="http://127.0.0.1:9991/api/v1"
export VTEUTHIS_OPENROUTER_API_KEY="smoke-key"
unset OPENROUTER_API_KEY STRIPE_SECRET_KEY 2>/dev/null || true

.venv/bin/python tests/fake_openrouter.py &
FAKE=$!
.venv/bin/python -m vteuthis.cli run &
WORKER=$!
trap 'kill $FAKE $WORKER 2>/dev/null || true' EXIT

echo "== spawn 2 (test db) =="
.venv/bin/python -m vteuthis.cli spawn 2 --force
echo "== tick =="
.venv/bin/python -m vteuthis.cli tick
echo "== status =="
.venv/bin/python -m vteuthis.cli status --all-agents
