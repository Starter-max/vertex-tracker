# 030-quick-commands

## Список команд (MVP)
- /д, /день -> morning brief сейчас
- /с, /статус -> system-status
- /б, /бюджет -> cost-reporter
- /к, /канбан -> in_progress + blocked
- /г, /гит -> git status + log -5
- /з, /знания -> knowledge_items status != ok
- /п <текст> -> добавить задачу в kanban
- /инбокс -> последние 10 inbox_events
- /алерты -> последние критичные алерты
- /долги -> зависшие задачи
- /стоп -> безопасная остановка текущей операции
- /риск <текст> -> быстрая оценка риска

## Где зарегистрированы
- Telegram команды формируются gateway автоматически из slash registry Hermes.
- Для кастомного поведения используется master-router intent mapping.

## Как добавить новую
1) Добавить intent в master-router.
2) Добавить обработчик (safe action / approval).
3) Добавить запись в docs + тест сценария.

## Как тестировать
- Отправлять команды в Telegram владельца.
- Проверять:
  - ответ пользователю
  - запись в inbox_events
  - запись в Redis stream (corp:inbox/audit при необходимости)
