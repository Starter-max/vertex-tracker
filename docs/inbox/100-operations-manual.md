# 100-operations-manual

## Назначение
Операционное руководство по inbox-контру Digital Corp.

## Основной контур
1) Входящее сообщение владельца -> master-router
2) Классификация intent
3) Безопасное действие или approval A/B/C
4) Лог в inbox_events
5) События в Redis (corp:inbox/corp:audit/...)
6) Короткий ответ владельцу

## Проверка здоровья
- Hermes: `hermes status --all`
- Gateway: `hermes gateway status`
- Dashboard API: `curl http://localhost:3000/api/system`
- Postgres: `docker exec corp-postgres psql -U corp -d digitalcorp -c "select now();"`
- Redis: `docker exec corp-redis redis-cli ping`

## Частые операции
- Последние inbox события:
  `docker exec corp-postgres psql -U corp -d digitalcorp -c "select id, intent_class, status, created_at from inbox_events order by id desc limit 20;"`
- Последние Redis inbox события:
  `docker exec corp-redis redis-cli XREVRANGE corp:inbox + - COUNT 20`

## Approval
- Рискованные действия не выполняются автоматически.
- Формат подтверждения: A/B/C.
- Хранение: inbox_events.requires_approval + approval_id, Redis corp:approvals.

## Cron morning brief
- Сначала тест доставки в Telegram target.
- Только после успеха включать daily 09:05.

## Безопасность
- Не выводить секреты.
- Не менять .env без подтверждения владельца.
- Не делать массовые UPDATE/DELETE без явного подтверждения.
