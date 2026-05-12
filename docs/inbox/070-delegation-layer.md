# Delegation Layer

## Roles

- A01 Cost Controller — costs and anomalies
- A02 Security Monitor — secrets/access/security
- A03 Risk Manager — risk review
- A04 Dispatcher / Hermes — routing and Telegram
- A05 Quality Auditor — result audit
- A06 Research — fresh external knowledge
- A07 Dev Assistant — code/tests/refactor
- A08 Dashboard — UI/API/dashboard

## Current transport

- Hermes `delegate_task` exists in the agent environment.
- Backend can enqueue tasks via `POST /api/board/send` into Redis `corp:tasks` and `agent_events`.

## Rule

Use direct safe action for simple queries. Use delegation or Redis tasks for complex, risky, or multi-agent work.

## Consilium mode

Use when there is high risk or architecture uncertainty. Return:
- Decision
- Risks
- Cost
- Do now
- Defer
- Confirmation needed: yes/no
