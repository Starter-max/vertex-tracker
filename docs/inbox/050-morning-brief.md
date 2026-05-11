# Morning Brief

## Goal

Short 09:05 owner briefing in Telegram with system state, spend, blockers, and decisions needed.

## Required format

Keep it short: 5–7 bullets max. No logs unless asked.

## Data sources

- `/api/system`
- `/api/costs/today`
- `kanban_cards`
- `inbox_events` with `requires_approval=true`
- Redis `corp:alerts`

## Current state

Manual backend data sources work. Cron/Telegram delivery still must be verified before claiming daily brief is live.

## Safe manual check

```bash
curl http://localhost:3000/api/system
curl http://localhost:3000/api/costs/today
curl http://localhost:3000/api/approvals/pending
```

## Disable/repair

Use Hermes cron list/update/remove, but do not edit secrets or `.env`.
