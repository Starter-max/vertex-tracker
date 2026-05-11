-- 006_inbox_events.sql
-- Create inbox event journal for Digital Corp master router

CREATE TABLE IF NOT EXISTS inbox_events (
  id BIGSERIAL PRIMARY KEY,
  source VARCHAR(30) NOT NULL DEFAULT 'telegram',
  source_message_id VARCHAR(100),
  owner_id VARCHAR(50),
  raw_text TEXT NOT NULL,
  normalized_intent VARCHAR(100),
  intent_class VARCHAR(50),
  project_id VARCHAR(10),
  priority VARCHAR(5) DEFAULT 'P2',
  risk_level VARCHAR(10) DEFAULT 'low',
  status VARCHAR(30) NOT NULL DEFAULT 'received',
  requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
  approval_id VARCHAR(64),
  agents_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  skills_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  cost_usd NUMERIC(10,6) DEFAULT 0,
  result_summary TEXT,
  error_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inbox_events_created_at ON inbox_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbox_events_status ON inbox_events(status);
CREATE INDEX IF NOT EXISTS idx_inbox_events_intent ON inbox_events(intent_class);
CREATE INDEX IF NOT EXISTS idx_inbox_events_project ON inbox_events(project_id);
CREATE INDEX IF NOT EXISTS idx_inbox_events_approval ON inbox_events(requires_approval, approval_id);
