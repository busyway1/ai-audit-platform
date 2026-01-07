-- AI Audit Platform - Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Description: Create core tables for audit workflow with pgvector support

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable pgvector extension for RAG functionality
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE 1: AUDIT PROJECTS
-- ============================================================================

CREATE TABLE audit_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name TEXT NOT NULL,
    fiscal_year INT NOT NULL,
    overall_materiality NUMERIC(15, 2),
    status TEXT CHECK (status IN ('Planning', 'Execution', 'Review', 'Completed')) DEFAULT 'Planning',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for filtering by status and fiscal year
CREATE INDEX idx_projects_status ON audit_projects(status);
CREATE INDEX idx_projects_fiscal_year ON audit_projects(fiscal_year);

-- ============================================================================
-- TABLE 2: AUDIT TASKS
-- ============================================================================
-- Maps to LangGraph TaskState with critical thread_id for checkpoint tracking

CREATE TABLE audit_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES audit_projects(id) ON DELETE CASCADE,
    thread_id TEXT UNIQUE NOT NULL, -- CRITICAL: LangGraph thread_id mapping
    category TEXT NOT NULL, -- "Sales", "Inventory", "AR", "AP", etc.
    status TEXT CHECK (status IN ('Pending', 'In-Progress', 'Review-Required', 'Completed', 'Failed')) DEFAULT 'Pending',
    risk_score INT CHECK (risk_score BETWEEN 0 AND 100) DEFAULT 50,
    assignees JSONB DEFAULT '[]', -- Array of staff agent names
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tasks_project ON audit_tasks(project_id);
CREATE INDEX idx_tasks_thread ON audit_tasks(thread_id);
CREATE INDEX idx_tasks_status ON audit_tasks(status);
CREATE INDEX idx_tasks_category ON audit_tasks(category);

-- ============================================================================
-- TABLE 3: AGENT MESSAGES
-- ============================================================================
-- Stores LangGraph message history for chat UI and debugging

CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES audit_tasks(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL, -- "Partner", "Manager", "Staff:Excel", "Staff:RAG", "Staff:Vouch", "Staff:Writer"
    content TEXT NOT NULL,
    message_type TEXT CHECK (message_type IN ('instruction', 'response', 'tool-use', 'human-feedback')) DEFAULT 'response',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient message retrieval
CREATE INDEX idx_messages_task ON agent_messages(task_id);
CREATE INDEX idx_messages_created ON agent_messages(created_at DESC);
CREATE INDEX idx_messages_agent_role ON agent_messages(agent_role);

-- ============================================================================
-- TABLE 4: AUDIT ARTIFACTS
-- ============================================================================
-- Stores workpapers, Excel files, vouchers, and other audit evidence

CREATE TABLE audit_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES audit_tasks(id) ON DELETE CASCADE,
    artifact_type TEXT CHECK (artifact_type IN ('workpaper', 'excel', 'voucher', 'memo', 'report')) DEFAULT 'workpaper',
    file_path TEXT, -- Supabase Storage path (e.g., "artifacts/task-123/workpaper.pdf")
    content TEXT, -- Inline content for text-based artifacts
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for artifact retrieval
CREATE INDEX idx_artifacts_task ON audit_artifacts(task_id);
CREATE INDEX idx_artifacts_type ON audit_artifacts(artifact_type);

-- ============================================================================
-- TABLE 5: AUDIT STANDARDS (RAG Corpus)
-- ============================================================================
-- Hierarchical storage for K-IFRS and K-GAAS standards with pgvector embeddings

CREATE TABLE audit_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES audit_standards(id), -- For Parent-Child chunk hierarchy
    standard_type TEXT CHECK (standard_type IN ('K-IFRS', 'K-GAAS')) NOT NULL,
    section_number TEXT, -- e.g., "1115", "500"
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimension (or 3072 for text-embedding-3-large)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW Index for fast vector similarity search
-- m=16: connections per layer (higher = better recall, more memory)
-- ef_construction=64: build-time search depth (higher = better index quality, slower build)
CREATE INDEX idx_standards_embedding ON audit_standards
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Additional indexes for metadata filtering
CREATE INDEX idx_standards_type ON audit_standards(standard_type);
CREATE INDEX idx_standards_section ON audit_standards(section_number);
CREATE INDEX idx_standards_parent ON audit_standards(parent_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE audit_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_artifacts ENABLE ROW LEVEL SECURITY;
-- audit_standards: Public read access (no RLS needed for standards library)

-- Example policy: Users can only see projects they created
-- NOTE: Adjust based on actual auth strategy (e.g., auth.uid(), custom claims)
CREATE POLICY "Users see own projects"
ON audit_projects FOR SELECT
USING (
    auth.uid()::text = (metadata->>'created_by')
    OR
    auth.jwt()->>'role' = 'admin'
);

CREATE POLICY "Users update own projects"
ON audit_projects FOR UPDATE
USING (
    auth.uid()::text = (metadata->>'created_by')
    OR
    auth.jwt()->>'role' = 'admin'
);

CREATE POLICY "Users insert own projects"
ON audit_projects FOR INSERT
WITH CHECK (
    auth.uid()::text = (metadata->>'created_by')
);

-- Tasks inherit project permissions
CREATE POLICY "Users see tasks from own projects"
ON audit_tasks FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = audit_tasks.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Messages inherit task permissions
CREATE POLICY "Users see messages from own tasks"
ON agent_messages FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = agent_messages.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Artifacts inherit task permissions
CREATE POLICY "Users see artifacts from own tasks"
ON audit_artifacts FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_tasks t
        JOIN audit_projects p ON p.id = t.project_id
        WHERE t.id = audit_artifacts.task_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- ============================================================================
-- REALTIME PUBLICATION
-- ============================================================================
-- Enable Realtime for live updates in frontend

ALTER PUBLICATION supabase_realtime ADD TABLE audit_tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE agent_messages;

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_audit_projects_updated_at
BEFORE UPDATE ON audit_projects
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_tasks_updated_at
BEFORE UPDATE ON audit_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA (Optional - for development/testing)
-- ============================================================================

-- Uncomment for local development
-- INSERT INTO audit_standards (standard_type, section_number, title, content) VALUES
-- ('K-GAAS', '500', '감사증거', 'Audit evidence must be sufficient and appropriate...'),
-- ('K-IFRS', '1115', '고객과의 계약에서 생기는 수익', 'Revenue from contracts with customers...');

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE audit_projects IS 'Top-level audit engagement projects';
COMMENT ON TABLE audit_tasks IS 'Individual audit tasks mapped to LangGraph workflows via thread_id';
COMMENT ON TABLE agent_messages IS 'Message history from LangGraph agents for chat UI';
COMMENT ON TABLE audit_artifacts IS 'Audit evidence and workpapers';
COMMENT ON TABLE audit_standards IS 'RAG corpus for K-IFRS and K-GAAS standards with vector embeddings';

COMMENT ON COLUMN audit_tasks.thread_id IS 'CRITICAL: Maps to LangGraph checkpoint thread_id for workflow persistence';
COMMENT ON COLUMN audit_standards.embedding IS 'Vector embedding (1536-dim) for semantic search via pgvector';
