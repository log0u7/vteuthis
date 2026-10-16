#!/usr/bin/env bash
# Local end-to-end smoke: real worker + schedule + tick + ledger + sandbox,
# with the LLM pointed at a key-free fake OpenRouter. No real keys, no spend.
#
# Prerequisites: the docker compose stack is up (postgres + temporal) and a
# worker is running (.venv/bin/python -m vteuthis.cli run).
set -euo pipefail
cd "$(dirname "$0")/.."

export VTEUTHIS_DB_DSN="${VTEUTHIS_DB_DSN:-postgresql://temporal:temporal@localhost:5432/vteuthis}"
export VTEUTHIS_OPENROUTER_BASE_URL="http://127.0.0.1:9991/api/v1"
export VTEUTHIS_OPENROUTER_API_KEY="${VTEUTHIS_OPENROUTER_API_KEY:-smoke-key}"
unset OPENROUTER_API_KEY STRIPE_SECRET_KEY 2>/dev/null || true

.venv/bin/python tests/fake_openrouter.py &
FAKE=$!
trap 'kill $FAKE 2>/dev/null || true' EXIT
sleep 0.5

echo "== spawn 2 =="
.venv/bin/python -m vteuthis.cli spawn 2
echo "== tick =="
.venv/bin/python -m vteuthis.cli tick
echo "== status =="
.venv/bin/python -m vteuthis.cli status --all-agents
