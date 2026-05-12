-- General Agents module: CEO-visible operating layer for Digital Corp.
-- Adds rich agent metadata, kanban links, agent chats and factual activity log.

ALTER TABLE agents
ADD COLUMN IF NOT EXISTS slug TEXT,
ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'project_agent',
ADD COLUMN IF NOT EXISTS short_description TEXT,
ADD COLUMN IF NOT EXISTS full_description TEXT,
ADD COLUMN IF NOT EXISTS avatar_url TEXT,
ADD COLUMN IF NOT EXISTS current_task_id TEXT,
ADD COLUMN IF NOT EXISTS next_task_id TEXT,
ADD COLUMN IF NOT EXISTS active_since TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS mandate JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS restrictions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE agents SET slug = COALESCE(slug, id) WHERE slug IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_slug ON agents(slug);
CREATE INDEX IF NOT EXISTS idx_agents_type_status ON agents(type, status);
CREATE INDEX IF NOT EXISTS idx_agents_current_task ON agents(current_task_id);

ALTER TABLE kanban_cards
ADD COLUMN IF NOT EXISTS assigned_agent_id TEXT,
ADD COLUMN IF NOT EXISTS curator_agent_id TEXT,
ADD COLUMN IF NOT EXISTS required_skills JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS next_step TEXT,
ADD COLUMN IF NOT EXISTS agent_discussion_id TEXT,
ADD COLUMN IF NOT EXISTS requires_owner_action BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS blocked_reason TEXT,
ADD COLUMN IF NOT EXISTS last_agent_activity_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS agent_status_snapshot JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_kanban_assigned_agent ON kanban_cards(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_kanban_curator_agent ON kanban_cards(curator_agent_id);

CREATE TABLE IF NOT EXISTS agent_chats (
    id TEXT PRIMARY KEY,
    chat_type TEXT NOT NULL,
    title TEXT NOT NULL,
    agent_id TEXT,
    task_id TEXT,
    project_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES agent_chats(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    text TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'message',
    task_id TEXT,
    project_id TEXT,
    parent_message_id TEXT,
    visibility TEXT DEFAULT 'owner_agents',
    requires_owner_action BOOLEAN DEFAULT FALSE,
    decision_options JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_chat_time ON agent_messages(chat_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_messages_task ON agent_messages(task_id);

CREATE TABLE IF NOT EXISTS agent_activity_log (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    task_id TEXT,
    project_id TEXT,
    text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_activity_agent_time ON agent_activity_log(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activity_task_time ON agent_activity_log(task_id, created_at DESC);

INSERT INTO projects(id,name,type,status,budget_daily,budget_monthly)
VALUES ('corp','Digital Corp Core','admin','active',5.00,150.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO kanban_cards (
    id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,
    assigned_agent_id,curator_agent_id,required_skills,started_at,next_step,agent_discussion_id,
    requires_owner_action,last_agent_activity_at,agent_status_snapshot
) VALUES (
    'task-dashboard-general-agents',
    'Разработать блок генеральных агентов',
    'Верхний слой цифровой корпорации: Пепе, Антон, Катя, связи с канбаном, скилами, чатами и журналом активности.',
    'feature','strategic','corp','anton','in_progress','P0',ARRAY['dashboard','agents','kanban'],
    'anton','pepe','["frontend_development","backend_development","dashboard_design","agent_state_modeling"]'::jsonb,
    NOW() - INTERVAL '45 minutes','Проверить dashboard после внедрения блока GeneralAgentsOverview','chat-task-dashboard-general-agents',
    FALSE,NOW() - INTERVAL '5 minutes','{"agent":"anton","status":"thinking"}'::jsonb
) ON CONFLICT (id) DO UPDATE SET
    assigned_agent_id=EXCLUDED.assigned_agent_id,
    curator_agent_id=EXCLUDED.curator_agent_id,
    required_skills=EXCLUDED.required_skills,
    next_step=EXCLUDED.next_step,
    agent_discussion_id=EXCLUDED.agent_discussion_id,
    last_agent_activity_at=EXCLUDED.last_agent_activity_at,
    agent_status_snapshot=EXCLUDED.agent_status_snapshot;

INSERT INTO agents (
    id,project_id,name,role,status,slug,type,short_description,full_description,avatar_url,
    current_task_id,next_task_id,active_since,last_activity_at,skills,mandate,restrictions,metadata,updated_at
) VALUES
('pepe','corp','Пепе','Управляющий Hermes','active','pepe','general_agent','Координирует всю систему, распределяет задачи и следит за движением корпорации.','Пепе — генеральный управляющий цифровой корпорации. Он отвечает за координацию агентов, распределение задач, контроль зависаний, сбор общей картины и коммуникацию с владельцем.','/avatars/agents/pepe.png','task-dashboard-general-agents',NULL,NOW() - INTERVAL '45 minutes',NOW() - INTERVAL '3 minutes','["system_coordination","task_routing","kanban_management","agent_supervision","owner_communication","risk_escalation"]'::jsonb,'["Принимать задачи от владельца","Классифицировать задачи","Назначать задачи агентам","Связывать задачи с канбаном","Контролировать сроки и зависания","Эскалировать владельцу только важное"]'::jsonb,'["Не удалять данные без подтверждения владельца","Не менять критичные настройки без подтверждения","Не тратить деньги сверх лимита без подтверждения","Не запускать рискованные внешние действия без подтверждения"]'::jsonb,'{"next_step":"Сверить связи агент → задача → чат → журнал","queue_count":2}'::jsonb,NOW()),
('anton','corp','Антон','ИТ-компания корпорации','thinking','anton','general_agent_company','Решает разработку, архитектуру, интеграции, базы данных, тестирование и безопасность.','Антон — внутренняя ИТ-компания цифровой корпорации. Решает вопросы разработки, архитектуры, интерфейсов, баз данных, безопасности, тестирования и развертывания.','/avatars/agents/anton.png','task-dashboard-general-agents','task-agent-profile-page',NOW() - INTERVAL '45 minutes',NOW() - INTERVAL '5 minutes','["architecture","frontend_development","backend_development","database_design","testing","security","deployment","technical_documentation"]'::jsonb,'["Проектировать техническую архитектуру","Разрабатывать интерфейсы и бэкенд","Работать с базами данных через миграции","Исправлять ошибки и анализировать логи","Готовить техническую документацию и безопасный запуск"]'::jsonb,'["Не менять схему базы данных без миграции","Не трогать .env и секреты без явного разрешения","Не выкатывать изменения в продакшен без подтверждения","Не удалять данные","Не менять существующие скилы без версии"]'::jsonb,'{"next_step":"Завершить frontend и smoke-test","queue_count":3}'::jsonb,NOW()),
('katya','corp','Катя','HR-компания агентов','waiting','katya','general_agent_company','Подбирает агентов, описывает роли, собирает команды, отвечает за скилы и встройку.','Катя отвечает за подбор, описание, встройку и развитие агентов. Она формирует команды, описывает роли, мандаты, ограничения, скилы и проверяет, хватает ли системе нужных компетенций.','/avatars/agents/katya.png',NULL,NULL,NULL,NOW() - INTERVAL '20 minutes','["agent_recruiting","role_design","skill_mapping","team_assembly","agent_onboarding","mandate_design"]'::jsonb,'["Описывать роли агентов","Формировать профили агентов","Подбирать недостающих агентов","Связывать агентов со скилами","Выявлять нехватку компетенций"]'::jsonb,'["Не создавать новых агентов без фиксации мандата","Не назначать агента без понятной зоны ответственности","Не смешивать личные, рабочие и сторонние проекты","Не менять права агентов без согласования"]'::jsonb,'{"next_step":"Проверить, хватает ли Антону скилов для задачи","queue_count":1}'::jsonb,NOW())
ON CONFLICT (id) DO UPDATE SET
    project_id=EXCLUDED.project_id,
    name=EXCLUDED.name,
    role=EXCLUDED.role,
    status=EXCLUDED.status,
    slug=EXCLUDED.slug,
    type=EXCLUDED.type,
    short_description=EXCLUDED.short_description,
    full_description=EXCLUDED.full_description,
    avatar_url=EXCLUDED.avatar_url,
    current_task_id=EXCLUDED.current_task_id,
    next_task_id=EXCLUDED.next_task_id,
    active_since=EXCLUDED.active_since,
    last_activity_at=EXCLUDED.last_activity_at,
    skills=EXCLUDED.skills,
    mandate=EXCLUDED.mandate,
    restrictions=EXCLUDED.restrictions,
    metadata=EXCLUDED.metadata,
    updated_at=NOW();

INSERT INTO agent_chats(id,chat_type,title,agent_id,task_id,project_id) VALUES
('global-agents-chat','global','Общий чат агентов',NULL,NULL,'corp'),
('chat-agent-pepe','direct','Личный чат: Пепе','pepe',NULL,'corp'),
('chat-agent-anton','direct','Личный чат: Антон','anton',NULL,'corp'),
('chat-agent-katya','direct','Личный чат: Катя','katya',NULL,'corp'),
('chat-task-dashboard-general-agents','task','Обсуждение задачи: блок генеральных агентов',NULL,'task-dashboard-general-agents','corp')
ON CONFLICT (id) DO NOTHING;

INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id,created_at) VALUES
('msg-general-agents-seed-1','global-agents-chat','agent','pepe','Пепе назначил Антону задачу по разработке блока генеральных агентов. Катя проверяет мандаты и скилы.','coordination','task-dashboard-general-agents','corp',NOW() - INTERVAL '40 minutes'),
('msg-general-agents-seed-2','chat-task-dashboard-general-agents','agent','anton','Принял задачу. Работаю через миграцию, API, dashboard-компоненты и smoke-test.','task_update','task-dashboard-general-agents','corp',NOW() - INTERVAL '35 minutes')
ON CONFLICT (id) DO NOTHING;

INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text,created_at) VALUES
('log-general-agents-start','anton','task_started','task-dashboard-general-agents','corp','Антон начал задачу по блоку генеральных агентов.',NOW() - INTERVAL '45 minutes'),
('log-general-agents-assign','pepe','task_assigned','task-dashboard-general-agents','corp','Пепе назначил Антона исполнителем и себя куратором.',NOW() - INTERVAL '44 minutes'),
('log-general-agents-skill-check','katya','status_changed','task-dashboard-general-agents','corp','Катя проверяет связку ролей, скилов и мандатов.',NOW() - INTERVAL '20 minutes')
ON CONFLICT (id) DO NOTHING;
