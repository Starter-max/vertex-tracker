#!/usr/bin/env python3
"""Smoke-check Digital Corp Kanban <-> agents <-> skills enrichment.

Checks the live dashboard API because the acceptance criteria are UI/API-level:
- kanban cards include real assigned/curator agent links;
- required skills are JSON arrays;
- matched/missing skills are JSON arrays;
- stalls endpoint is available for Pepe's stuck-work view.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

BASE = "http://localhost:3000"
ROOT = Path(__file__).resolve().parents[1]


def get_json(path: str) -> Any:
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def require(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def main() -> int:
    system = get_json("/api/system")
    require(isinstance(system, dict) and system.get("ts"), "/api/system is not healthy")

    cards = get_json("/api/kanban")
    require(isinstance(cards, list), "/api/kanban must return a list")
    require(cards, "/api/kanban returned no cards")

    linked = [c for c in cards if c.get("effective_assigned_agent_id") or c.get("assigned_agent_id") or c.get("agent_id")]
    require(linked, "no kanban card is linked to an agent")

    for card in linked:
        require("effective_assigned_agent_id" in card, f"card {card.get('id')} missing effective_assigned_agent_id")
        require("assigned_agent_name" in card, f"card {card.get('id')} missing assigned_agent_name")
        require("curator_agent_name" in card, f"card {card.get('id')} missing curator_agent_name")
        require(isinstance(card.get("required_skills", []), list), f"card {card.get('id')} required_skills is not a list")
        require(isinstance(card.get("matched_skills", []), list), f"card {card.get('id')} matched_skills is not a list")
        require(isinstance(card.get("missing_skills", []), list), f"card {card.get('id')} missing_skills is not a list")

    stalls = get_json("/api/agents/stalls")
    require(isinstance(stalls, dict), "/api/agents/stalls must return an object")
    require("threshold_minutes" in stalls, "/api/agents/stalls missing threshold_minutes")
    require("count" in stalls, "/api/agents/stalls missing count")
    require("items" in stalls and isinstance(stalls["items"], list), "/api/agents/stalls.items must be a list")
    require(stalls.get("count") == len(stalls.get("items", [])), "/api/agents/stalls count mismatch")

    html = (ROOT / "dashboard/frontend/index.html").read_text(encoding="utf-8")
    require(html.count("<template ") == html.count("</template>"), "frontend template tag count mismatch")
    for marker in [
        "Генеральные агенты",
        "agentFilterType",
        "agentFilterProject",
        "Пепе видит зависания",
        "openAgentDirectChat",
        "missing_skills",
    ]:
        require(marker in html, f"frontend marker missing: {marker}")

    for doc in [
        "docs/general-agents-module.md",
        "docs/dashboard-agent-api.md",
        "docs/general-agents-acceptance-checklist.md",
        "docs/ops-dashboard-agents-runbook.md",
        "docs/parallel-task-engine-mvp.md",
    ]:
        path = ROOT / doc
        require(path.exists() and path.stat().st_size > 1000, f"documentation missing or too small: {doc}")

    print("OK kanban_integrity")
    print(json.dumps({
        "cards": len(cards),
        "linked_cards": len(linked),
        "stalls": stalls.get("count", len(stalls.get("items", []))),
        "sample": {
            "id": linked[0].get("id"),
            "agent": linked[0].get("effective_assigned_agent_id"),
            "agent_name": linked[0].get("assigned_agent_name"),
            "matched_skills": linked[0].get("matched_skills", []),
            "missing_skills": linked[0].get("missing_skills", []),
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL kanban_integrity: {exc}", file=sys.stderr)
        raise SystemExit(1)
