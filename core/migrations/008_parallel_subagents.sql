-- 008_parallel_subagents.sql
-- Safe additive migration for Digital Corp parallel async task layer.
-- No destructive operations.

CREATE TABLE IF NOT EXISTS agent_instances (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
    profile_name TEXT,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    current_work_package_id TEXT,
    current_subtask_id TEXT,
    last_heartbeat TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_packages (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    owner_id TEXT DEFAULT 'kevin',
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    kanban_card_id TEXT REFERENCES kanban_cards(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    priority TEXT NOT NULL DEFAULT 'P2',
    parallel_limit INTEGER NOT NULL DEFAULT 3,
    requires_backup BOOLEAN NOT NULL DEFAULT TRUE,
    backup_ref TEXT,
    diagnostic_ref TEXT,
    result_summary TEXT,
    error_summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subtasks (
    id TEXT PRIMARY KEY,
    work_package_id TEXT NOT NULL REFERENCES work_packages(id) ON DELETE CASCADE,
    parent_subtask_id TEXT REFERENCES subtasks(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    assignee_agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
    assignee_profile TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    priority TEXT NOT NULL DEFAULT 'P2',
    parallel_group_id TEXT,
    dependency_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result_summary TEXT,
    error_summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS owner_decisions (
    id TEXT PRIMARY KEY,
    work_package_id TEXT REFERENCES work_packages(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    selected_option TEXT,
    response TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS parallel_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    work_package_id TEXT REFERENCES work_packages(id) ON DELETE CASCADE,
    subtask_id TEXT REFERENCES subtasks(id) ON DELETE SET NULL,
    agent_id TEXT,
    severity TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS kanban_master_id TEXT;
ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS parent_task_id TEXT;
ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS work_package_id TEXT REFERENCES work_packages(id) ON DELETE SET NULL;
ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS subagent_id TEXT;
ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS parallel_group_id TEXT;
ALTER TABLE kanban_cards ADD COLUMN IF NOT EXISTS result_summary TEXT;

CREATE INDEX IF NOT EXISTS idx_work_packages_status ON work_packages(status);
CREATE INDEX IF NOT EXISTS idx_work_packages_project ON work_packages(project_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_package_status ON subtasks(work_package_id, status);
CREATE INDEX IF NOT EXISTS idx_parallel_events_package ON parallel_events(work_package_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kanban_cards_work_package ON kanban_cards(work_package_id);
