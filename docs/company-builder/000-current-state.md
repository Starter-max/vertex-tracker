# Current State

Existing system: FastAPI dashboard on port 3000, PostgreSQL, Redis, Hermes chat sidebar, project cards, project agents, kanban UI, knowledge tab, board stream.

Database has `projects`, `agents`, `kanban_cards`, `inbox_events`. No `agent_messages` table yet; MVP workroom uses files under `/projects/{project}/workroom/`.

A09 runtime is implemented in `dashboard/backend/company_builder.py`. Master Router entrypoints are dashboard chat and `/api/inbox/route`.
