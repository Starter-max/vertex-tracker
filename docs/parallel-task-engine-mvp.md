# Parallel Task Engine MVP

Дата: 2026-05-12
Runtime: /Users/admin/digital-corp-runner-v2
Dashboard: http://localhost:3000

## Что внедрено

Безопасный additive backend/data слой для параллельного выполнения задач через агентов и субагентов.

Добавлены таблицы миграцией:
- agent_instances
- work_packages
- subtasks
- owner_decisions
- parallel_events

Добавлены связи в kanban_cards:
- kanban_master_id
- parent_task_id
- work_package_id
- subagent_id
- parallel_group_id
- result_summary

Добавлен backend модуль:
- dashboard/backend/parallel_engine.py

Добавлены API endpoints:
- GET /api/parallel/work-packages
- POST /api/parallel/work-packages
- POST /api/parallel/dispatcher/tick
- GET /api/parallel/work-packages/{work_package_id}
- PATCH /api/parallel/subtasks/{subtask_id}/status
- POST /api/parallel/work-packages/{work_package_id}/events

## Поток данных

POST /api/parallel/work-packages
→ row in work_packages
→ root kanban_cards card_type=parallel_work_package
→ rows in subtasks
→ child kanban_cards card_type=parallel_subtask
→ parallel_events
→ Redis stream corp:parallel_events
→ Redis stream corp:kanban_events
→ agent_activity_log

POST /api/parallel/dispatcher/tick
→ выбирает work_packages status queued/running
→ учитывает work_package.parallel_limit
→ проверяет subtask.dependency_ids against done subtasks
→ ready subtasks переводит queued/blocked → running
→ создаёт agent_instances rows для claim-only исполнения
→ обновляет linked kanban cards и agent_activity_log
→ пишет subtask_claimed/subtask_blocked в parallel_events + Redis

Важно: launch_mode=claim_only. Dispatcher делает безопасный claim и observability, но пока не запускает тяжёлые Hermes subprocesses автоматически.

## Safety constraints

- .env не читался и не копировался.
- Удаление данных не выполнялось.
- Схема изменена только через миграцию core/migrations/008_parallel_subagents.sql.
- Изменения additive: CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.
- Реальные тяжёлые агенты пока не запускаются автоматически; это backend/data MVP и диспетчерский слой.

## Backup

Последний backup ref хранится в:
/Users/admin/.hermes/backups/parallel-subagents-latest.txt

Созданный пакет содержит config.yaml, skills archive, PostgreSQL dump, Redis stream snapshots, git status/diff snapshots.
.env deliberately not copied/read.

## Smoke test result

Первичный backend/data smoke:
- wp_20260512110311_e8a4f715
- /api/system HTTP 200
- POST /api/parallel/work-packages HTTP 200
- PATCH /api/parallel/subtasks/{id}/status HTTP 200
- GET /api/parallel/work-packages/{id} returned 4 subtasks
- GET /api/kanban?layer=operational&card_type=parallel_subtask returned generated cards
- Redis and PostgreSQL parallel_events incremented

Dispatcher smoke:
- wp_20260512111926_2ea0dad6: POST /api/parallel/dispatcher/tick claimed 2 ready subtasks, blocked 1 dependency item, launch_mode=claim_only.

Dependency regression:
- wp_20260512112041_09a4011e: first tick claimed diagnostics and blocked dependent subtasks; after PATCH first subtask → done, second tick claimed backups and kept later dependencies blocked.

## Следующий шаг

Подключить worker execution layer поверх безопасного dispatcher claim:
1. worker получает running subtasks с metadata.agent_instance_id;
2. запускает Hermes/delegate agents только в bounded mode с PATH including /Users/admin/.local/bin;
3. пишет done/failed через PATCH или напрямую через update_subtask_status;
4. собирает result_summary в work_packages;
5. эскалирует owner_decisions только при рисках: деньги, данные, секреты, irreversible/prod.

Критерий качества владельца: владелец видит один work_package, статусы subtasks, события и результат, а не управляет каждым агентом вручную.
