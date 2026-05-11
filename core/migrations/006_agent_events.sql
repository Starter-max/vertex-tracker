BEGIN;

CREATE TABLE IF NOT EXISTS agent_events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT UNIQUE NOT NULL,
  project_id TEXT,
  task_id TEXT,
  parent_task_id TEXT,
  from_agent TEXT,
  to_agent TEXT,
  event_type TEXT NOT NULL,
  status TEXT,
  priority TEXT,
  message TEXT,
  result_summary TEXT,
  skills_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  tools_used JSONB NOT NULL DEFAULT '[]'::jsonb,
  cost_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_created_at ON agent_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_task_id ON agent_events (task_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_project_id ON agent_events (project_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_to_agent ON agent_events (to_agent);
CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent_events (event_type);

COMMIT;
