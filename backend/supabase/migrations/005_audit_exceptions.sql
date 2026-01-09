-- AI Audit Platform - Audit Exceptions Table
-- Migration: 005_audit_exceptions.sql
-- Description: Track procedure deviations, control deficiencies, misstatements, and scope limitations

-- ============================================================================
-- TABLE: AUDIT_EXCEPTIONS
-- ============================================================================
-- Tracks all types of audit exceptions requiring follow-up or escalation

CREATE TABLE IF NOT EXISTS audit_exceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES audit_tasks(id) ON DELETE CASCADE,
    assertion_id UUID REFERENCES task_assertions(id) ON DELETE SET NULL,  -- Optional link to specific assertion
    exception_type VARCHAR(50) NOT NULL CHECK (exception_type IN (
        'procedure_deviation',   -- Deviation from planned audit procedure
        'control_deficiency',    -- Internal control weakness identified
        'misstatement',          -- Monetary or disclosure misstatement
        'scope_limitation'       -- Limitation on audit scope
    )),
    severity VARCHAR(20) NOT NULL CHECK (severity IN (
        'minor',                 -- Inconsequential, no impact on opinion
        'significant',           -- Requires adjustment or disclosure
        'material'               -- Could affect audit opinion
    )),
    description TEXT NOT NULL,            -- Detailed description of the exception
    root_cause TEXT,                      -- Analysis of why this occurred
    remediation_plan TEXT,                -- Proposed corrective action
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN (
        'open',                  -- Exception identified, awaiting action
        'addressed',             -- Corrective action taken
        'waived',                -- Accepted without correction (documented)
        'escalated'              -- Escalated to higher authority
    )),
    -- Identification tracking
    identified_by VARCHAR(100),           -- Agent or user who identified
    identified_at TIMESTAMPTZ DEFAULT NOW(),
    -- Resolution tracking
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    -- Impact assessment
    monetary_impact NUMERIC(15, 2),       -- Estimated monetary impact (if applicable)
    affected_accounts JSONB DEFAULT '[]', -- List of affected account codes
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for AUDIT_EXCEPTIONS
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS ix_exceptions_task ON audit_exceptions(task_id);
CREATE INDEX IF NOT EXISTS ix_exceptions_assertion ON audit_exceptions(assertion_id);
CREATE INDEX IF NOT EXISTS ix_exceptions_status ON audit_exceptions(status);
CREATE INDEX IF NOT EXISTS ix_exceptions_type ON audit_exceptions(exception_type);
CREATE INDEX IF NOT EXISTS ix_exceptions_severity ON audit_exceptions(severity);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS ix_exceptions_open_severity ON audit_exceptions(status, severity)
    WHERE status = 'open';
CREATE INDEX IF NOT EXISTS ix_exceptions_material ON audit_exceptions(severity)
    WHERE severity = 'material';
CREATE INDEX IF NOT EXISTS ix_exceptions_identified_at ON audit_exceptions(identified_at DESC);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS ix_exceptions_affected_accounts ON audit_exceptions USING GIN (affected_accounts);
CREATE INDEX IF NOT EXISTS ix_exceptions_metadata ON audit_exceptions USING GIN (metadata);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE audit_exceptions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see exceptions from tasks in their projects
CREATE POLICY "Users see audit_exceptions from own projects"
ON audit_exceptions FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = audit_exceptions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can insert exceptions for tasks in their projects
CREATE POLICY "Users insert audit_exceptions for own projects"
ON audit_exceptions FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = audit_exceptions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can update exceptions from tasks in their projects
CREATE POLICY "Users update audit_exceptions from own projects"
ON audit_exceptions FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = audit_exceptions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can delete exceptions from tasks in their projects
CREATE POLICY "Users delete audit_exceptions from own projects"
ON audit_exceptions FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = audit_exceptions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- ============================================================================
-- TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_audit_exceptions_updated_at
BEFORE UPDATE ON audit_exceptions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRIGGER FOR AUTO-SET RESOLVED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION set_exception_resolved_at()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-set resolved_at when status changes to 'addressed' or 'waived'
    IF NEW.status IN ('addressed', 'waived') AND OLD.status NOT IN ('addressed', 'waived') THEN
        NEW.resolved_at = COALESCE(NEW.resolved_at, NOW());
    END IF;

    -- Clear resolved_at if status changes back to 'open'
    IF NEW.status = 'open' AND OLD.status != 'open' THEN
        NEW.resolved_at = NULL;
        NEW.resolution_notes = NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_exception_resolved_at
BEFORE UPDATE ON audit_exceptions
FOR EACH ROW
EXECUTE FUNCTION set_exception_resolved_at();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get exception summary for a project
CREATE OR REPLACE FUNCTION get_project_exception_summary(p_project_id UUID)
RETURNS TABLE (
    exception_type VARCHAR(50),
    severity VARCHAR(20),
    status VARCHAR(20),
    exception_count BIGINT,
    total_monetary_impact NUMERIC(15, 2)
) AS $$
SELECT
    ae.exception_type,
    ae.severity,
    ae.status,
    COUNT(*) as exception_count,
    SUM(COALESCE(ae.monetary_impact, 0)) as total_monetary_impact
