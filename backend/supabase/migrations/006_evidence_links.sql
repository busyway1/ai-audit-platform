-- AI Audit Platform - Evidence Links Tables
-- Migration: 006_evidence_links.sql
-- Description: Document-Task-WorkPaper many-to-many relationships and evidence chain tracking

-- ============================================================================
-- TABLE: EVIDENCE_LINKS
-- ============================================================================
-- Creates many-to-many relationships between various audit entities and documents/evidence

CREATE TABLE IF NOT EXISTS evidence_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Source entity (what is being supported by evidence)
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN (
        'task',              -- Links to audit_tasks
        'workpaper',         -- Links to audit_artifacts (workpapers)
        'assertion',         -- Links to task_assertions
        'exception'          -- Links to audit_exceptions
    )),
    source_id UUID NOT NULL,
    -- Target document (the evidence)
    document_id UUID REFERENCES audit_artifacts(id) ON DELETE SET NULL,
    document_path TEXT,                   -- Alternative: file path if not in audit_artifacts
    -- Link metadata
    link_type VARCHAR(50) NOT NULL CHECK (link_type IN (
        'supporting',        -- Document supports the source entity
        'referenced',        -- Source entity references the document
        'generated'          -- Source entity generated this document
    )),
    page_range VARCHAR(50),               -- Specific pages (e.g., "1-5", "10,15,20")
    section_ref VARCHAR(100),             -- Section reference within document
    description TEXT,                     -- Description of how this evidence relates
    -- Audit trail
    linked_at TIMESTAMPTZ DEFAULT NOW(),
    linked_by VARCHAR(100),               -- Agent or user who created the link
    verified_at TIMESTAMPTZ,              -- When link was verified
    verified_by VARCHAR(100),             -- Who verified the link
    -- Metadata
    relevance_score NUMERIC(3, 2),        -- 0.00 to 1.00 relevance score
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for EVIDENCE_LINKS
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS ix_evidence_source ON evidence_links(source_type, source_id);
CREATE INDEX IF NOT EXISTS ix_evidence_document ON evidence_links(document_id);
CREATE INDEX IF NOT EXISTS ix_evidence_link_type ON evidence_links(link_type);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS ix_evidence_source_type ON evidence_links(source_type);
CREATE INDEX IF NOT EXISTS ix_evidence_linked_at ON evidence_links(linked_at DESC);

-- GIN index for JSONB metadata
CREATE INDEX IF NOT EXISTS ix_evidence_metadata ON evidence_links USING GIN (metadata);

-- ============================================================================
-- UNIQUE CONSTRAINT
-- ============================================================================

-- Prevent duplicate links between same source and document
CREATE UNIQUE INDEX IF NOT EXISTS ix_evidence_links_unique
ON evidence_links(source_type, source_id, document_id, link_type)
WHERE document_id IS NOT NULL;

-- ============================================================================
-- TABLE: EVIDENCE_CHAIN
-- ============================================================================
-- Tracks complete evidence trails from original source to final workpaper

