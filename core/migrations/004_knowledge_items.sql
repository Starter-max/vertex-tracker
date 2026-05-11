CREATE TABLE IF NOT EXISTS knowledge_items (
    id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50),
    name VARCHAR(100),
    description TEXT,
    current_version VARCHAR(100),
    latest_version VARCHAR(100),
    freshness_score INT DEFAULT 50,
    status VARCHAR(20) DEFAULT 'unknown',
    last_checked TIMESTAMPTZ,
    check_url TEXT,
    alternatives JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO knowledge_items (id, category, name, description, current_version, check_url, freshness_score, status) VALUES
('llm.claude-sonnet', 'llm', 'Claude Sonnet', 'Основная модель для агентов', 'claude-sonnet-4-6', 'https://api.anthropic.com', 50, 'unknown'),
('llm.claude-haiku', 'llm', 'Claude Haiku', 'Дешёвая модель для простых задач', 'claude-haiku-4-5', 'https://api.anthropic.com', 50, 'unknown'),
('llm.gpt4o-mini', 'llm', 'GPT-4o mini', 'Альтернатива через OpenRouter', 'gpt-4o-mini', 'https://openrouter.ai', 50, 'unknown'),
('framework.hermes', 'framework', 'Hermes Agent', 'Наш оркестратор', 'installed', 'https://github.com/search?q=hermes+agent', 100, 'ok'),
('framework.google-adk', 'framework', 'Google ADK', 'Альтернативный фреймворк', 'unknown', 'https://github.com/google/adk-python', 50, 'unknown'),
('framework.langgraph', 'framework', 'LangGraph', 'Граф-фреймворк для агентов', 'unknown', 'https://github.com/langchain-ai/langgraph', 50, 'unknown'),
('framework.crewai', 'framework', 'CrewAI', 'Multi-agent фреймворк', 'unknown', 'https://github.com/crewAIInc/crewAI', 50, 'unknown'),
('framework.moai-adk', 'framework', 'MoAI-ADK', 'ADK для Claude Code', 'unknown', 'https://github.com/modu-ai/moai-adk', 50, 'unknown'),
('infra.python', 'infra', 'Python', 'Runtime агентов', '3.12', 'https://pypi.org/pypi/pip/json', 80, 'ok'),
('infra.fastapi', 'infra', 'FastAPI', 'Dashboard backend', 'unknown', 'https://pypi.org/pypi/fastapi/json', 50, 'unknown'),
('infra.redis', 'infra', 'Redis', 'Message queue', '7', 'https://hub.docker.com/r/library/redis/tags', 80, 'ok'),
('infra.postgres', 'infra', 'PostgreSQL', 'База данных', '16', 'https://hub.docker.com/r/library/postgres/tags', 80, 'ok'),
('infra.orbstack', 'infra', 'OrbStack', 'Docker runtime', 'v2.1.3', 'https://orbstack.dev', 80, 'ok'),
('skill.cost-reporter', 'skill', 'cost-reporter', 'Отчёт расходов', 'v1.1', NULL, 100, 'ok'),
('skill.system-status', 'skill', 'system-status', 'Статус системы', 'v1.0', NULL, 100, 'ok'),
('skill.git-manager', 'skill', 'git-manager', 'GitHub менеджер', 'v1.0', NULL, 100, 'ok')
ON CONFLICT DO NOTHING;
