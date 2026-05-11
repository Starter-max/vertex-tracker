# 120-next-steps

1) Завершить связку master-router с Telegram входом на runtime уровне.
2) Добавить backend endpoints для inbox:
   - GET /api/inbox/events
   - GET /api/inbox/approvals
   - POST /api/inbox/approvals/{id}/decision
3) Добавить Inbox блок в dashboard UI:
   - последние 10 сообщений
   - pending approvals
   - critical alerts
4) Доделать full e2e тест сценариев 1..20 из ТЗ через Telegram.
5) Зафиксировать cron morning brief 09:05 только после стабильного delivery теста.
6) Вынести master-router/kanban-aggregator в исполняемый модуль (Python service) с параметризованными SQL.
7) Добавить unit/integration tests для классификатора intent и approval transitions.
