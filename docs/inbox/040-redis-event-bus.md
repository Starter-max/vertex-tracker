# Redis Event Bus

## Streams

- `corp:inbox` — owner input events
- `corp:tasks` — tasks delegated to agents
- `corp:results` — agent results
- `corp:alerts` — alerts
- `corp:costs` — cost events
- `corp:health` — agent health
- `corp:audit` — important/risky actions
- `corp:approvals` — pending approvals

## Current integration

`POST /api/inbox/events` writes `corp:inbox`.
If approval is required, it writes `corp:approvals`.
If risk is medium/high/critical, it writes `corp:audit`.

`POST /api/board/send` writes `corp:tasks` and persists into `agent_events`.

## Debug

```bash
docker exec corp-redis redis-cli XLEN corp:inbox
docker exec corp-redis redis-cli XREVRANGE corp:inbox + - COUNT 5
```

## Repair

If streams are missing, create them by first `XADD`; absence before first event is not an error.
