# Inbox Event Log

## What it is

Durable journal for owner messages, classification, risk level, approvals, skills/agents used, and final result.

## Files

Migration: `core/migrations/007_inbox_events.sql`
Backend: `dashboard/backend/main.py`

## Table

`inbox_events` fields include:
- `event_id`
- `source`
- `source_message_id`
- `owner_id`
- `raw_text`
- `normalized_intent`
- `intent_class`
- `project_id`
- `priority`
- `risk_level`
- `status`
- `requires_approval`
- `approval_id`
- `agents_used`
- `skills_used`
- `cost_usd`
- `result_summary`
- `error_summary`
- timestamps

## API

Create event:

```bash
curl -X POST http://localhost:3000/api/inbox/events   -H 'Content-Type: application/json'   -d '{"raw_text":"/с","source":"telegram","intent_class":"SYSTEM_STATUS"}'
```

Recent events:

```bash
curl http://localhost:3000/api/inbox/events/recent
```

## Redis side effect

Every created inbox event writes to `corp:inbox`.
If `requires_approval=true`, it also writes to `corp:approvals`.
If risk is medium/high/critical, it writes to `corp:audit`.

## Repair

If API fails, check:
- launchd backend log: `logs/dashboard-backend.err.log`
- migration applied: `docker exec corp-postgres psql -U corp -d digitalcorp -c '\d inbox_events'`
- Redis: `docker exec corp-redis redis-cli XLEN corp:inbox`
