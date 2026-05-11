# Testing Report

Date: 2026-05-11
Runtime path: `/Users/admin/workspace/digital-corp`

## Summary

Smoke tests passed for backend, PostgreSQL `inbox_events`, Redis event side effects, approval queue, Agent Control Room APIs, and dashboard root.

## Backend syntax

Command:

```bash
python3 -m py_compile dashboard/backend/main.py
```

Result: passed.

## HTTP endpoints

Checked with curl:

- `/api/system` -> 200
- `/api/projects` -> 200
- `/api/costs/today` -> 200
- `/api/inbox/events/recent` -> 200
- `/api/approvals/pending` -> 200
- `/api/agents/activity` -> 200

## Inbox event write

Command shape:

```bash
curl -X POST http://localhost:3000/api/inbox/events \
  -H 'Content-Type: application/json' \
  -d '{"raw_text":"smoke approval check","source":"smoke-test","owner_id":"89434175","intent_class":"RISK_REVIEW","project_id":"corp","priority":"P1","risk_level":"high","status":"waiting_approval","requires_approval":true,"metadata":{"test":true}}'
```

Result:

- API returned `ok=true`.
- `event_id` was generated.
- `approval_id` was generated.

## PostgreSQL

`inbox_events` table exists and accepts writes.

Observed count after smoke writes: `2`.

## Redis

Observed lengths after smoke writes:

- `corp:inbox`: 2
- `corp:approvals`: 1
- `corp:audit`: 1

This proves first-write stream creation and side effects for approval/risk events.

## Dashboard

Root page checked and contains `🤖 Агенты` tab.

## Launchd backend

Backend is managed by:

`com.digitalcorp.dashboard-backend`

Restart command:

```bash
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.dashboard-backend
```

## Cron

Inspected Hermes cron jobs.

Updated model for:

- `daily-cost-report` -> `openrouter/owl-alpha`
- `morning-brief-inbox-0905` -> `openrouter/owl-alpha`

Created one-shot smoke job:

- `inbox-delivery-smoke-test`
- deliver target: `telegram:Kevin (dm)`
- model: `openrouter/owl-alpha`

Delivery target resolution still needs final observation from Hermes cron list / Telegram receipt before claiming recurring Telegram delivery is fully proven.

## Not fully tested in this pass

- Telegram owner quick commands end-to-end through gateway.
- Full natural-language master-router skill dispatch.
- Real A0x workers consuming `corp:tasks` and emitting results.
- Full Inbox dashboard widget.

## Safety

No `.env` file was edited.
No secrets were printed intentionally.
No DELETE or mass UPDATE was executed.
