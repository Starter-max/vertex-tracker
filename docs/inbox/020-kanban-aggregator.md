# Kanban Aggregator

## Purpose

Safe layer around `kanban_cards` so owner can add/view/move work without manually editing SQL.

## Existing API

- `GET /api/kanban?layer=strategic`
- `POST /api/kanban`
- `PATCH /api/kanban/{card_id}/status`

## Safety rules

- View operations are safe.
- Create operations default to `status=planned`, `priority=P2`.
- Move operations must target one card by id.
- If natural-language search finds multiple candidates, ask owner to choose.
- Do not call DELETE without explicit confirmation.

## Useful SQL

In progress:

```sql
SELECT id,title,project_id,status,priority,moved_at
FROM kanban_cards
WHERE status='in_progress'
ORDER BY priority,moved_at;
```

Blocked/frozen:

```sql
SELECT id,title,project_id,status,priority,moved_at
FROM kanban_cards
WHERE status IN ('blocked','frozen')
ORDER BY priority,moved_at;
```

## Test

```bash
curl http://localhost:3000/api/kanban?layer=strategic
```
