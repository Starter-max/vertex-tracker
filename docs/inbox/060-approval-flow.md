# Approval Flow

## When to ask owner

Ask before:
- deleting data
- changing `.env` or keys
- mass UPDATE/DELETE
- DB migration application
- external access/deploy
- spend over $2
- unclear project with substantial consequences

## Storage

MVP stores pending approvals as `inbox_events` rows with:
- `requires_approval=true`
- `approval_id=appr_*`
- `status=waiting_approval` or `received`

The event is also written to Redis `corp:approvals`.

## API

Pending approvals:

```bash
curl http://localhost:3000/api/approvals/pending
```

## Owner question template

Need confirmation.
Want: [action]
Risk: [short]
Cost: [$ if any]
Rollback: [yes/no]
A — yes, do it
B — no, cancel
C — safer variant
