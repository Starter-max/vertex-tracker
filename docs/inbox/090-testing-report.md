# 090 Testing Report

## Scope
MVP inbox + dashboard runtime on internal disk + Agent Control Room API/UI.

## Environment
- Repo: /Users/admin/workspace/digital-corp
- Branch: dev
- Backend: uvicorn main:app on :3000
- Postgres/Redis: docker compose (core)

## Checks
1) Dashboard availability
- GET / -> OK (server alive)
- GET /api/system -> 200
- GET /api/projects -> 200
- GET /api/costs/today -> 200

2) Agent events schema/API
- Migration 006_agent_events.sql applied
- Table `agent_events` exists
- GET /api/agent-events/recent -> 200
- GET /api/agent-events/by-task/task_seed_001 -> 200
- GET /api/agents/activity -> 200

3) Seed validation
- Inserted 3 seed events (delegated/review_started/review_passed)
- Returned in `recent` and `activity` responses

4) Agent Control Room UI
- Added /agents-room route
- Page renders and auto-polls every 5s
- Displays Live feed + Agents activity

## Result
- MVP control room is operational.
- Core inbox/dashboard runtime is stable from internal disk.

## Known caveats
- HEAD / returns 405 (expected for this app shape); use GET for health checks.
- Data is fresh baseline after DB volume recreate.
