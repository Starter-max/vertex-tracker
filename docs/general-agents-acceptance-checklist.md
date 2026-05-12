# General Agents Acceptance Checklist

Use this checklist before declaring the General Agents layer complete.

## 0. Runtime health

- [ ] `GET /api/system` returns HTTP 200 JSON.
- [ ] Dashboard is served from the expected repo/runtime path.
- [ ] Port 3000 is owned by the intended dashboard process/launchd runner.
- [ ] PostgreSQL and Redis are reachable.
- [ ] No stale uvicorn process is serving old code.

## 1. Main dashboard `/dashboard`

- [ ] The top dashboard contains the section `Генеральные агенты`.
- [ ] Pepe is visible.
- [ ] Anton is visible.
- [ ] Katya is visible.
- [ ] Every general-agent card shows name.
- [ ] Every general-agent card shows role.
- [ ] Every general-agent card shows status.
- [ ] Every general-agent card shows current task or an explicit idle state.
- [ ] Current task is linked to a real Kanban card through `current_task_id`.
- [ ] Every card shows next step when known.
- [ ] Work duration/active-since is visible when known.
- [ ] Button/link `Открыть агента` navigates to the agent page.
- [ ] Button/link `Написать` navigates to personal agent chat.
- [ ] Button/link `Открыть задачу` navigates to Kanban task when a task exists.
- [ ] Last activity is visible.
- [ ] Block `Пепе видит зависания` renders empty and non-empty states.

## 2. Kanban linkage

- [ ] `GET /api/kanban` returns cards.
- [ ] At least one card has `effective_assigned_agent_id`.
- [ ] Assigned agent display name is present as `assigned_agent_name`.
- [ ] Assigned agent status is present as `assigned_agent_status`.
- [ ] Curator agent display name is present as `curator_agent_name` when curator exists.
- [ ] `required_skills` is an array.
- [ ] `matched_skills` is an array.
- [ ] `missing_skills` is an array.
- [ ] Kanban UI shows assigned agent badge.
- [ ] Kanban UI shows curator where applicable.
- [ ] Kanban UI shows required/matched/missing skills.
- [ ] Kanban UI shows discussion/chat link where available.
- [ ] Kanban UI shows owner-action flag when `requires_owner_action=true`.
- [ ] Kanban UI shows blocked reason when `blocked_reason` exists.

## 3. Agent list `/dashboard/agents`

- [ ] Agent list is reachable from dashboard navigation.
- [ ] All agents are shown.
- [ ] Filter by status works.
- [ ] Filter by type works.
- [ ] Filter by project works.
- [ ] Filter by skill works.
- [ ] Current task is shown per agent.
- [ ] Queue/task count is shown or explicitly marked as MVP gap.
- [ ] Last activity is shown.
- [ ] Profile link works.
- [ ] Chat link works.

## 4. Agent page `/dashboard/agents/:agentId`

- [ ] Page works for `/dashboard/agents/pepe`.
- [ ] Page works for `/dashboard/agents/anton`.
- [ ] Page works for `/dashboard/agents/katya`.
- [ ] Profile block shows avatar/name/role/type/description/status.
- [ ] Current task is shown.
- [ ] Current project is shown when known.
- [ ] Last activity is shown.
- [ ] Created-at date is shown when available.
- [ ] Mandate is shown as readable list.
- [ ] Restrictions are shown as readable list.
- [ ] Skills are shown as links to skill pages or clearly marked until skill pages exist.
- [ ] Active tasks are shown.
- [ ] Queue is shown.
- [ ] Activity journal is shown.
- [ ] Chat tab/button is available.

## 5. Global agent chat `/dashboard/agent-chat`

