# Agent chat → kanban task integration

## Purpose

This module connects owner/agent messages to real kanban work. A chat message can become a kanban card, update the assigned agent, and write observable activity-log facts.

Core rule: chat is communication, kanban is work state, agent_activity_log is the factual audit trail.

## Endpoints

### POST /api/agent-chats/{chat_id}/messages

Creates an owner/agent/system message in an agent chat.

Important behavior:
- Owner message in a personal chat notifies that chat agent.
- Owner message in `global-agents-chat` notifies Pepe, Anton, and Katya.
- Agent replies are persisted as `agent_messages`.
- Activity rows are written to `agent_activity_log`.
- Response includes `reply_ids` and `agents_notified`.

Smoke expectation:

```json
{
  "ok": true,
  "id": "msg-...",
  "reply_ids": ["msg-..."],
  "agents_notified": ["anton"]
}
```

### POST /api/agent-chats/{chat_id}/create-task

Creates a kanban card from a chat message.

Request:

```json
{
  "title": "Task title",
  "description": "Optional override. If empty, source message text is used.",
  "message_id": "optional msg id",
  "agent_id": "anton",
  "curator_agent_id": "pepe",
  "project_id": "corp",
  "priority": "P2",
  "required_skills": ["testing", "backend_development"]
}
```

Behavior:
- Inserts a row in `kanban_cards`.
- Sets `agent_id` and `assigned_agent_id` to the assigned agent.
- Sets `curator_agent_id`, `required_skills`, `agent_discussion_id`, `next_step`.
- Links the source chat message to the new task/project.
- Inserts a `task_update` system message into the chat.
- Writes `task_created` and `task_assigned` to `agent_activity_log`.
- Updates `agents.current_task_id`, `status`, `active_since`, `last_activity_at`.
- Returns `reply_ids` containing the system chat message id.

Smoke expectation:

```json
{
  "ok": true,
  "id": "task-...",
  "source_message_id": "msg-...",
  "assigned_agent_id": "anton",
  "reply_ids": ["msg-..."]
}
```

### GET /api/agents/stalls?threshold_minutes=1

Returns active/thinking agents whose `last_activity_at` is older than the threshold.

Used by Pepe to detect stuck work and create warnings/self-healing follow-up.

### POST /api/board/send

Sends an owner message to the corporate board stream and persists quick agent replies.

Smoke expectation:

```json
{
  "ok": true,
  "stream": "corp:tasks",
  "agents_notified": ["pepe", "anton", "katya"],
  "reply_ids": ["msg-...", "msg-...", "msg-..."]
}
```

## Verification sequence

Run after backend changes:

```bash
cd /Users/admin/digital-corp-runner-v2
python3 -m py_compile dashboard/backend/main.py
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.dashboard.runner || true
curl -sS http://localhost:3000/api/health
python3 scripts/smoke_agent_chat_actions.py
```

Manual roundtrip checks:

```bash
curl -sS http://localhost:3000/api/agents/anton
curl -sS 'http://localhost:3000/api/agent-activity?agent_id=anton'
curl -sS 'http://localhost:3000/api/agents/stalls?threshold_minutes=1'
curl -sS http://localhost:3000/dashboard
```

## Known pitfalls

- FastAPI static routes such as `/api/agents/stalls` must be declared before `/api/agents/{agent_id}`.
- asyncpg can infer conflicting types when the same argument is used for varchar/text columns. Cast parameters explicitly, e.g. `$5::text`.
- Do not use chat as the factual audit log. Chat messages and `agent_activity_log` rows are both required.
- Do not claim the UI works unless the write→read chain is verified: create task → read agent current_task_id → read activity log → read kanban card.
