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
- POST /api/parallel/worker/tick
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

Важно: launch_mode=claim_only. Dispatcher делает безопасный claim и observability, но не запускает тяжёлые Hermes subprocesses автоматически.

POST /api/parallel/worker/tick
→ выбирает уже claimed subtasks со status=running
→ ограничивает fan-out через max_items 1..5 и timeout_seconds 15..600
→ safe default: allow_cli=false, mode=dry_run, Hermes CLI не запускается
→ dry_run проверяет тот же durable write path: subtask done, kanban result_summary, work_package aggregate status, parallel_events + Redis
→ explicit execution: allow_cli=true запускает /Users/admin/.local/bin/hermes chat -q с PATH including /Users/admin/.local/bin
→ если worker выводит NEEDS_OWNER_DECISION, создаётся owner_decisions row и subtask переходит в needs_review
→ при ошибке subtask переходит в failed, пишется subtask_worker_failed event

## Safety constraints

- .env не читался и не копировался.
- Удаление данных не выполнялось.
- Схема изменена только через миграцию core/migrations/008_parallel_subagents.sql.
- Изменения additive: CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.
- Реальные тяжёлые агенты не запускаются автоматически: dispatcher только claim-only, worker по умолчанию dry_run.
- Реальный Hermes CLI worker доступен только при explicit allow_cli=true, max_items cap и timeout cap.
- Системные служебные записи используют virtual agent `parallel-engine`, чтобы не ломать FK/NOT NULL constraints в agents/agent_activity_log.

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

Bounded worker dry-run smoke:
- wp_20260512132611_aa2445dc: dispatcher claimed step 1 and blocked step 2; worker/tick dry_run completed step 1; dispatcher claimed step 2 after dependency done; worker/tick dry_run completed step 2.
- final_status=done; both subtasks status=done; result_summary present; events included work_package_created, subtask_claimed, subtask_blocked, subtask_status, subtask_executed.
- This confirms backend/data execution path only. It does not prove real Hermes subprocess execution because allow_cli=false was used deliberately for safety.

## Следующий шаг

MVP-дорожка закрыта до controlled real execution:
1. worker metrics добавлены в ответ `/api/parallel/worker/tick` и событие `worker_tick_summary`: executed/skipped/failed/duration/timeouts/guardrail_blocked;
2. guardrails для `allow_cli=true` добавлены: обязательный `diagnostic_ref`, `backup_ref` при `requires_backup=true`, блокировка risky metadata flags без owner decision;
3. добавлен безопасный runner `scripts/parallel_worker_tick.py` для ручного/launchd/cron tick; по умолчанию `ALLOW_PARALLEL_WORKER_CLI=false`, `max_items=1`;
4. controlled allow_cli=true smoke выполнен на read-only подзадаче с timeout и PATH `/Users/admin/.local/bin`;
5. `work_packages.result_summary` собирается из subtasks и даёт owner-facing report;
6. `owner_decisions` создаются при `NEEDS_OWNER_DECISION` и при guardrail block.

Последний controlled smoke:
- guardrail block: `wp_20260512140259_21ee60be` → status=`needs_review`, `guardrail_blocked_count=1`;
- real CLI read-only: `wp_20260512140259_334ae6ad` → status=`done`, mode=`hermes_cli`, executed=1, failed=0, timeout=0, duration≈4.23s;
- result_summary: `BOUNDED_WORKER_OK read-only smoke completed.`

Осталось для production-hardening, не для MVP:
1. включать `scripts/parallel_worker_tick.py` в launchd только после выбора политики: dry-run automation или allow_cli automation;
2. добавить UI-блок для worker metrics на dashboard;
3. расширить CI на миграции + API smoke;
4. добавить per-agent budgets/rate limits перед массовым allow_cli fan-out.

Критерий качества владельца: владелец видит один work_package, статусы subtasks, события и результат, а не управляет каждым агентом вручную.
