# 040-redis-event-bus

## Streams
- corp:inbox
- corp:tasks
- corp:results
- corp:alerts
- corp:costs
- corp:health
- corp:audit
- corp:approvals

## Формат task event
- task_id, source, source_message_id, owner_id, project_id
- agent, intent, message, priority, risk_level
- requires_approval, created_at, deadline, correlation_id

## Формат result event
- result_id, task_id, agent, status, summary, details_path, cost_usd, created_at

## Формат audit event
- audit_id, actor, action, target, risk_level, before_summary, after_summary, created_at

## Примеры redis-cli
- XADD corp:inbox * source telegram owner_id 89434175 message "статус"
- XREVRANGE corp:inbox + - COUNT 10
- XINFO STREAM corp:tasks

## Отладка
- Если stream не существует: это нормально до первого XADD.
- Проверять контейнер: docker exec corp-redis redis-cli ...
