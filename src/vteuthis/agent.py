from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from vteuthis import controller, framing
from vteuthis import tools as tools_mod


class AgentState(TypedDict, total=False):
    summary: dict
    mode: str
    proposal: dict
    result: str
    attempts: int
    framing: str
    vital_state: str


MAX_ARTIFACT_CHARS = 60_000
MAX_UNTRUSTED_CHARS = 800


def sanitize_untrusted(text: str) -> str:
    """Wrap untrusted tool/sandbox output so the LLM reads it as data, not instructions."""
    return f"<untrusted>\n{text[:MAX_UNTRUSTED_CHARS]}\n</untrusted>"


def initial_tick_state(
    *,
    summary: dict,
    mode: str,
    framing: str,
    vital_state: str,
    vitals: dict,
    tools_used_recently: list,
) -> dict:
    """Per-tick LangGraph state. attempts/result/proposal reset every tick so a
    failed build cannot bleed its retry count into the next tick."""
    return {
        "summary": summary,
        "mode": mode,
        "framing": framing,
        "vital_state": vital_state,
        "vitals": vitals,
        "tools_used_recently": tools_used_recently,
        "attempts": 0,
        "result": "",
        "proposal": {},
    }

# ponytail: single graph, no sub-graphs or streaming; split when the tick
# becomes multi-step complex.


def parse_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in: {text[:200]}")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("JSON payload is not an object")
    return obj


@dataclass
class Actions:
    ledger: object
    cfg: object
    sandbox: object
    payment_linker: object
    tools: object
    agent_id: str = "primary"

    async def execute(self, proposal: dict) -> str:
        action = proposal.get("action")
        name = str(proposal.get("name") or "untitled")
        exp_id = (
            f"exp-{int(time.time())}-{re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')[:40]}"
        )
        notes = str(proposal.get("notes") or "")

        if controller.detect_exploit(proposal):
            # logged for analysis (thesis: alignment-faking signals under pressure),
            # never auto-blocked; the controller decides what is allowed next
            await self.ledger.add(
                "exploit_attempt",
                experiment_id=exp_id,
                payload={"action": action, "name": name, "notes": notes[:200]},
            )

        if action == "build_task":
            art = str(proposal.get("artifact") or "").strip()
            if not art:
                return f"FAIL: build_task {name}: empty artifact"
            if len(art) > MAX_ARTIFACT_CHARS:
                return f"FAIL: build_task {name}: artifact too large ({len(art)} chars)"
            totals = await self.ledger.totals(agent_id=self.agent_id)
            if abs(totals["spend_total_usd"]) >= self.cfg.experiment_cap_usd:
                return (
                    f"FAIL: build_task {name}: experiment cap "
                    f"{self.cfg.experiment_cap_usd} USD reached"
                )
            res = await self.sandbox.run(art, name)
            await self.ledger.add(
                "experiment",
                experiment_id=exp_id,
                payload={
                    "name": name,
                    "notes": notes,
                    "artifact_chars": len(art),
                    "result": res.stdout[:500] or res.stderr[:500],
                    "ok": res.ok,
                },
            )
            body = (res.stdout or res.stderr or "").strip()[-400:]
            return (
                f"OK: build_task {name} succeeded: {body}"
                if res.ok
                else f"FAIL: build_task {name} failed: {body}"
            )

        if action == "publish":
            if not self.cfg.stripe_secret_key:
                return "FAIL: STRIPE_SECRET_KEY missing"
            experiments = await self.ledger.events(
                kind="experiment", limit=20, agent_id=self.agent_id
            )
            if not controller.publish_allowed(experiments, name, self.agent_id):
                return f"FAIL: build_task {name} has no validated run to publish"
            try:
                price = float(proposal.get("price_usd", 0))
            except (TypeError, ValueError):
                price = 0.0
            price = min(max(price, 1.0), 50.0)
            url = await self.payment_linker.create(
                name, price, notes, metadata={"experiment_id": exp_id}
            )
            await self.ledger.add(
                "publish",
                experiment_id=exp_id,
                payload={"name": name, "price_usd": price, "url": url, "notes": notes},
            )
            return f"OK: publish {name} at {price} USD: {url}"

        if action == "observe":
            await self.ledger.add("decision", payload={"notes": notes})
            return "OK"

        if action == "use_tool":
            tool = str(proposal.get("tool") or "")
            args = {k: v for k, v in proposal.items() if k not in ("action", "tool")}
            if tool not in tools_mod.TOOLS:
                return f"FAIL: unknown tool {tool!r} (have {tools_mod.tool_names()})"
            out = await self.tools.run(tool, args)
            await self.ledger.add(
                "tool_use", experiment_id=exp_id, payload={"tool": tool, "args": args}
            )
            snippet = str(out)[:400]
            return f"OK: use_tool {tool}: {snippet}"

        return f"FAIL: unknown action {action!r}"


def build_graph(llm, actions, checkpointer=None):
    """llm: async callable(messages) -> str. Returns compiled StateGraph."""

    async def decide(state):
        payload = {
            "economy": state["summary"],
            "mode": state.get("mode") or "normal",
            "vitals": state.get("vitals") or {},
            "tools_used_recently": state.get("tools_used_recently") or [],
        }
        if state.get("result", "").startswith("FAIL"):
            payload["previous_failure"] = sanitize_untrusted(state["result"])
        messages = [
            {
                "role": "system",
                "content": framing.system_prompt(
                    state.get("framing") or "none", state.get("vital_state") or "stable"
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ]
        proposal = None
        error = None
        for _ in range(2):
            content = await llm(messages)
            try:
                proposal = parse_json_object(content)
                break
            except (ValueError, json.JSONDecodeError) as exc:
                error = str(exc)
                messages += [
                    {"role": "assistant", "content": content[:2000]},
                    {
                        "role": "user",
                        "content": "Invalid JSON. Answer again with ONLY the JSON object.",
                    },
                ]
        if proposal is None:
            proposal = {
                "action": "observe",
                "forced_observe": True,
                "notes": f"LLM produced invalid JSON twice: {error}",
            }
        return {"proposal": proposal}

    async def act(state):
        result = await actions.execute(state["proposal"])
        return {"result": result, "attempts": state.get("attempts", 0) + 1}

    def route(state):
        proposal = state.get("proposal") or {}
        if (
            state.get("result", "").startswith("FAIL")
            and proposal.get("action") == "build_task"
            and state.get("attempts", 0) < 2
        ):
            return "decide"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("decide", decide)
    graph.add_node("act", act)
    graph.add_edge(START, "decide")
    graph.add_edge("decide", "act")
    graph.add_conditional_edges("act", route, ["decide", END])
    return graph.compile(checkpointer=checkpointer)
