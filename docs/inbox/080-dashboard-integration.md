# Dashboard Integration

## Current dashboard

Root: `http://localhost:3000/`
Backend: launchd service `com.digitalcorp.dashboard-backend`
Frontend files: `dashboard/frontend/`
Backend file: `dashboard/backend/main.py`

## Added/available APIs

- `/api/system`
- `/api/projects`
- `/api/costs/today`
- `/api/agents/activity`
- `/api/agent-events/recent`
- `/api/inbox/events/recent`
- `/api/approvals/pending`

## UI state

Agent tab exists. Full Inbox block is not yet built in the main UI; backend APIs are ready for it.

## Next dashboard addition

Add a compact Inbox widget:
- last 10 inbox events
- pending approvals
- recent alerts
- today costs

Do this only as a small UI patch; do not break existing dashboard.
