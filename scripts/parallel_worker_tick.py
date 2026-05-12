#!/usr/bin/env python3
"""Safe Digital Corp parallel worker tick runner.

Default mode is dry-run and bounded. Real Hermes CLI execution is opt-in only via
ALLOW_PARALLEL_WORKER_CLI=true plus explicit work package id if desired.
"""
import json
import os
import sys
import urllib.request

BASE_URL = os.getenv("DIGITAL_CORP_DASHBOARD_URL", "http://localhost:3000").rstrip("/")
WORK_PACKAGE_ID = os.getenv("PARALLEL_WORK_PACKAGE_ID") or None
ALLOW_CLI = os.getenv("ALLOW_PARALLEL_WORKER_CLI", "").lower() in {"1", "true", "yes"}
MAX_ITEMS = max(1, min(int(os.getenv("PARALLEL_WORKER_MAX_ITEMS", "1") or "1"), 5))
TIMEOUT_SECONDS = max(15, min(int(os.getenv("PARALLEL_WORKER_TIMEOUT_SECONDS", "120") or "120"), 600))
DISPATCH_LIMIT = max(1, min(int(os.getenv("PARALLEL_DISPATCH_LIMIT", "1") or "1"), 10))


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS + 30) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def main():
    dispatch_payload = {"limit": DISPATCH_LIMIT}
    worker_payload = {
        "max_items": MAX_ITEMS,
        "allow_cli": ALLOW_CLI,
        "timeout_seconds": TIMEOUT_SECONDS,
    }
    if WORK_PACKAGE_ID:
        dispatch_payload["work_package_id"] = WORK_PACKAGE_ID
        worker_payload["work_package_id"] = WORK_PACKAGE_ID

    dispatch_status, dispatch = post("/api/parallel/dispatcher/tick", dispatch_payload)
    worker_status, worker = post("/api/parallel/worker/tick", worker_payload)
    out = {
        "ok": dispatch_status == 200 and worker_status == 200,
        "base_url": BASE_URL,
        "work_package_id": WORK_PACKAGE_ID,
        "allow_cli": ALLOW_CLI,
        "dispatch": dispatch,
        "worker": worker,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
