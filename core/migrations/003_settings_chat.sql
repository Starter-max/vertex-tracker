CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    group_name VARCHAR(50) DEFAULT 'general',
    label VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) DEFAULT 'Новый чат',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50),
    role VARCHAR(10),
    content TEXT,
    file_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_msg ON chat_messages(session_id,created_at);
