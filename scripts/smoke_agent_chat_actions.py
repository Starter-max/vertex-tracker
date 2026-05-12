#!/usr/bin/env python3
"""Smoke tests for agent chat / kanban task integration.

No secrets. Assumes dashboard backend is running on localhost:3000.
"""

import json
import sys
import time
from urllib import request, error

BASE = "http://localhost:3000"


def http(method, path, payload=None, timeout=20):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(BASE + path, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else None


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    status, health = http("GET", "/api/health")
    assert_true(status == 200 and health.get("status") == "ok", "health endpoint not ok")

    title = f"Smoke scripted: chat task roundtrip {int(time.time())}"
    status, created = http(
        "POST",
        "/api/agent-chats/chat-agent-anton/create-task",
        {
            "title": title,
            "agent_id": "anton",
            "curator_agent_id": "pepe",
            "project_id": "corp",
            "priority": "P2",
            "required_skills": ["testing", "backend_development"],
        },
    )
    assert_true(status == 200 and created.get("ok") is True, "create-task did not return ok")
    task_id = created.get("id")
    assert_true(task_id and task_id.startswith("task-"), "create-task missing task id")
    assert_true(created.get("assigned_agent_id") == "anton", "assigned agent mismatch")
    assert_true(created.get("reply_ids"), "create-task missing reply_ids")

    status, anton = http("GET", "/api/agents/anton")
    agent = anton.get("agent", {})
    assert_true(status == 200, "agent endpoint failed")
    assert_true(agent.get("current_task_id") == task_id, "agent current_task_id was not updated")
    assert_true(agent.get("status") in ("active", "paused"), "agent status was not updated")

    status, activity = http("GET", "/api/agent-activity?agent_id=anton")
    event_pairs = {(row.get("event_type"), row.get("task_id")) for row in activity}
    assert_true(("task_created", task_id) in event_pairs, "missing task_created log")
    assert_true(("task_assigned", task_id) in event_pairs, "missing task_assigned log")

    status, board = http(
        "POST",
        "/api/board/send",
        {"content": "Smoke scripted: board send fallback", "target": "corp"},
    )
    assert_true(status == 200 and board.get("ok") is True, "board_send not ok")
    assert_true(len(board.get("reply_ids", [])) == 3, "board_send should persist 3 replies")

    status, stalls = http("GET", "/api/agents/stalls?threshold_minutes=1")
    assert_true(status == 200 and "items" in stalls, "stalls endpoint failed")

    print(json.dumps({
        "ok": True,
        "created_task_id": task_id,
        "agent_current_task_id": agent.get("current_task_id"),
        "board_reply_ids": board.get("reply_ids"),
        "stalls_count": stalls.get("count"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
