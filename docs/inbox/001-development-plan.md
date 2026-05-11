# 001-development-plan

Дата: 2026-05-11

## Цель MVP
Собрать единый мультиагентный inbox-контур для владельца (CEO-mode): короткий вход в Telegram, автоматическая маршрутизация, безопасные действия, журнал событий, базовая интеграция с канбаном/Redis/dashboard.

## Базовые принципы
- Никаких галлюцинаций: только подтверждённые факты.
- Безопасность прежде всего: рискованные действия только через approval.
- Минимум нагрузки на владельца: короткие ответы, 1 уточняющий вопрос максимум.
- Не ломать текущие рабочие контуры и не трогать секреты.

## Этапы реализации

### Этап 1. Подготовка
1. Зафиксировать блокеры из 000-current-state-audit.md.
2. Поднять dashboard локально и проверить /api/system, /api/projects, /api/costs/today.
3. Проверить доступ к PostgreSQL/Redis через docker exec (если psql/redis-cli вне PATH).

### Этап 2. master-router MVP
1. Создать skill: ~/.hermes/skills/digital-corp/master-router/SKILL.md
2. Реализовать классификацию классов intent (status/cost/kanban/git/knowledge/complex/unknown).
3. В unknown — ровно один вопрос с вариантами.
4. Формат ответа: короткий итог + next step.

### Этап 3. quick commands
1. Выяснить фактический путь регистрации команд (CLI/gateway mapping).
2. Добавить/проверить: /д /с /б /к /г /з /п /инбокс /алерты /долги /стоп /риск.
3. Документировать, где и как они регистрируются.

### Этап 4. kanban-aggregator
1. Создать безопасный слой (skill или встроенно в master-router).
2. Реализовать read/create/move/priority/stale checks.
3. Любой update только после SELECT кандидатов.
4. Для >1 кандидата — запрос выбора.

### Этап 5. inbox-event-log
1. Проверить, хватает ли chat_sessions/chat_messages.
2. Если нет — подготовить миграцию 006_inbox_events.sql (без слепого применения).
3. Прописать статусы/risk/requires_approval/cost/result/error.

### Этап 6. Redis event bus
1. Писать события в corp:inbox, corp:tasks, corp:results, corp:audit, corp:approvals.
2. Форматы полей — в 040-redis-event-bus.md.
3. Stream создавать лениво через XADD.

### Этап 7. approval-flow
1. Определить список рискованных действий.
2. Формат A/B/C подтверждения.
3. Связка с approval_id и timeout.

### Этап 8. morning-brief
1. Сначала устранить проблему cron delivery target resolve.
2. Прогон тестового one-shot cron в Telegram.
3. Затем daily 09:05 (локальная TZ).

### Этап 9. dashboard integration
1. Проверить текущее состояние UI/API после запуска.
2. Если быстро и безопасно — добавить inbox-блок (последние 10, approvals, alerts).
3. Если это большой объём — оформить как kanban-задачу и next steps.

### Этап 10. тесты и коммит
1. Пройти 20 тестовых сценариев из ТЗ.
2. Заполнить 090-testing-report.md.
3. Проверить отсутствие секретов/.env в diff.
4. Коммит: feat: add digital corp inbox router

## Что входит в MVP сейчас
- Аудит, план, базовый master-router, quick commands, kanban-aggregator, event-log, Redis-integration, approval-flow, ручной morning brief, документация.

## Что может быть отложено
- Полноценный inbox UI в dashboard, если потребуется глубокая переделка фронта/бэка.
- Расширенный consilium mode с несколькими агентами, если нужно больше времени на QA.

## Критерий перехода к следующим этапам
- Dashboard поднимается локально.
- Подтверждён доступ к таблицам/streams.
- Cron delivery в Telegram либо исправлен, либо явно зафиксирован как блокер с обходом.