CREATE TABLE IF NOT EXISTS evidence_chain (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES audit_projects(id) ON DELETE CASCADE,
    chain_name VARCHAR(200),              -- Descriptive name for the chain
    chain_description TEXT,               -- Description of what this chain proves
    root_document_id UUID REFERENCES audit_artifacts(id) ON DELETE SET NULL,
    chain_path JSONB NOT NULL DEFAULT '[]',  -- Ordered list of document/entity IDs in chain
    -- Chain validation
    is_complete BOOLEAN DEFAULT FALSE,    -- Whether chain is fully verified
    validated_at TIMESTAMPTZ,
    validated_by VARCHAR(100),
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for EVIDENCE_CHAIN
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_evidence_chain_project ON evidence_chain(project_id);
CREATE INDEX IF NOT EXISTS ix_evidence_chain_root ON evidence_chain(root_document_id);
CREATE INDEX IF NOT EXISTS ix_evidence_chain_complete ON evidence_chain(is_complete);
CREATE INDEX IF NOT EXISTS ix_evidence_chain_path ON evidence_chain USING GIN (chain_path);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_chain ENABLE ROW LEVEL SECURITY;

-- Evidence Links RLS Policies
-- Note: Complex RLS due to polymorphic source_type
CREATE POLICY "Users see evidence_links from own projects"
ON evidence_links FOR SELECT
USING (
    -- Check based on source_type
    CASE source_type
        WHEN 'task' THEN EXISTS (
            SELECT 1 FROM audit_tasks t
            JOIN audit_projects p ON p.id = t.project_id
            WHERE t.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'workpaper' THEN EXISTS (
            SELECT 1 FROM audit_artifacts a
            JOIN audit_tasks t ON t.id = a.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE a.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'assertion' THEN EXISTS (
            SELECT 1 FROM task_assertions ta
            JOIN audit_tasks t ON t.id = ta.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE ta.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'exception' THEN EXISTS (
            SELECT 1 FROM audit_exceptions ae
            JOIN audit_tasks t ON t.id = ae.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE ae.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        ELSE FALSE
    END
);

CREATE POLICY "Users insert evidence_links for own projects"
ON evidence_links FOR INSERT
WITH CHECK (
    CASE source_type
        WHEN 'task' THEN EXISTS (
            SELECT 1 FROM audit_tasks t
            JOIN audit_projects p ON p.id = t.project_id
            WHERE t.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'workpaper' THEN EXISTS (
            SELECT 1 FROM audit_artifacts a
            JOIN audit_tasks t ON t.id = a.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE a.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'assertion' THEN EXISTS (
            SELECT 1 FROM task_assertions ta
            JOIN audit_tasks t ON t.id = ta.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE ta.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        WHEN 'exception' THEN EXISTS (
            SELECT 1 FROM audit_exceptions ae
            JOIN audit_tasks t ON t.id = ae.task_id
            JOIN audit_projects p ON p.id = t.project_id
            WHERE ae.id = evidence_links.source_id
            AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
        )
        ELSE FALSE
    END
);

-- Evidence Chain RLS Policies (simpler - direct project reference)
CREATE POLICY "Users see evidence_chain from own projects"
ON evidence_chain FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = evidence_chain.project_id
        AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
    )
);

CREATE POLICY "Users insert evidence_chain for own projects"
ON evidence_chain FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = evidence_chain.project_id
        AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
    )
);

CREATE POLICY "Users update evidence_chain from own projects"
ON evidence_chain FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = evidence_chain.project_id
        AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
    )
);

CREATE POLICY "Users delete evidence_chain from own projects"
ON evidence_chain FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = evidence_chain.project_id
        AND (auth.uid()::text = (p.metadata->>'created_by') OR auth.jwt()->>'role' = 'admin')
    )
);

-- ============================================================================
-- TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_evidence_chain_updated_at
BEFORE UPDATE ON evidence_chain
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get all evidence for a source entity
CREATE OR REPLACE FUNCTION get_evidence_for_source(
    p_source_type VARCHAR(50),
    p_source_id UUID
)
RETURNS TABLE (
    link_id UUID,
    document_id UUID,
    document_path TEXT,
    link_type VARCHAR(50),
    page_range VARCHAR(50),
    description TEXT,
    linked_at TIMESTAMPTZ,
    linked_by VARCHAR(100),
    artifact_type TEXT,
    artifact_content TEXT
) AS $$
SELECT
    el.id as link_id,
    el.document_id,
    el.document_path,
    el.link_type,
    el.page_range,
    el.description,
    el.linked_at,
    el.linked_by,
    a.artifact_type,
    a.content as artifact_content
FROM evidence_links el
LEFT JOIN audit_artifacts a ON a.id = el.document_id
WHERE el.source_type = p_source_type
    AND el.source_id = p_source_id
ORDER BY el.linked_at DESC;
$$ LANGUAGE SQL STABLE;

-- Function to get reverse links (what entities reference a document)
CREATE OR REPLACE FUNCTION get_document_references(p_document_id UUID)
RETURNS TABLE (
    link_id UUID,
    source_type VARCHAR(50),
    source_id UUID,
    link_type VARCHAR(50),
    description TEXT,
    linked_at TIMESTAMPTZ
) AS $$
SELECT
    el.id as link_id,
    el.source_type,
    el.source_id,
    el.link_type,
    el.description,
    el.linked_at
FROM evidence_links el
WHERE el.document_id = p_document_id
ORDER BY el.source_type, el.linked_at DESC;
$$ LANGUAGE SQL STABLE;

-- Function to validate an evidence chain
CREATE OR REPLACE FUNCTION validate_evidence_chain(p_chain_id UUID)
RETURNS TABLE (
    is_valid BOOLEAN,
    total_nodes INT,
    verified_nodes INT,
    missing_documents TEXT[],
    validation_errors TEXT[]
) AS $$
DECLARE
    v_chain_path JSONB;
    v_node JSONB;
    v_total_nodes INT := 0;
    v_verified_nodes INT := 0;
    v_missing_documents TEXT[] := '{}';
    v_validation_errors TEXT[] := '{}';
    v_doc_exists BOOLEAN;
