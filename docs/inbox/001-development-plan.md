# Inbox MVP Completion Plan

Goal: close the remaining practical gaps from the original Digital Corp inbox specification without pretending that unfinished autonomous worker paths are complete.

Current baseline:
- Runtime path: `/Users/admin/workspace/digital-corp`.
- Dashboard backend is reachable on `http://localhost:3000/` and launchd-managed by `com.digitalcorp.dashboard-backend`.
- Agent Control Room has real backend APIs and `agent_events` persistence.
- Missing pieces are documentation, explicit inbox event logging, Redis `corp:inbox`/`corp:audit`, approval storage rules, cron model/delivery verification, and final smoke tests.

## MVP scope for this pass

1. Add durable `inbox_events` schema.
2. Add backend helper endpoints that can record inbox events safely:
   - write to PostgreSQL `inbox_events`;
   - write to Redis `corp:inbox` for received messages;
   - write to Redis `corp:audit` for important actions;
   - do not delete or mass-update data.
3. Keep existing `agent_events` for Agent Control Room activity.
4. Document the current state and operational model in `docs/inbox/`.
5. Fix the morning-brief cron model away from broken `claude-sonnet-4` if safely possible.
6. Verify Telegram cron delivery with an explicit target before claiming it works.
7. Update testing report with what passed and what remains limited.
8. Commit and push changes to `origin/dev` after secret scan.

## Deferred beyond this pass

1. Full natural-language Telegram router inside Hermes gateway core.
2. Real autonomous A02/A03/A05/A07 workers that continuously consume `corp:tasks` and emit result/progress events.
3. Full dashboard UX for pending approvals if it becomes larger than a small safe addition.
4. Destructive-action execution. Approval flow records intent only; execution remains guarded.

## Safety rules

- Do not edit `.env` files.
- Do not print secrets.
- Do not run DELETE.
- Do not run mass UPDATE.
- Any schema change must be a new migration file and then applied explicitly.
- If cron delivery cannot be proven, document it and leave recurring brief disabled or marked degraded.

## Implementation steps

1. Inspect backend code and existing migrations.
2. Create `core/migrations/007_inbox_events.sql`.
3. Apply migration to local Postgres and verify table structure.
4. Patch `dashboard/backend/main.py` with minimal inbox endpoints:
   - `POST /api/inbox/events`
   - `GET /api/inbox/events/recent`
   - optional `POST /api/approvals/request`
   - optional `GET /api/approvals/pending`
5. Restart launchd backend and verify endpoints.
6. Generate practical docs:
   - `000-current-state-audit.md`
   - `010-inbox-event-log.md`
   - `020-kanban-aggregator.md`
   - `030-quick-commands.md`
   - `040-redis-event-bus.md`
   - `050-morning-brief.md`
   - `060-approval-flow.md`
   - `070-delegation-layer.md`
   - `080-dashboard-integration.md`
   - `100-operations-manual.md`
   - `110-known-limitations.md`
   - `120-next-steps.md`
7. Inspect cron list; update broken model config for morning brief if possible with available tooling.
8. Run smoke tests:
   - `/api/system`
   - `/api/projects`
   - `/api/inbox/events/recent`
   - `POST /api/inbox/events`
   - Redis `corp:inbox`/`corp:audit`
   - Postgres `inbox_events`
   - dashboard root contains Agent tab
9. Update `090-testing-report.md`.
10. Secret scan, git diff review, commit, push.
