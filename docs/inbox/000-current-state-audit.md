# 000-current-state-audit

Дата: 2026-05-11

## 1) Что реально найдено
- Hermes установлен и работает, gateway активен через launchd.
- Telegram подключён (gateway лог: "Connected to Telegram").
- Локальные навыки digital-corp есть: cost-reporter, system-status, git-manager, mental-flow-system.
- Cron jobs: 4 активных (daily-model-picker, daily-cost-report, git-auto-commit, weekly-knowledge-refresh).
- Репозиторий: /Volumes/256/digital-corp, ветки main/dev, удалённый origin -> Starter-max/vertex-tracker.
- Docker контейнеры подняты:
  - corp-postgres (порт 5432)
  - corp-redis (порт 6379)
- Структура проекта существует: agents/, core/, core/migrations/, dashboard/, projects/.
- Миграции есть: 001..005 (до kanban_cards).
- Dashboard код найден:
  - backend: /Volumes/256/digital-corp/dashboard/backend/main.py
  - frontend: /Volumes/256/digital-corp/dashboard/frontend/index.html

## 2) Что ожидалось, но не найдено
- http://localhost:3000 сейчас недоступен (ERR_CONNECTION_REFUSED).
- psql не установлен в PATH текущей сессии.
- redis-cli не установлен в PATH текущей сессии.
- Нельзя подтвердить состояние таблиц через psql CLI без альтернативного доступа.

## 3) Что работает
- Hermes status/gateway status/skills/cron/config/auth команды отрабатывают.
- Gateway стабильно поднимается и подключается к Telegram.
- Docker показывает работающие Postgres/Redis контейнеры.
- Git доступен, история и ветки читаются.

## 4) Что не работает
- Dashboard не запущен на 3000 порту.
- Cron доставка daily-cost-report в Telegram имеет предупреждение:
  "no delivery target resolved for deliver=telegram".

## 5) Риски
- Любые изменения cron-delivery без точной привязки target могут повторно ломать доставку.
- В рабочем дереве есть незакоммиченные изменения (mental-flow-system/*), риск случайно смешать с inbox MVP.
- Backend dashboard/main.py выглядит частично повреждённым в хвосте файла (подозрительный фрагмент REDIS_URL + декоратор), нужен аккуратный запуск/проверка перед правками.

## 6) Что можно делать безопасно
- Создать документацию и план внедрения inbox в docs/inbox.
- Добавить новые skills в ~/.hermes/skills/digital-corp/* без изменения существующих.
- Проводить read-only аудит файлов/логов/cron.
- Создать отдельные SQL миграции (без применения вслепую).

## 7) Что требует подтверждения владельца
- Изменения .env.
- Любые миграции с ALTER/CREATE/UPDATE в БД (применение).
- DELETE/массовые UPDATE.
- Изменения, влияющие на внешнюю доставку или безопасность.

## 8) Текущее состояние dashboard (localhost:3000)
- Страница не открывается: соединение отклонено.
- Визуальный скрин недоступен, так как сервис не отвечает.

## 9) Найденные API dashboard (по коду backend/main.py)
- GET /api/system
- GET /api/projects
- GET /api/projects/{pid}
- POST /api/projects/{pid}/pause
- POST /api/projects/{pid}/start
- PUT /api/projects/{pid}/budget
- GET /api/costs/today
- GET /api/settings
- PUT /api/settings/{key}
- GET /api/knowledge
- POST /api/knowledge/refresh
- GET /api/kanban
- POST /api/kanban
- PATCH /api/kanban/{card_id}/status
- DELETE /api/kanban/{card_id}
- GET /api/chat/sessions
- POST /api/chat/sessions
- GET /api/chat/sessions/{sid}/messages
- DELETE /api/chat/sessions/{sid}
- POST /api/chat/send
- POST /api/chat/upload
- WebSocket /ws
- GET /api/agents
- GET /api/agents/counts
- GET /api/board/messages
- POST /api/board/send
- POST /api/agents/{agent_id}/ping

## 10) Найденные skills Hermes
- В ~/.hermes/skills/digital-corp:
  - cost-reporter
  - system-status
  - git-manager
  - mental-flow-system

## 11) Текущие cron-задачи
- daily-model-picker (active, deliver=local) — последний запуск timeout.
- daily-cost-report (active, deliver=telegram) — предупреждение по delivery target resolve.
- git-auto-commit (active, deliver=origin,telegram).
- weekly-knowledge-refresh (active, deliver=local).

## 12) Состояние Redis
- Контейнер redis запущен и слушает 6379.
- Проверка stream-ов через redis-cli невозможна в текущем PATH (redis-cli отсутствует).

## 13) Состояние PostgreSQL
- Контейнер postgres запущен и слушает 5432.
- Проверка таблиц через psql невозможна в текущем PATH (psql отсутствует).

## 14) Состояние Git
- Ветка: dev.
- Есть незакоммиченные изменения в mental-flow-system (много файлов).
- origin: https://github.com/Starter-max/vertex-tracker.git
- Последние коммиты:
  - 094d3c6 feat: add mental flow dashboard kanban
  - 37e41d4 feat: seed mental flow project in dashboard
  - 2f93ffa feat: scaffold mental flow system
  - 3fab9d8 ui: add kanban drag and drop polish
  - 2ee0265 ui: polish kanban and knowledge views

## Вывод по Этапу 0
Готово к MVP: частично.
Блокеры:
1) Dashboard не поднят на localhost:3000.
2) Нет psql/redis-cli в PATH (ограничение аудита таблиц и streams).
3) Cron delivery в Telegram уже имеет известную проблему target resolve.

Без устранения блокеров можно продолжать только с документацией и безопасной подготовкой (skills/план/архитектура), но не подтверждать full-ready MVP end-to-end.
