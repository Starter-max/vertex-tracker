# 090 Testing Report — A09 Company Builder

Дата: 2026-05-12

## Проверки

### Backend compile

Команда:

```bash
python3.12 -m py_compile main.py company_builder.py
```

Результат: PASS.

### PostgreSQL

Проверено asyncpg-подключение к PostgreSQL с переменными из `/Volumes/256/digital-corp/core/.env`.

Результат: PASS (`SELECT 1`).

### Dashboard health

Endpoint:

```text
GET http://localhost:3000/api/system
```

Результат: PASS, HTTP 200. Контейнеры `corp-postgres` и `corp-redis` в статусе up.

### Master Router → A09

Endpoint:

```text
POST /api/inbox/route
```

Тестовое сообщение:

```text
Создай компанию под разработку тестового проекта P_TEST
```

Результат: PASS.

Возвращено:

- `ok: true`
- `intent_class: PROJECT_COMPANY_REQUEST`
- `status: done`
- `project_id: p_test`

### Project company files

Создана структура:

```text
/Volumes/256/digital-corp/projects/p_test-test-agent-company/
```

Проверены ключевые файлы:

- `project.json`
- `README.md`
- `company/company-charter.md`
- `company/org-structure.md`
- `company/agents.md`
- `company/skills.md`
- `company/agents/*.md`
- `kanban/initial-plan.md`
- `workroom/messages/2026-05-12.md`
- `workroom/decisions/decision-001-project-start.md`
- `workroom/summaries/initial-kickoff.md`

Результат: PASS.

### Workroom API

Endpoints:

```text
GET /api/project-companies/p_test/workroom?kind=chat
GET /api/project-companies/p_test/workroom?kind=decisions
```

Результат: PASS. Возвращаются сообщения kickoff и Decision 001.

### Agents API

Endpoint:

```text
GET /api/agents?project_id=p_test
```

Результат: PASS. Возвращаются агенты проектной компании.

### Kanban API

Endpoint:

```text
GET /api/kanban?layer=operational
```

Результат: PASS. Карточки `p_test-a09-*` присутствуют.

### Dashboard MVP

Во frontend добавлен блок `Agent Workroom` в карточку проекта:

- чат;
- решения;
- споры;
- итоги.

Использует endpoint:

```text
/api/project-companies/{pid}/workroom?kind={chat|decisions|debates|summaries}
```

HTML parser check: PASS.

## Известные ограничения

- Workroom MVP файловый. PostgreSQL-таблица `agent_messages` пока не обязательна.
- Dashboard показывает workroom через файл/API, не через отдельную SQL-модель.
- Удаление проектной компании намеренно не реализовано без подтверждения владельца.

## Итог

A09 Company Builder прошёл smoke-тест создания тестовой проектной компании P_TEST: проект, агенты, мандаты, канбан, workroom, первое обсуждение и первое решение созданы и доступны через API/dashboard.
