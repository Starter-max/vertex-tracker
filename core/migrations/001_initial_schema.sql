-- Phase 0: базовые таблицы
CREATE TABLE IF NOT EXISTS costs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50),
    project_id VARCHAR(10),
    model VARCHAR(100),
    tokens_in INT DEFAULT 0,
    tokens_out INT DEFAULT 0,
    cost_usd DECIMAL(10,8) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_costs_project ON costs(project_id);
CREATE INDEX IF NOT EXISTS idx_costs_created ON costs(created_at);

CREATE TABLE IF NOT EXISTS agent_health (
    agent_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'unknown',
    last_heartbeat TIMESTAMPTZ,
    restart_count INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    type VARCHAR(20),
    budget_daily DECIMAL(10,2),
    budget_monthly DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO projects VALUES
  ('p01','Бизнес-трекер собственников','active','business',5.00,100.00),
  ('p02','Аудит-агент','active','business',10.00,200.00),
  ('a01','Контроллер расходов','active','admin',1.00,20.00),
  ('a04','Диспетчер оповещений','active','admin',0.50,10.00)
ON CONFLICT DO NOTHING;
