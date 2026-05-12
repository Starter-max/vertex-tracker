# Operations Manual

## Start/Restart backend

```bash
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.dashboard-backend
```

## Logs

- `logs/dashboard-backend.out.log`
- `logs/dashboard-backend.err.log`

## Health checks

```bash
curl http://localhost:3000/api/system
curl http://localhost:3000/api/inbox/events/recent
docker exec corp-postgres psql -U corp -d digitalcorp -c '\d inbox_events'
docker exec corp-redis redis-cli XLEN corp:inbox
```

## Add inbox event

```bash
curl -X POST http://localhost:3000/api/inbox/events   -H 'Content-Type: application/json'   -d '{"raw_text":"status","source":"manual","intent_class":"SYSTEM_STATUS"}'
```

## Common failures

- Backend down: restart launchd and inspect err log.
- Redis stream empty: send a test event.
- Postgres table missing: apply `core/migrations/007_inbox_events.sql`.
