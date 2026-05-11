# Quick Commands

## Target commands

- `/д`, `/день` -> run morning brief now
- `/с`, `/статус` -> system status
- `/б`, `/бюджет` -> costs/budget
- `/к`, `/канбан` -> in progress + blocked kanban
- `/г`, `/гит` -> git status/log
- `/з`, `/знания` -> stale knowledge
- `/п [text]` -> create planned kanban task
- `/инбокс` -> recent inbox events
- `/алерты` -> recent alerts
- `/долги` -> stale tasks
- `/стоп` -> cancel/stop safe current operation
- `/риск [text]` -> risk estimate

## Current state

Backend primitives exist for inbox logging and kanban. Full Telegram command routing still needs gateway/Hermes skill wiring and end-to-end Telegram tests.

## How to test backend primitive

```bash
curl -X POST http://localhost:3000/api/inbox/events   -H 'Content-Type: application/json'   -d '{"raw_text":"/к","source":"telegram","intent_class":"KANBAN_VIEW"}'
```
