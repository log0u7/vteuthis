# Security Policy

## Reporting a vulnerability

Do not open a public issue for security problems.

Use GitHub private vulnerability reporting: repository page -> Security ->
Report a vulnerability. Include reproduction steps, affected versions, and
impact. You will get an acknowledgment within 72 hours.

## Scope

- Sandbox escape: root access, network access, a writable host filesystem, or
  resource-cap bypass from an agent-built artifact.
- Prompt injection that reaches the controller: any path where LLM output
  changes spend limits, the treasury floor, or the ledger outside the gate.
- Secret exposure: OpenRouter or Stripe credentials reaching LLM messages,
  prompts, logs, artifacts, or the ledger payload.
- Ledger tampering: writes that are not append-only outside `Ledger.clear()`.
- Malicious artifact execution during build or observation.

## Hardening notes

- The sandbox runs non-root, with `--network none`, a read-only filesystem,
  `--cap-drop ALL`, 512 MB RAM, 1 CPU and a hard timeout. It is never loosened
  to make a build pass.
- Secrets live only in `.env` and `activities.py`; `.env` is gitignored.
- `controller_gate` is deterministic code and is evaluated once per tick.
- The ledger is append-only; death redistribution and budget partitioning are
  controller decisions, never LLM decisions.
