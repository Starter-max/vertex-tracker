#!/usr/bin/env python3
import json
import sys
import time
import urllib.request

BASE = "http://localhost:3000"

def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.status, json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.status, json.loads(r.read().decode())

def main():
    # Guardrail smoke: missing diagnostic/backup + risky metadata must become needs_review, not launch CLI.
    status, guard_wp = post("/api/parallel/work-packages", {
        "title": "Smoke guardrail block",
        "objective": "Validate worker guardrails block risky CLI execution",
        "project_id": "corp",
        "parallel_limit": 1,
        "subtasks": [{
            "title": "risky read/write request should be blocked",
            "instructions": "Do not execute. This is a guardrail test.",
            "metadata": {"destructive": True, "touches_secrets": True},
            "dependency_ids": []
        }]
    })
    assert status == 200, status
    gid = guard_wp["id"]
    post("/api/parallel/dispatcher/tick", {"work_package_id": gid, "limit": 1})
    _, guard_worker = post("/api/parallel/worker/tick", {"work_package_id": gid, "max_items": 1, "allow_cli": True, "timeout_seconds": 60})
    assert guard_worker["guardrail_blocked_count"] == 1, guard_worker
    _, guard_final = get(f"/api/parallel/work-packages/{gid}")
    assert guard_final["status"] == "needs_review", guard_final["status"]

    # Controlled real CLI smoke: safe read-only subtask with diagnostic+backup refs.
    status, cli_wp = post("/api/parallel/work-packages", {
        "title": "Smoke bounded Hermes CLI read-only",
        "objective": "Validate bounded Hermes CLI execution on a harmless read-only prompt",
        "project_id": "corp",
        "parallel_limit": 1,
        "diagnostic_ref": "diag-smoke-20260512",
        "backup_ref": "backup-smoke-20260512",
        "metadata": {"smoke": True, "allow_cli_scope": "read_only"},
        "subtasks": [{
            "title": "read-only CLI proof",
            "instructions": "Return exactly one concise sentence: BOUNDED_WORKER_OK read-only smoke completed. Do not call tools. Do not modify files.",
            "metadata": {"destructive": False, "touches_env": False, "touches_secrets": False, "schema_change": False, "production_change": False, "money_spend": False},
            "dependency_ids": []
        }]
    })
    assert status == 200, status
    cid = cli_wp["id"]
    _, disp = post("/api/parallel/dispatcher/tick", {"work_package_id": cid, "limit": 1})
    assert disp["claimed_count"] == 1, disp
    _, cli_worker = post("/api/parallel/worker/tick", {"work_package_id": cid, "max_items": 1, "allow_cli": True, "timeout_seconds": 180})
    assert cli_worker["mode"] == "hermes_cli", cli_worker
    assert cli_worker["executed_count"] == 1, cli_worker
    assert cli_worker["failed_count"] == 0, cli_worker
    assert cli_worker["guardrail_blocked_count"] == 0, cli_worker
    _, cli_final = get(f"/api/parallel/work-packages/{cid}")
    assert cli_final["status"] == "done", cli_final["status"]
    assert cli_final.get("result_summary"), cli_final

    print(json.dumps({
        "ok": True,
        "guardrail_wp": gid,
        "guardrail_status": guard_final["status"],
        "cli_wp": cid,
        "cli_status": cli_final["status"],
        "cli_worker": cli_worker,
        "result_summary_excerpt": cli_final.get("result_summary", "")[:500],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
