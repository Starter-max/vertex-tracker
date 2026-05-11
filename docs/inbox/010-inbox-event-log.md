# 010-inbox-event-log

## Что это
Журнал входящих задач владельца для master-router: фиксирует исходный текст, классификацию, риск, ход выполнения, подтверждения и итог.

## Где лежит
- SQL миграция: /Volumes/256/digital-corp/core/migrations/006_inbox_events.sql
- Таблица: public.inbox_events

## Поля (ключевые)
- raw_text, normalized_intent, intent_class
- project_id, priority, risk_level
- status (received/classified/routed/waiting_approval/in_progress/completed/failed/cancelled)
- requires_approval, approval_id
- agents_used, skills_used
- cost_usd, result_summary, error_summary
- created_at/updated_at/completed_at

## Как использовать
- На входе: писать событие со status=received.
- После классификации: status=classified/routed.
- На рискованных шагах: status=waiting_approval + approval_id.
- По завершению: status=completed или failed.

## Как смотреть последние задачи
SELECT id, created_at, intent_class, status, risk_level, left(raw_text,120) AS text
FROM inbox_events
ORDER BY id DESC
LIMIT 20;

## Как откатывать ошибочные действия
1) Не удалять записи из журнала.
2) Добавить новую запись с action/result_summary об откате.
3) Для карточек/данных делать компенсационное действие (например, вернуть статус карточки назад).
