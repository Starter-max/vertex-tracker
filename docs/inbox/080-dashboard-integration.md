# 080-dashboard-integration

## Фактическое состояние
- Dashboard backend работает на localhost:3000
- Проверенные endpoints:
  - /api/system
  - /api/projects
  - /api/costs/today
  - /api/kanban
  - /api/knowledge
  - /api/agents

## Что уже есть в UI
- Обзор системы
- Проекты и расходы
- Знания
- Канбан
- Чат/board сообщения

## MVP интеграция inbox
Сделано на backend/data уровне:
- Таблица inbox_events
- Redis streams corp:inbox/corp:audit

## Что добавить следующим шагом в UI
- Блок Inbox (последние 10)
- Блок approvals (pending)
- Блок alerts (последние critical)

## Как проверить
- curl localhost:3000/api/system
- psql select из inbox_events
- redis xrevrange corp:inbox
