# Next Steps

1. Wire Hermes Telegram gateway messages to `POST /api/inbox/events`.
2. Implement master-router skill as the default owner-message classifier.
3. Add dashboard Inbox widget using `/api/inbox/events/recent` and `/api/approvals/pending`.
4. Verify Telegram cron delivery and enable 09:05 morning brief only after proof.
5. Add A0x worker consumers for `corp:tasks` and emit `agent_events` updates.
6. Add automated tests for inbox API, Redis side effects, and approval storage.
7. Remove or guard destructive dashboard endpoints behind explicit approval.
