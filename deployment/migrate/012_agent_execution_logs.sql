-- 012: Agent Execution Logs table
-- Records each agent scan/trigger execution for monitoring and debugging

BEGIN;

CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES writing_agents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL,           -- 'intelligent', 'legacy', 'manual'
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'cron',  -- 'cron', 'manual'
    status VARCHAR(20) NOT NULL DEFAULT 'running',     -- 'running', 'success', 'failed', 'skipped'
    drafts_created INTEGER NOT NULL DEFAULT 0,
    topics_found INTEGER NOT NULL DEFAULT 0,
    hotspots_matched INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_exec_logs_agent_id ON agent_execution_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_exec_logs_user_id ON agent_execution_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_exec_logs_started_at ON agent_execution_logs(started_at DESC);

COMMIT;
