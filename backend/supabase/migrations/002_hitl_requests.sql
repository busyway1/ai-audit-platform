-- AI Audit Platform - HITL Requests Table
-- Migration: 002_hitl_requests.sql
-- Description: Create hitl_requests table for Human-in-the-Loop workflow

-- ============================================================================
-- TABLE: HITL_REQUESTS (Human-in-the-Loop Requests)
-- ============================================================================
-- Stores HITL approval/review requests for tasks exceeding urgency thresholds

CREATE TABLE IF NOT EXISTS hitl_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES audit_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES audit_tasks(id) ON DELETE SET NULL,
    thread_id TEXT,                                    -- LangGraph thread ID for workflow resume
    request_type TEXT NOT NULL DEFAULT 'urgency_threshold', -- 'urgency_threshold', 'materiality_exceeded', 'manual_request', 'system_alert'
    urgency_score NUMERIC(5, 2) DEFAULT 0,             -- Calculated urgency score (0-100)
    urgency_level TEXT NOT NULL DEFAULT 'medium',      -- 'critical', 'high', 'medium', 'low'
    status TEXT NOT NULL DEFAULT 'pending',            -- 'pending', 'approved', 'rejected', 'escalated', 'expired'
    title TEXT NOT NULL,
    description TEXT,
    context JSONB DEFAULT '{}',                        -- Relevant context for decision-making
    response JSONB,                                    -- Human response (action, comment, modified_values)
    responded_by TEXT,                                 -- User ID who responded
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for HITL_REQUESTS
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_hitl_requests_project ON hitl_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_task ON hitl_requests(task_id);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_thread ON hitl_requests(thread_id);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_status ON hitl_requests(status);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_urgency_level ON hitl_requests(urgency_level);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_urgency_score ON hitl_requests(urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_created ON hitl_requests(created_at DESC);

-- Composite index for common query pattern (pending requests sorted by urgency)
CREATE INDEX IF NOT EXISTS idx_hitl_requests_pending_urgency
ON hitl_requests(status, urgency_score DESC)
WHERE status = 'pending';

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE hitl_requests ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see HITL requests from their projects
CREATE POLICY "Users see hitl_requests from own projects"
ON hitl_requests FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = hitl_requests.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can insert HITL requests for their projects
CREATE POLICY "Users insert hitl_requests for own projects"
ON hitl_requests FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = hitl_requests.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can update HITL requests from their projects
CREATE POLICY "Users update hitl_requests from own projects"
ON hitl_requests FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = hitl_requests.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- ============================================================================
-- REALTIME PUBLICATION
-- ============================================================================
-- Enable Realtime for live HITL queue updates in frontend

ALTER PUBLICATION supabase_realtime ADD TABLE hitl_requests;

-- ============================================================================
-- TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_hitl_requests_updated_at
BEFORE UPDATE ON hitl_requests
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE hitl_requests IS 'Human-in-the-loop approval and review requests for audit tasks';
COMMENT ON COLUMN hitl_requests.thread_id IS 'LangGraph thread ID for resuming workflow after HITL response';
COMMENT ON COLUMN hitl_requests.urgency_score IS 'Calculated urgency score (0-100) based on risk factors';
COMMENT ON COLUMN hitl_requests.urgency_level IS 'Urgency level: critical (>80), high (>60), medium (>40), low (<=40)';
