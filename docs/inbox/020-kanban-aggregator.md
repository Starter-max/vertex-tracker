# 020-kanban-aggregator

## Что это
Безопасный слой работы с kanban_cards для inbox-router.

## Где лежит
- Skill: /Users/admin/.hermes/skills/digital-corp/kanban-aggregator/SKILL.md
- Таблица: public.kanban_cards

## Операции
1. Показать in_progress
2. Показать blocked/frozen
3. Показать strategic layer
4. Добавить задачу (status=planned, priority=P2 default)
5. Переместить задачу (SELECT кандидатов -> UPDATE 1)
6. Поставить приоритет P0/P1/P2/P3
7. Найти зависшие

## SQL (безопасные шаблоны)
- View in_progress:
  SELECT * FROM kanban_cards WHERE status='in_progress' ORDER BY priority, moved_at;
- View blocked/frozen:
  SELECT * FROM kanban_cards WHERE status IN ('blocked','frozen') ORDER BY moved_at;
- Create:
  INSERT INTO kanban_cards (id,title,description,card_type,layer,project_id,status,priority)
  VALUES ($1,$2,$3,$4,$5,$6,$7,$8);
- Candidate select before move:
  SELECT id,title,status FROM kanban_cards WHERE lower(title) LIKE lower($1) ORDER BY moved_at DESC;
- Move one:
  UPDATE kanban_cards SET status=$1, moved_at=NOW(), updated_at=NOW() WHERE id=$2;

## Правила безопасности
- Никаких массовых UPDATE/DELETE.
- При >1 кандидате обязательно уточнение.
- DELETE задач только через approval flow.

## Приоритеты
- "срочно" => P0
- "важно" => P1
- default => P2
- "потом" => P3

## Зависшие
- in_progress > 3 дней
- blocked/frozen > 7 дней
- planned и due_date < today
