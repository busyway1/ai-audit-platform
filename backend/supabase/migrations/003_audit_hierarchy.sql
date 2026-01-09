-- AI Audit Platform - Audit Hierarchy Table
-- Migration: 003_audit_hierarchy.sql
-- Description: 3-level audit hierarchy (Business Process -> FSLI -> EGA)

-- ============================================================================
-- TABLE: AUDIT_HIERARCHY
-- ============================================================================
-- Stores hierarchical audit structure with 3 levels:
--   high: Business Process (e.g., "Revenue Cycle", "Procurement Cycle")
--   mid:  FSLI - Financial Statement Line Item (e.g., "Sales Revenue", "Accounts Receivable")
--   low:  EGA - Entity/Group Account (e.g., "Domestic Sales", "Export Sales")

CREATE TABLE IF NOT EXISTS audit_hierarchy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES audit_projects(id) ON DELETE CASCADE,
    level VARCHAR(10) NOT NULL CHECK (level IN ('high', 'mid', 'low')),
    parent_id UUID REFERENCES audit_hierarchy(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    source_column VARCHAR(100),           -- Excel column reference (e.g., "A", "B", "C")
    source_row INTEGER,                   -- Excel row reference
    ref_no VARCHAR(50),                   -- Reference number (e.g., "BP-001", "FSLI-001", "EGA-001")
    status VARCHAR(50) DEFAULT 'active',  -- 'active', 'inactive', 'archived'
    metadata JSONB DEFAULT '{}',          -- Additional properties (risk_assessment, materiality, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for AUDIT_HIERARCHY
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS ix_hierarchy_project ON audit_hierarchy(project_id);
CREATE INDEX IF NOT EXISTS ix_hierarchy_parent ON audit_hierarchy(parent_id);
CREATE INDEX IF NOT EXISTS ix_hierarchy_level ON audit_hierarchy(level);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS ix_hierarchy_project_level ON audit_hierarchy(project_id, level);
CREATE INDEX IF NOT EXISTS ix_hierarchy_ref_no ON audit_hierarchy(ref_no);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS ix_hierarchy_metadata ON audit_hierarchy USING GIN (metadata);

-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Ensure parent-child level consistency (parent must be higher level)
-- high > mid > low
ALTER TABLE audit_hierarchy ADD CONSTRAINT chk_hierarchy_parent_level CHECK (
    (parent_id IS NULL AND level = 'high') OR
    (parent_id IS NOT NULL)
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE audit_hierarchy ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see hierarchy from their projects
CREATE POLICY "Users see audit_hierarchy from own projects"
ON audit_hierarchy FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = audit_hierarchy.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can insert hierarchy for their projects
CREATE POLICY "Users insert audit_hierarchy for own projects"
ON audit_hierarchy FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = audit_hierarchy.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can update hierarchy from their projects
CREATE POLICY "Users update audit_hierarchy from own projects"
ON audit_hierarchy FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = audit_hierarchy.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can delete hierarchy from their projects
CREATE POLICY "Users delete audit_hierarchy from own projects"
ON audit_hierarchy FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = audit_hierarchy.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- ============================================================================
-- TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_audit_hierarchy_updated_at
BEFORE UPDATE ON audit_hierarchy
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get full hierarchy path (breadcrumb)
CREATE OR REPLACE FUNCTION get_hierarchy_path(hierarchy_id UUID)
RETURNS TABLE (
    id UUID,
    level VARCHAR(10),
    name VARCHAR(500),
    depth INT
) AS $$
WITH RECURSIVE hierarchy_path AS (
    -- Base case: start from the given node
    SELECT h.id, h.level, h.name, h.parent_id, 0 AS depth
    FROM audit_hierarchy h
    WHERE h.id = hierarchy_id

    UNION ALL

    -- Recursive case: traverse up to parents
    SELECT h.id, h.level, h.name, h.parent_id, hp.depth + 1
    FROM audit_hierarchy h
    JOIN hierarchy_path hp ON h.id = hp.parent_id
)
SELECT hp.id, hp.level, hp.name, hp.depth
FROM hierarchy_path hp
ORDER BY hp.depth DESC;
$$ LANGUAGE SQL STABLE;

-- Function to get all descendants of a hierarchy node
CREATE OR REPLACE FUNCTION get_hierarchy_descendants(hierarchy_id UUID)
RETURNS TABLE (
    id UUID,
    level VARCHAR(10),
    name VARCHAR(500),
    parent_id UUID,
    depth INT
) AS $$
WITH RECURSIVE hierarchy_tree AS (
    -- Base case: start from the given node
    SELECT h.id, h.level, h.name, h.parent_id, 0 AS depth
    FROM audit_hierarchy h
    WHERE h.id = hierarchy_id

    UNION ALL

    -- Recursive case: traverse down to children
    SELECT h.id, h.level, h.name, h.parent_id, ht.depth + 1
    FROM audit_hierarchy h
    JOIN hierarchy_tree ht ON h.parent_id = ht.id
)
SELECT ht.id, ht.level, ht.name, ht.parent_id, ht.depth
FROM hierarchy_tree ht
WHERE ht.id != hierarchy_id  -- Exclude the starting node
ORDER BY ht.depth, ht.name;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE audit_hierarchy IS '3-level audit hierarchy: Business Process (high) -> FSLI (mid) -> EGA (low)';
COMMENT ON COLUMN audit_hierarchy.level IS 'Hierarchy level: high=Business Process, mid=FSLI, low=EGA';
COMMENT ON COLUMN audit_hierarchy.parent_id IS 'Reference to parent node (NULL for top-level Business Processes)';
COMMENT ON COLUMN audit_hierarchy.source_column IS 'Excel column reference from source mapping file';
COMMENT ON COLUMN audit_hierarchy.source_row IS 'Excel row reference from source mapping file';
COMMENT ON COLUMN audit_hierarchy.ref_no IS 'Reference number (e.g., BP-001, FSLI-001, EGA-001)';
COMMENT ON FUNCTION get_hierarchy_path(UUID) IS 'Returns full path from root to given hierarchy node';
COMMENT ON FUNCTION get_hierarchy_descendants(UUID) IS 'Returns all descendant nodes of given hierarchy node';
