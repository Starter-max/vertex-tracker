# Current State Audit

Date: 2026-05-11
Runtime path: `/Users/admin/workspace/digital-corp`

## Summary

Ready for MVP: partially yes.

Works:
- Dashboard backend: `http://localhost:3000/` returns 200.
- Backend is launchd-managed: `com.digitalcorp.dashboard-backend`.
- PostgreSQL is running in Docker as `corp-postgres` on `localhost:5432`.
- Redis is running in Docker as `corp-redis` on `localhost:6379`.
- Agent Control Room APIs are live.
- `inbox_events` migration has been created and applied locally.
- Redis stream `corp:inbox` is created by first write.

Not fully proven yet:
- End-to-end Telegram quick commands through Hermes gateway.
- Telegram cron delivery for morning brief.
- Real A0x autonomous workers consuming Redis streams.

## Dashboard

Checked endpoints:
- `/api/system` -> 200
- `/api/projects` -> 200
- `/api/costs/today` -> 200
- `/api/agents/activity` -> 200
- `/api/inbox/events/recent` -> 200
- `/api/approvals/pending` -> 200

Dashboard root contains the Agents tab. Inbox is currently represented by backend APIs; full UI block is next-step work.

## PostgreSQL

Found tables:
- agent_events
- agent_health
- agents
- chat_messages
- chat_sessions
- costs
- inbox_events
- kanban_cards
- knowledge_items
- projects
- settings

## Redis

Streams observed after smoke write:
- `corp:inbox`: length 1
- `corp:tasks`: length 2
- `corp:results`: length 0
- `corp:alerts`: length 0
- `corp:costs`: length 0
- `corp:health`: length 0
- `corp:audit`: length 0
- `corp:approvals`: length 0

## Git

Branch: `dev`.
Recent commits include Agent Control Room and board-send persistence.
Current pass modifies backend, adds `007_inbox_events.sql`, and adds inbox docs.

## Risks

- Existing `/api/kanban/{card_id}` DELETE endpoint exists; router/owner flow must not call it without explicit confirmation.
- Cron delivery previously had target resolution failures; do not claim daily Telegram brief until verified.
- Some dashboard system metrics still check `/Volumes/256`; this is cosmetic/debt, not a blocker for inbox MVP.

## Safe next actions

- Use `POST /api/inbox/events` for received inbox messages.
- Use `GET /api/inbox/events/recent` to inspect recent events.
- Use Redis streams for event bus integration.
