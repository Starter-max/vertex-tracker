CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(10) REFERENCES projects(id),
    name VARCHAR(100),
    role VARCHAR(50),
    status VARCHAR(20) DEFAULT 'configured',
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO agents (id,project_id,name,role) VALUES
('p01-secretary','p01','Секретарь','secretary'),
('p01-strategist','p01','Стратег','strategist'),
('p01-tracker','p01','Трекер','tracker'),
('p01-analyst','p01','Аналитик','analyst'),
('p02-auditor','p02','Аудитор','auditor'),
('a01-controller','a01','Контроллер','controller'),
('a04-dispatcher','a04','Диспетчер','dispatcher')
ON CONFLICT DO NOTHING;
