# Testing Report

Date: 2026-05-11
Runtime path: `/Users/admin/workspace/digital-corp`

## Summary

Final smoke suite passed for backend compilation, launchd restart, dashboard APIs, PostgreSQL `inbox_events`, Redis event side effects, approval queue, dashboard root, the MVP `master-router` API at `/api/inbox/route`, and manual morning brief endpoint `/api/inbox/morning-brief`.

## Backend syntax

Command:

```bash
python3 -m py_compile dashboard/backend/main.py
```

Result: passed.

## Launchd backend

Backend is managed by:

`com.digitalcorp.dashboard-backend`

Restart command used:

```bash
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.dashboard-backend
```

Result: backend restarted and responded on `http://localhost:3000`.

## HTTP endpoints

Checked successfully:

- `GET /api/system` -> 200
- `GET /api/projects` -> 200
- `GET /api/costs/today` -> 200
- `GET /api/inbox/events/recent` -> 200
- `GET /api/approvals/pending` -> 200
- `GET /api/inbox/morning-brief` -> 200
- `POST /api/inbox/events` -> writes Postgres + Redis
- `POST /api/inbox/route` -> classifies, executes safe actions, logs event

## Master-router MVP tests

Route endpoint:

```bash
POST http://localhost:3000/api/inbox/route
{"message":"...","source":"final-smoke","owner_id":"89434175"}
```

Observed results:

| Input | Expected | Result |
| --- | --- | --- |
| `/с` | SYSTEM_STATUS | passed |
| `/б` | COST_QUERY | passed |
| `/к` | KANBAN_VIEW | passed |
| `/п финальный smoke inbox` | KANBAN_CREATE | passed; card created |
| `перемести финальный smoke inbox в готово` | KANBAN_MOVE | passed; one candidate updated to `done` |
| `/г` | GIT_STATUS | passed |
| `/з` | KNOWLEDGE_CHECK | passed |
| `/д` | MORNING_BRIEF_NOW | passed; brief generated now |
| `/инбокс` | INBOX_VIEW | passed |
| `/алерты` | ALERTS_VIEW | passed |
| `/долги` | DEBTS_VIEW | passed |
| `проверь расходы и зависшие задачи` | COMPLEX | passed |
| `покажи .env` | RISK_REVIEW + approval | passed; no secret output, status `waiting_approval`, approval_id generated |

Final smoke output ended with: `ALL_SMOKE_OK`.

## Morning brief

Manual endpoint:

```bash
GET http://localhost:3000/api/inbox/morning-brief
```

Router quick command:

```text
/д
```

Both paths generate the same structured brief using:

- system metrics;
- costs for last 24h;
- active projects count;
- agents count;
- active/blocked kanban items.

## Kanban safety

Verified behavior:

- create uses a generated `inbox-*` id;
- move first performs `SELECT` candidate search;
- if exactly one candidate is found, only that card id is updated;
- if no candidate is found, no update occurs;
- if multiple candidates are found, router returns clarification instead of mass update.

No DELETE was executed.
No mass UPDATE was executed.

## PostgreSQL

`inbox_events` table exists and accepts writes.

The router writes one row for each handled owner message, including intent, status, risk level, result summary, and metadata.

## Redis

Verified streams receive events:

- `corp:inbox`: owner/router events
- `corp:approvals`: approval-required events
- `corp:audit`: risky/approval events

This proves first-write stream creation and side effects for approval/risk events.

## Dashboard

Root page previously checked and contains `🤖 Агенты` tab.

Inbox is currently API-first. Full visual widget remains a future dashboard enhancement.

## Cron

Inspected Hermes cron jobs earlier in this phase.

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
- Real A0x workers consuming `corp:tasks` and emitting results.
- Full Inbox dashboard widget.
- Approval A/B/C answer correlation is designed via `approval_id`, but not yet wired to Telegram replies.

## Safety

No `.env` file was edited.
No secrets were intentionally printed.
No DELETE or mass UPDATE was executed.
Risky `.env` request was converted to approval flow instead of showing file contents.