BEGIN
    -- Get the chain path
    SELECT chain_path INTO v_chain_path FROM evidence_chain WHERE id = p_chain_id;

    IF v_chain_path IS NULL THEN
        RETURN QUERY SELECT FALSE, 0, 0, ARRAY['Chain not found']::TEXT[], ARRAY['Chain ID does not exist']::TEXT[];
        RETURN;
    END IF;

    -- Iterate through chain nodes
    FOR v_node IN SELECT * FROM jsonb_array_elements(v_chain_path)
    LOOP
        v_total_nodes := v_total_nodes + 1;

        -- Check if document exists
        SELECT EXISTS(
            SELECT 1 FROM audit_artifacts WHERE id = (v_node->>'document_id')::UUID
        ) INTO v_doc_exists;

        IF v_doc_exists THEN
            v_verified_nodes := v_verified_nodes + 1;
        ELSE
            v_missing_documents := array_append(v_missing_documents, v_node->>'document_id');
            v_validation_errors := array_append(v_validation_errors, 'Document ' || (v_node->>'document_id') || ' not found');
        END IF;
    END LOOP;

    RETURN QUERY SELECT
        (v_total_nodes = v_verified_nodes AND v_total_nodes > 0),
        v_total_nodes,
        v_verified_nodes,
        v_missing_documents,
        v_validation_errors;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to build evidence chain from task
CREATE OR REPLACE FUNCTION build_task_evidence_chain(p_task_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_chain JSONB := '[]';
    v_link RECORD;
BEGIN
    -- Collect all direct evidence links
    FOR v_link IN
        SELECT
            el.document_id,
            el.link_type,
            el.page_range,
            el.description,
            a.artifact_type,
            a.file_path
        FROM evidence_links el
        LEFT JOIN audit_artifacts a ON a.id = el.document_id
        WHERE el.source_type = 'task' AND el.source_id = p_task_id
        ORDER BY el.linked_at
    LOOP
        v_chain := v_chain || jsonb_build_object(
            'document_id', v_link.document_id,
            'link_type', v_link.link_type,
            'page_range', v_link.page_range,
            'description', v_link.description,
            'artifact_type', v_link.artifact_type,
            'file_path', v_link.file_path
        );
    END LOOP;

    -- Also collect evidence from task assertions
    FOR v_link IN
        SELECT
            el.document_id,
            el.link_type,
            el.page_range,
            el.description,
            a.artifact_type,
            a.file_path,
            ta.assertion_type
        FROM task_assertions ta
        JOIN evidence_links el ON el.source_type = 'assertion' AND el.source_id = ta.id
        LEFT JOIN audit_artifacts a ON a.id = el.document_id
        WHERE ta.task_id = p_task_id
        ORDER BY el.linked_at
    LOOP
        v_chain := v_chain || jsonb_build_object(
            'document_id', v_link.document_id,
            'link_type', v_link.link_type,
            'page_range', v_link.page_range,
            'description', v_link.description,
            'artifact_type', v_link.artifact_type,
            'file_path', v_link.file_path,
            'assertion_type', v_link.assertion_type
        );
    END LOOP;

    RETURN v_chain;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE evidence_links IS 'Many-to-many links between audit entities (tasks, assertions, exceptions) and evidence documents';
COMMENT ON TABLE evidence_chain IS 'Complete evidence trails from source documents to final workpapers';
COMMENT ON COLUMN evidence_links.source_type IS 'Type of source entity: task, workpaper, assertion, exception';
COMMENT ON COLUMN evidence_links.link_type IS 'Relationship type: supporting, referenced, generated';
COMMENT ON COLUMN evidence_links.page_range IS 'Specific page references within the document';
COMMENT ON COLUMN evidence_chain.chain_path IS 'JSONB array of ordered document/entity references forming the chain';
COMMENT ON FUNCTION get_evidence_for_source(VARCHAR, UUID) IS 'Gets all evidence documents linked to a source entity';
COMMENT ON FUNCTION get_document_references(UUID) IS 'Gets all entities that reference a specific document';
COMMENT ON FUNCTION validate_evidence_chain(UUID) IS 'Validates completeness of an evidence chain';
COMMENT ON FUNCTION build_task_evidence_chain(UUID) IS 'Builds complete evidence chain for a task including assertions';