FROM audit_exceptions ae
JOIN audit_tasks t ON t.id = ae.task_id
WHERE t.project_id = p_project_id
GROUP BY ae.exception_type, ae.severity, ae.status
ORDER BY
    CASE ae.severity WHEN 'material' THEN 1 WHEN 'significant' THEN 2 WHEN 'minor' THEN 3 END,
    CASE ae.status WHEN 'open' THEN 1 WHEN 'escalated' THEN 2 WHEN 'addressed' THEN 3 WHEN 'waived' THEN 4 END;
$$ LANGUAGE SQL STABLE;

-- Function to get open material exceptions requiring attention
CREATE OR REPLACE FUNCTION get_critical_exceptions(p_project_id UUID)
RETURNS TABLE (
    id UUID,
    task_id UUID,
    exception_type VARCHAR(50),
    description TEXT,
    monetary_impact NUMERIC(15, 2),
    identified_at TIMESTAMPTZ,
    days_open INT
) AS $$
SELECT
    ae.id,
    ae.task_id,
    ae.exception_type,
    ae.description,
    ae.monetary_impact,
    ae.identified_at,
    EXTRACT(DAY FROM NOW() - ae.identified_at)::INT as days_open
FROM audit_exceptions ae
JOIN audit_tasks t ON t.id = ae.task_id
WHERE t.project_id = p_project_id
    AND ae.status IN ('open', 'escalated')
    AND ae.severity IN ('material', 'significant')
ORDER BY
    CASE ae.severity WHEN 'material' THEN 1 WHEN 'significant' THEN 2 END,
    ae.identified_at ASC;
$$ LANGUAGE SQL STABLE;

-- Function to calculate materiality impact
CREATE OR REPLACE FUNCTION calculate_exception_materiality(p_project_id UUID)
RETURNS TABLE (
    total_misstatements NUMERIC(15, 2),
    material_misstatements NUMERIC(15, 2),
    significant_misstatements NUMERIC(15, 2),
    minor_misstatements NUMERIC(15, 2),
    overall_materiality NUMERIC(15, 2),
    materiality_threshold_exceeded BOOLEAN
) AS $$
WITH project_data AS (
    SELECT overall_materiality FROM audit_projects WHERE id = p_project_id
),
exception_sums AS (
    SELECT
        SUM(COALESCE(ae.monetary_impact, 0)) FILTER (WHERE ae.exception_type = 'misstatement') as total_misstatements,
        SUM(COALESCE(ae.monetary_impact, 0)) FILTER (WHERE ae.exception_type = 'misstatement' AND ae.severity = 'material') as material_misstatements,
        SUM(COALESCE(ae.monetary_impact, 0)) FILTER (WHERE ae.exception_type = 'misstatement' AND ae.severity = 'significant') as significant_misstatements,
        SUM(COALESCE(ae.monetary_impact, 0)) FILTER (WHERE ae.exception_type = 'misstatement' AND ae.severity = 'minor') as minor_misstatements
    FROM audit_exceptions ae
    JOIN audit_tasks t ON t.id = ae.task_id
    WHERE t.project_id = p_project_id
        AND ae.status NOT IN ('waived')
)
SELECT
    COALESCE(es.total_misstatements, 0),
    COALESCE(es.material_misstatements, 0),
    COALESCE(es.significant_misstatements, 0),
    COALESCE(es.minor_misstatements, 0),
    pd.overall_materiality,
    COALESCE(es.total_misstatements, 0) > COALESCE(pd.overall_materiality, 0) as materiality_threshold_exceeded
FROM exception_sums es
CROSS JOIN project_data pd;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE audit_exceptions IS 'Tracks audit exceptions: procedure deviations, control deficiencies, misstatements, scope limitations';
COMMENT ON COLUMN audit_exceptions.exception_type IS 'Type of exception: procedure_deviation, control_deficiency, misstatement, scope_limitation';
COMMENT ON COLUMN audit_exceptions.severity IS 'Exception severity: minor, significant, material';
COMMENT ON COLUMN audit_exceptions.status IS 'Current status: open, addressed, waived, escalated';
COMMENT ON COLUMN audit_exceptions.monetary_impact IS 'Estimated monetary impact for misstatements';
COMMENT ON COLUMN audit_exceptions.affected_accounts IS 'JSONB array of affected account codes';
COMMENT ON FUNCTION get_project_exception_summary(UUID) IS 'Returns exception summary grouped by type, severity, status';
COMMENT ON FUNCTION get_critical_exceptions(UUID) IS 'Returns open material/significant exceptions requiring attention';
COMMENT ON FUNCTION calculate_exception_materiality(UUID) IS 'Calculates total misstatements vs. materiality threshold';
