# General Agents Module

## Purpose

The General Agents module is the top management layer of the Digital Corp dashboard.
It exists to show the owner who is responsible for work, what each agent is doing,
what the next step is, where the related Kanban card lives, which skills are needed,
and where the operational discussion/activity trail can be inspected.

Product principle: the owner is the CEO/customer, not an operator. Every UI and API
change should reduce owner screen time and avoid forcing the owner to debug internal
technical details.

## Current MVP scope

Implemented MVP surfaces:

- Top dashboard block: `GeneralAgentsOverview` / "Генеральные агенты".
- Starter general agents: `pepe`, `anton`, `katya`.
- Agent list and agent detail/chat navigation markers in the dashboard frontend.
- Kanban cards enriched with assigned agent, curator, matched skills and missing skills.
- Stalled-agent endpoint for Pepe supervision: `GET /api/agents/stalls`.
- Agent chat/task integration routes used by the dashboard board and personal chats.
- Parallel dispatcher MVP in safe modes: dispatcher `claim_only`, worker `dry_run` by default.

## Core concepts

### Agent

An agent is a working subject in the system, not a decorative card.

Important fields:

- `id`
- `name`
- `slug`
- `type`
- `role`
- `short_description`
- `full_description`
- `status`
- `current_task_id`
- `next_task_id`
- `active_since`
- `last_activity_at`
- `skills`
- `mandate`
- `restrictions`

Starter agents:

- `pepe`: managing/coordination layer.
- `anton`: internal IT/development company.
- `katya`: HR/agent-role/skill-mapping company.

### Kanban card linkage

Kanban cards must be linked to agents through data fields, not text labels.

Important fields:

- `assigned_agent_id`
- `curator_agent_id`
- `required_skills`
- `started_at`
- `next_step`
- `agent_discussion_id`
- `requires_owner_action`
- `blocked_reason`
- `last_agent_activity_at`

The live `/api/kanban` read model adds:

- `effective_assigned_agent_id`
- `assigned_agent_name`
- `assigned_agent_status`
- `assigned_agent_last_activity_at`
- `curator_agent_name`
- `matched_skills`
- `missing_skills`

Current MVP computes skill matching from `agents.skills` JSONB so the live system does
not depend on a missing `agent_skills` table. A future migration can normalize skills
without breaking the read model.

### Skill matching

`required_skills` belongs to the task.
`skills` belongs to the agent.

The dashboard must show:

- skills required by the task;
- skills the assigned agent has;
- skills missing from the assigned agent.

If missing skills exist, Katya should eventually propose a better agent, a new subagent,
or a skill improvement task for Anton.

### Chat vs activity log

Chat and activity log are intentionally separate.

Chat is communication:

- owner messages;
- agent messages;
- agent-to-agent coordination;
- approval requests/responses;
- task/project discussion.

Activity log is factual history:

- task created;
- task assigned;
- task started;
- status changed;
- message sent;
- approval requested/received;
- task blocked/completed;
- error detected;
- owner escalated.

Do not collapse the activity log into chat messages only.

## UI pages

### `/dashboard`

Top block:

- section title: `Генеральные агенты`;
- cards for Pepe, Anton and Katya;
- status, current task, next step, work timer/active-since where available;
- links to agent profile, direct chat and Kanban task;
- stalled-agent supervision block: `Пепе видит зависания`.

### `/dashboard/agents`

Agent overview:

- list of agents;
- filters by status, type, project and skill;
- current task per agent;
- last activity;
- profile/chat actions.

### `/dashboard/agents/:agentId`

Agent profile target structure:

- profile summary;
- mandate;
- restrictions;
- skills;
- active tasks;
- queue;
- activity journal;
- chat entry point.

### `/dashboard/agent-chat`

Global agent chat target structure:

- owner and agents in one working communication log;
- messages linked to task/project where applicable;
- system events visually distinct from normal messages;
- approval request cards with decision options;
- create-task-from-message action.

### `/dashboard/agents/:agentId/chat`

Personal agent chat target structure:

- write to a specific agent;
- create a Kanban task from the discussion;
- attach a message to an existing task;
- promote a fragment to global chat;
- call Pepe as curator;
- show current task context.

## Backend endpoints

See `docs/dashboard-agent-api.md` for the API reference.

Critical read endpoints:

- `GET /api/agents`
- `GET /api/kanban`
- `GET /api/agents/stalls`

Critical write/action endpoints:

- `POST /api/board/send`
- `POST /api/parallel/dispatcher/tick`
- `POST /api/parallel/worker/tick`

## Acceptance gates

A feature is not complete if it is only UI.
For every General Agents feature, prove the chain:

1. UI has a visible navigation path.
2. API returns real data.
3. Data links agent -> task and task -> agent.
4. JSON fields are arrays/objects, not serialized strings.
5. Write actions are proven by read-after-write checks.
6. Important actions produce activity rows or clearly documented MVP gaps.
7. Smoke tests pass.

## Known MVP gaps

Remaining beyond the current MVP:

- normalized `agent_skills` / skill entity table and skill detail pages;
- fully interactive global chat UX with all message types;
- fully interactive personal chat UX with create-task/promote/call-curator actions;
- complete activity timeline on agent pages;
- automatic status updates for all task/message/error transitions;
- scheduled stalled-agent self-healing/warning creation;
- real parallel worker execution beyond dry-run/claim-only safety modes;
- production performance metrics for the parallel engine.

## Verification commands

From the repo root:

```bash
python3 -m py_compile dashboard/backend/main.py dashboard/backend/parallel_engine.py scripts/verify_kanban_integrity.py
python3 tests/test_parallel_engine_unit.py
python3 scripts/verify_kanban_integrity.py
curl -s http://localhost:3000/api/system
curl -s http://localhost:3000/api/agents/stalls
```

Expected smoke result:

- `OK kanban_integrity`
- `/api/system` returns JSON;
- `/api/agents` returns agents;
- `/api/kanban` returns Kanban cards with agent enrichment;
- `/api/agents/stalls` returns `{count, items, threshold_minutes}`.