- [ ] Page is reachable from dashboard navigation.
- [ ] Owner messages can be sent.
- [ ] Agent messages are visible.
- [ ] Sender type/id is clear.
- [ ] Message can be linked to task.
- [ ] Message can be linked to project.
- [ ] System events are visually distinct.
- [ ] Approval requests render as separate cards.
- [ ] Decision options render when present.
- [ ] Task updates are distinct from normal messages.
- [ ] Error/self-healing messages are distinct from normal messages.
- [ ] Create-task-from-message action works or is clearly marked as MVP gap.

## 6. Personal agent chat `/dashboard/agents/:agentId/chat`

- [ ] Personal chat works for Pepe.
- [ ] Personal chat works for Anton.
- [ ] Personal chat works for Katya.
- [ ] Message composer works.
- [ ] Agent response is persisted.
- [ ] Current task context is visible.
- [ ] Create task from message works.
- [ ] Attach message to task works or is marked as MVP gap.
- [ ] Promote discussion to global chat works or is marked as MVP gap.
- [ ] Call Pepe as curator works or is marked as MVP gap.

## 7. Activity log

- [ ] `agent_activity_log` exists or current storage equivalent is documented.
- [ ] Task creation writes activity.
- [ ] Task assignment writes activity.
- [ ] Task start writes activity.
- [ ] Status change writes activity.
- [ ] Message sent writes activity where relevant.
- [ ] Approval request writes activity.
- [ ] Approval received writes activity.
- [ ] Error detected writes activity.
- [ ] Task completion writes activity.
- [ ] Activity is visible on the agent page.
- [ ] Activity can be filtered by agent/task/project or this is marked as a future gap.

## 8. Status automation and stalls

- [ ] Agent status updates when a task is assigned.
- [ ] Agent status updates when a task changes status.
- [ ] Agent status updates when an agent sends a message.
- [ ] Agent status updates when a task completes.
- [ ] Agent status updates when a task is paused.
- [ ] Agent status updates when an error occurs.
- [ ] `GET /api/agents/stalls` returns `{threshold_minutes,count,items}`.
- [ ] Stalled important tasks create a warning/event or this is marked as MVP gap.
- [ ] Pepe supervision UI shows the warning clearly.

## 9. Parallel dispatcher MVP

- [ ] `POST /api/parallel/dispatcher/tick` works.
- [ ] Default launch mode is safe `claim_only`.
- [ ] Limit is clamped.
- [ ] `POST /api/parallel/worker/tick` works.
- [ ] Worker defaults to dry-run unless CLI execution is explicitly allowed.
- [ ] Worker max items and timeout are clamped.
- [ ] Unit tests cover route presence and safety defaults.
- [ ] Real execution beyond dry-run is not claimed until implemented.

## 10. Telegram/notification delivery

- [ ] Existing `daily-cost-report` target-resolution issue is checked before adding new notification dependencies.
- [ ] New cron jobs use explicit resolved target where needed: `telegram:Kevin (dm)`.
- [ ] Delivery smoke test passes.
- [ ] Failures are logged and visible.

## 11. Documentation

- [ ] `docs/general-agents-module.md` exists.
- [ ] `docs/dashboard-agent-api.md` exists.
- [ ] `docs/general-agents-acceptance-checklist.md` exists.
- [ ] `docs/ops-dashboard-agents-runbook.md` exists.
- [ ] Parallel dispatcher docs are updated.
- [ ] Smoke scripts are documented.

## 12. Verification commands

Run before commit:

```bash
python3 -m py_compile dashboard/backend/main.py dashboard/backend/parallel_engine.py scripts/verify_kanban_integrity.py
python3 tests/test_parallel_engine_unit.py
python3 scripts/verify_kanban_integrity.py
curl -s http://localhost:3000/api/system
curl -s http://localhost:3000/api/agents/stalls
```

## 13. Git

- [ ] `git diff` reviewed.
- [ ] All intended files staged.
- [ ] Commit created on branch `dev`.
- [ ] Push attempted if remote is configured and safe.
- [ ] Three completion sounds played on macOS after important terminal work.
