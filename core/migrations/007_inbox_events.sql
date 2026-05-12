BEGIN;

CREATE TABLE IF NOT EXISTS inbox_events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT UNIQUE NOT NULL,
  source TEXT NOT NULL DEFAULT 'dashboard',
  source_message_id TEXT,
  owner_id TEXT,
  raw_text TEXT NOT NULL,
  normalized_intent TEXT,
  intent_class TEXT NOT NULL DEFAULT 'UNKNOWN',
  project_id TEXT,
  priority TEXT NOT NULL DEFAULT 'P2',
  risk_level TEXT NOT NULL DEFAULT 'low',
  status TEXT NOT NULL DEFAULT 'received',
  requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
  approval_id TEXT,
  agents_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  skills_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  cost_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
  result_summary TEXT,
  error_summary TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inbox_events_created_at ON inbox_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbox_events_intent_class ON inbox_events (intent_class);
CREATE INDEX IF NOT EXISTS idx_inbox_events_project_id ON inbox_events (project_id);
CREATE INDEX IF NOT EXISTS idx_inbox_events_status ON inbox_events (status);
CREATE INDEX IF NOT EXISTS idx_inbox_events_approval_id ON inbox_events (approval_id);
CREATE INDEX IF NOT EXISTS idx_inbox_events_requires_approval ON inbox_events (requires_approval) WHERE requires_approval = TRUE;

CREATE OR REPLACE FUNCTION set_inbox_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_inbox_events_updated_at ON inbox_events;
CREATE TRIGGER trg_inbox_events_updated_at
BEFORE UPDATE ON inbox_events
FOR EACH ROW
EXECUTE FUNCTION set_inbox_events_updated_at();

COMMIT;
