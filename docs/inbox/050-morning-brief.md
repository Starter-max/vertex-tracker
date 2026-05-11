# 050-morning-brief

## Что это
Ежедневный краткий бриф владельцу в Telegram в 09:05 (локальная TZ).

## Источники
- system-status
- costs/cost-reporter
- kanban_cards
- agents/projects
- Redis: corp:alerts, corp:approvals

## Формат
5-7 пунктов максимум: система, расходы, активные проекты/агенты, внимание, в работе, блокировано, нужно решение.

## Проверка доставки
- Исторический баг: `deliver=telegram` без явного target мог давать `target resolved failed`.
- Исправление: использовать явный target `telegram:Kevin (dm)`.
- Тестовый job: `telegram-delivery-test-inbox` (job_id=f079df80078c), форс-запуск выполнен.

## Cron
- Ежедневный job создан: `morning-brief-inbox-0905`
- Schedule: `5 9 * * *`
- Deliver: `telegram:Kevin (dm)`

## Ручной запуск
- /д, /день (через router)

## Отключение
- pause/remove cron job через `hermes cron` или cronjob tool.
