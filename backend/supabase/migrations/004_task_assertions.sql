-- AI Audit Platform - Task Assertions Table
-- Migration: 004_task_assertions.sql
-- Description: Links audit tasks to K-GAAS assertions for assertion-procedure mapping

-- ============================================================================
-- TABLE: TASK_ASSERTIONS
-- ============================================================================
-- Links tasks to audit assertions based on K-GAAS (Korean Generally Accepted Auditing Standards)
-- Each task tests one or more assertions about financial statement items

CREATE TABLE IF NOT EXISTS task_assertions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES audit_tasks(id) ON DELETE CASCADE,
    assertion_type VARCHAR(50) NOT NULL CHECK (assertion_type IN (
        'existence',      -- Assets/liabilities/transactions exist (K-GAAS 315)
        'completeness',   -- All transactions/events are recorded (K-GAAS 315)
        'valuation',      -- Assets/liabilities recorded at appropriate amounts (K-GAAS 315)
        'rights',         -- Entity has rights to assets, obligations for liabilities (K-GAAS 315)
        'presentation'    -- Proper classification, description, disclosure (K-GAAS 315)
    )),
    test_approach TEXT,                   -- Description of how this assertion is tested
    conclusion VARCHAR(20) CHECK (conclusion IN (
        'satisfied',      -- Assertion is satisfied based on evidence
        'exception',      -- Exception identified, requires follow-up
        'pending'         -- Testing not yet complete
    )) DEFAULT 'pending',
    evidence_refs JSONB DEFAULT '[]',     -- Array of document/evidence IDs supporting conclusion
    conclusion_date TIMESTAMPTZ,          -- When conclusion was reached
    concluded_by VARCHAR(100),            -- Agent or user who reached conclusion
    notes TEXT,                           -- Additional notes or observations
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for TASK_ASSERTIONS
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS ix_task_assertions_task ON task_assertions(task_id);
CREATE INDEX IF NOT EXISTS ix_task_assertions_type ON task_assertions(assertion_type);
CREATE INDEX IF NOT EXISTS ix_task_assertions_conclusion ON task_assertions(conclusion);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS ix_task_assertions_task_type ON task_assertions(task_id, assertion_type);
CREATE INDEX IF NOT EXISTS ix_task_assertions_pending ON task_assertions(conclusion) WHERE conclusion = 'pending';
CREATE INDEX IF NOT EXISTS ix_task_assertions_exceptions ON task_assertions(conclusion) WHERE conclusion = 'exception';

-- GIN index for JSONB evidence_refs queries
CREATE INDEX IF NOT EXISTS ix_task_assertions_evidence ON task_assertions USING GIN (evidence_refs);

-- ============================================================================
-- UNIQUE CONSTRAINT
-- ============================================================================

-- Each task can only have one record per assertion type
CREATE UNIQUE INDEX IF NOT EXISTS ix_task_assertions_unique
ON task_assertions(task_id, assertion_type);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE task_assertions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see assertions from tasks in their projects
CREATE POLICY "Users see task_assertions from own projects"
ON task_assertions FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = task_assertions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can insert assertions for tasks in their projects
CREATE POLICY "Users insert task_assertions for own projects"
ON task_assertions FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = task_assertions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can update assertions from tasks in their projects
CREATE POLICY "Users update task_assertions from own projects"
ON task_assertions FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = task_assertions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can delete assertions from tasks in their projects
CREATE POLICY "Users delete task_assertions from own projects"
ON task_assertions FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = task_assertions.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- ============================================================================
-- TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_task_assertions_updated_at
BEFORE UPDATE ON task_assertions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get assertion coverage summary for a task
CREATE OR REPLACE FUNCTION get_assertion_coverage(p_task_id UUID)
RETURNS TABLE (
    assertion_type VARCHAR(50),
    conclusion VARCHAR(20),
    test_approach TEXT,
    evidence_count INT
) AS $$
SELECT
    ta.assertion_type,
    COALESCE(ta.conclusion, 'not_tested') as conclusion,
    ta.test_approach,
    COALESCE(jsonb_array_length(ta.evidence_refs), 0) as evidence_count
FROM (
    SELECT unnest(ARRAY['existence', 'completeness', 'valuation', 'rights', 'presentation']) as assertion_type
) all_types
LEFT JOIN task_assertions ta ON ta.task_id = p_task_id AND ta.assertion_type = all_types.assertion_type
ORDER BY
    CASE all_types.assertion_type
        WHEN 'existence' THEN 1
        WHEN 'completeness' THEN 2
        WHEN 'valuation' THEN 3
        WHEN 'rights' THEN 4
        WHEN 'presentation' THEN 5
    END;
$$ LANGUAGE SQL STABLE;

-- Function to get project-wide assertion summary
CREATE OR REPLACE FUNCTION get_project_assertion_summary(p_project_id UUID)
RETURNS TABLE (
    assertion_type VARCHAR(50),
    total_count BIGINT,
    satisfied_count BIGINT,
    exception_count BIGINT,
    pending_count BIGINT,
    satisfaction_rate NUMERIC
) AS $$
SELECT
    ta.assertion_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE ta.conclusion = 'satisfied') as satisfied_count,
    COUNT(*) FILTER (WHERE ta.conclusion = 'exception') as exception_count,
    COUNT(*) FILTER (WHERE ta.conclusion = 'pending') as pending_count,
    ROUND(
        COUNT(*) FILTER (WHERE ta.conclusion = 'satisfied')::NUMERIC /
        NULLIF(COUNT(*), 0) * 100,
        2
    ) as satisfaction_rate
FROM task_assertions ta
JOIN audit_tasks t ON t.id = ta.task_id
WHERE t.project_id = p_project_id
GROUP BY ta.assertion_type
ORDER BY
    CASE ta.assertion_type
        WHEN 'existence' THEN 1
        WHEN 'completeness' THEN 2
        WHEN 'valuation' THEN 3
        WHEN 'rights' THEN 4
        WHEN 'presentation' THEN 5
    END;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE task_assertions IS 'Links audit tasks to K-GAAS assertions for assertion-procedure mapping';
COMMENT ON COLUMN task_assertions.assertion_type IS 'K-GAAS assertion type: existence, completeness, valuation, rights, presentation';
COMMENT ON COLUMN task_assertions.test_approach IS 'Description of audit procedure used to test this assertion';
COMMENT ON COLUMN task_assertions.conclusion IS 'Test conclusion: satisfied, exception, or pending';
COMMENT ON COLUMN task_assertions.evidence_refs IS 'JSONB array of document/evidence IDs supporting the conclusion';
COMMENT ON FUNCTION get_assertion_coverage(UUID) IS 'Returns assertion coverage summary for a specific task';
COMMENT ON FUNCTION get_project_assertion_summary(UUID) IS 'Returns project-wide assertion testing summary';
