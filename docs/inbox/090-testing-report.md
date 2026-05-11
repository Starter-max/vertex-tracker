# 090-testing-report

Дата: 2026-05-11

## Сводка
MVP реализован и документирован. Закрыты аудит, план, журнал inbox, kanban-layer, redis-bus, approval-flow, delegation, ops docs и daily morning brief cron.

## Пройдено
1) Аудит среды + dashboard/local services.
2) Dashboard API: /api/system, /api/projects, /api/costs/today -> PASS.
3) PostgreSQL schema проверена -> PASS.
4) Redis streams/read-write (corp:inbox, corp:audit) -> PASS.
5) Миграция 006_inbox_events.sql применена -> PASS.
6) inbox_events read/write -> PASS.
7) Risk event (waiting_approval) -> PASS.
8) Morning brief daily cron создан:
   - job_id: 2cc5d9b2b1fb
   - schedule: 5 9 * * *
   - deliver: telegram:Kevin (dm)

## Частично / ограничения
- Исторический job daily-cost-report с deliver=telegram остаётся как пример некорректного target-resolve.
- Отдельный тестовый one-shot job был удалён/недоступен в листинге к моменту повторного форс-запуска; в качестве устойчивого решения создан постоянный morning-brief job с явным target.
- Полный live E2E прогон всех 20 сценариев через Telegram UI не завершён автоматически в рамках этой сессии; data-plane и ключевые сценарии закрыты.

## Результат
Инфраструктурно и документально inbox-контур готов к эксплуатации MVP.
Для полного done по acceptance: провести финальный ручной live Telegram smoke (команды /с /б /к /п /инбокс /риск /д) и отметить PASS в этом отчёте.
