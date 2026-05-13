# Dashboard Agent API Reference

Base URL for local dashboard runtime:

```text
http://localhost:3000
```

## GET `/api/system`

Health and system-status endpoint used as the first dashboard smoke check.

Expected:

- HTTP 200;
- JSON object;
- enough service status to prove the dashboard backend is alive.

Smoke:

```bash
curl -s http://localhost:3000/api/system
```

## GET `/api/agents`

Returns dashboard agents.

Important fields:

- `id`
- `name`
- `type`
- `role`
- `status`
- `current_task_id`
- `next_task_id`
- `last_activity_at`
- `skills`
- `mandate`
- `restrictions`

JSON/JSONB fields must be decoded as arrays/objects, not serialized strings.

Smoke:

```bash
curl -s http://localhost:3000/api/agents | python3 -m json.tool
```

## GET `/api/kanban`

Returns Kanban cards enriched with agent and skill-gap data.

Critical base fields:

- `id`
- `title`
- `status`
- `priority`
- `project_id`
- `assigned_agent_id`
- `curator_agent_id`
- `required_skills`
- `next_step`
- `agent_discussion_id`
- `requires_owner_action`
- `blocked_reason`
- `last_agent_activity_at`

General Agents enrichment fields:

- `effective_assigned_agent_id`
- `assigned_agent_name`
- `assigned_agent_status`
- `assigned_agent_last_activity_at`
- `curator_agent_name`
- `matched_skills`
- `missing_skills`
- `agent_activity_heat` (`0..3`, used by Kanban agent heatmap)
- `agent_activity_state` (`hot`, `warm`, `cool`, `stale`, or `unknown`)
- `agent_activity_age_minutes` when activity timestamp is known

Acceptance:

- At least one real card is linked to a real agent.
- `matched_skills` and `missing_skills` are arrays.
- If the assigned agent lacks task-required skills, `missing_skills` is non-empty.
- Curator agent, when present, resolves to a display name.

Smoke:

```bash
curl -s http://localhost:3000/api/kanban | python3 -m json.tool
python3 scripts/verify_kanban_integrity.py
```

## GET `/api/agents/stalls`

Returns agents whose current task appears stalled.

Response shape:

```json
{
  "threshold_minutes": 120,
  "max_items": 50,
  "count": 0,
  "items": []
}
```

Item fields can include:

- `id`
- `name`
- `status`
- `current_task_id`
- `current_task_title`
- `last_activity_at`
- `inactive_minutes`
- `priority`
- `requires_owner_action`
- `blocked_reason`

Acceptance:

- Endpoint always returns a JSON object, not a raw list.
- `threshold_minutes` is clamped to safe bounds (`5..10080`).
- `max_items` is clamped to safe bounds (`1..200`) and echoed in the response.
- `count == len(items)`.
- Pepe dashboard block can render empty and non-empty states.

Smoke:

```bash
curl -s http://localhost:3000/api/agents/stalls | python3 -m json.tool
```

## POST `/api/board/send`

Sends a message to the corporate board/global agent channel.

Typical body:

```json
{
  "content": "Нужно создать задачу для Антона",
  "target": "corp"
}
```

Expected behavior for General Agents integration:

- persist owner/agent message where applicable;
- trigger the agent response/action path;
- when task creation is requested, create/update a Kanban card;
- update assigned agent `current_task_id` when a task is assigned;
- write `agent_activity_log` rows for task creation/assignment;
- return non-empty reply/message identifiers when actions are produced.

MVP note: if a specific action is still dry-run/stubbed, the response must make that explicit.

Smoke pattern:

```bash
curl -s -X POST http://localhost:3000/api/board/send \
  -H 'Content-Type: application/json' \
  -d '{"content":"Пепе, проверь статус генеральных агентов","target":"corp"}' \
  | python3 -m json.tool
```

## POST `/api/parallel/dispatcher/tick`

Safe MVP dispatcher endpoint for claiming work packages/subtasks.

Body:

```json
{
  "limit": 1,
  "launch_mode": "claim_only"
}
```

Safety defaults:

- default mode: `claim_only`;
- `limit` is clamped to safe maximum;
- endpoint claims/marks work without launching unrestricted agent execution.

Expected response fields:

- `ok`
- `launch_mode`
- `claimed_count`
- `claimed`
- `blocked`

Smoke:

```bash
curl -s -X POST http://localhost:3000/api/parallel/dispatcher/tick \
  -H 'Content-Type: application/json' \
  -d '{"limit":1}' | python3 -m json.tool
```

## POST `/api/parallel/worker/tick`

Bounded worker endpoint for MVP execution checks.

Body:

```json
{
  "max_items": 1,
  "allow_cli": false,
  "timeout_seconds": 30
}
```

Safety defaults:

- default mode is dry-run when CLI execution is not explicitly allowed;
- `allow_cli` defaults to false;
- `max_items` and `timeout_seconds` are clamped.

Expected response fields:

- `ok`
- `mode`
- `allow_cli`
- `executed_count`
- `items`

Smoke:

```bash
curl -s -X POST http://localhost:3000/api/parallel/worker/tick \
  -H 'Content-Type: application/json' \
  -d '{"max_items":1,"allow_cli":false,"timeout_seconds":30}' \
  | python3 -m json.tool
```

## Telegram delivery note

For this local Hermes setup, generic `deliver=telegram` previously produced target-resolution failures.
Use an explicit resolved target for Kevin DM where needed:

```text
telegram:Kevin (dm)
```

Any new cron/job notification path that depends on Telegram must be smoke-tested before it is considered complete.
