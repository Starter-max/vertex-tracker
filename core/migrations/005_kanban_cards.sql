CREATE TABLE IF NOT EXISTS kanban_cards (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    card_type VARCHAR(30) DEFAULT 'task',
    layer VARCHAR(20) DEFAULT 'strategic',
    project_id VARCHAR(10),
    agent_id VARCHAR(50),
    status VARCHAR(30) DEFAULT 'planned',
    priority VARCHAR(5) DEFAULT 'P2',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    moved_at TIMESTAMPTZ DEFAULT NOW(),
    due_date DATE,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_kanban_status ON kanban_cards(layer, status);
CREATE INDEX IF NOT EXISTS idx_kanban_project ON kanban_cards(project_id);

INSERT INTO kanban_cards (id,title,card_type,layer,project_id,status,priority,description) VALUES
('s-infra-001','Phase 0: Инфраструктура (Redis, Postgres, Docker)','feature','strategic','a01','done','P0','Базовая инфраструктура корпорации'),
('s-infra-002','Dashboard v1: Обзор проектов и метрики','feature','strategic','a08','done','P1','Браузерная панель управления'),
('s-infra-003','Git Manager + версионирование','feature','strategic',NULL,'done','P1','Автокоммиты, GitHub интеграция'),
('s-infra-004','A06 Knowledge Currency System','feature','strategic','a06','done','P2','Отслеживание актуальности компонентов'),
('s-infra-005','Канбан корпорации','feature','strategic','a08','in_progress','P1','Текущая задача'),
('s-p01-001','P01 Бизнес-трекер собственников','feature','strategic','p01','in_progress','P0','Мультиагентный трекер для двух собственников'),
('s-p02-001','P02 Аудит-агент (коммерческий)','feature','strategic','p02','planned','P0','Автономный аудит соцсетей/сайтов → PDF'),
('s-p03-001','P03 SEO/Content мониторинг','feature','strategic','p03','idea','P2','Мониторинг мультиязычного SEO конвейера'),
('s-p04-001','P04 Личный психолог','feature','strategic','p04','idea','P2','Персональный психологический ассистент'),
('s-p05-001','P05 Личный помощник','feature','strategic','p05','idea','P2','Личный ассистент с доступом к системе'),
('s-p06-001','P06 Валидатор задач','feature','strategic','p06','idea','P2','Контроль стихийных реакций, философия 30 мин'),
('s-p07-001','P07 Аналитика для дружественных лиц','feature','strategic','p07','idea','P3','Периодическая аналитика по расписанию'),
('s-a02-001','A02 Security Monitor','feature','strategic',NULL,'planned','P2','Мониторинг уязвимостей и ключей'),
('s-a03-001','A03 Risk Manager','feature','strategic',NULL,'planned','P2','Классификация рисков корпорации'),
('s-a05-001','A05 Quality Auditor','feature','strategic',NULL,'planned','P2','Проверка здоровья агентов'),
('s-a07-001','A07 Dev Assistant','feature','strategic',NULL,'idea','P2','Внутренний разработчик-агент'),
('td-001','Hermes chat: подключить к dashboard','tech_debt','strategic',NULL,'in_progress','P1','Gateway не открывает HTTP — нужен другой подход'),
('td-002','Self-healing Level 2-3 не реализован','tech_debt','strategic',NULL,'planned','P1','LLM диагностика падений агентов'),
('td-003','Backup диск не подключён','tech_debt','strategic',NULL,'planned','P0','Внешний backup диск отсутствует'),
('td-004','Obsidian vault не настроен','tech_debt','strategic',NULL,'planned','P2','Knowledge base для агентов'),
('td-005','Python 3.9.6 системный — заменить везде на 3.12','tech_debt','strategic',NULL,'done','P2','Решено в Phase 0')
ON CONFLICT DO NOTHING;
