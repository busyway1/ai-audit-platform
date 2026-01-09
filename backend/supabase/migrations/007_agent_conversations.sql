-- AI Audit Platform - Agent Conversations Table
-- Migration: 007_agent_conversations.sql
-- Description: Store all agent-to-agent conversations for audit trail and debugging

-- ============================================================================
-- TABLE: AGENT_CONVERSATIONS
-- ============================================================================
-- Comprehensive logging of all inter-agent communications in the audit workflow

CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES audit_projects(id) ON DELETE CASCADE,
    hierarchy_id UUID REFERENCES audit_hierarchy(id) ON DELETE SET NULL,
    task_id UUID REFERENCES audit_tasks(id) ON DELETE SET NULL,
    -- Message routing
    from_agent VARCHAR(100) NOT NULL,     -- Sender agent (e.g., "Partner", "Manager", "Staff:Excel")
    to_agent VARCHAR(100) NOT NULL,       -- Recipient agent (can be "broadcast" for multi-agent)
    -- Message content
    message_type VARCHAR(50) NOT NULL CHECK (message_type IN (
        'instruction',    -- Task assignment or directive
        'response',       -- Task completion or status update
        'question',       -- Clarification request
        'answer',         -- Response to question
        'error',          -- Error notification
        'escalation',     -- Issue escalation to higher authority
        'feedback',       -- Performance or quality feedback
        'tool_use'        -- Tool invocation and result
    )),
    content TEXT NOT NULL,                -- Message content
    -- Context and threading
    parent_message_id UUID REFERENCES agent_conversations(id) ON DELETE SET NULL,
    conversation_thread_id UUID,          -- Groups related messages into a thread
    -- Tool usage tracking (for message_type = 'tool_use')
    tool_name VARCHAR(100),               -- Name of tool invoked
    tool_input JSONB,                     -- Tool input parameters
    tool_output JSONB,                    -- Tool output/result
    tool_duration_ms INT,                 -- Tool execution duration
    -- Timing
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    -- Metadata
    metadata JSONB DEFAULT '{}',          -- Additional context (tokens, model, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for AGENT_CONVERSATIONS
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS ix_conv_project_timestamp ON agent_conversations(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_conv_hierarchy ON agent_conversations(hierarchy_id);
CREATE INDEX IF NOT EXISTS ix_conv_task ON agent_conversations(task_id);
CREATE INDEX IF NOT EXISTS ix_conv_from_agent ON agent_conversations(from_agent);
CREATE INDEX IF NOT EXISTS ix_conv_to_agent ON agent_conversations(to_agent);
CREATE INDEX IF NOT EXISTS ix_conv_message_type ON agent_conversations(message_type);

-- Threading indexes
CREATE INDEX IF NOT EXISTS ix_conv_parent ON agent_conversations(parent_message_id);
CREATE INDEX IF NOT EXISTS ix_conv_thread ON agent_conversations(conversation_thread_id);

-- Tool usage tracking
CREATE INDEX IF NOT EXISTS ix_conv_tool_name ON agent_conversations(tool_name) WHERE tool_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_conv_tool_use ON agent_conversations(message_type) WHERE message_type = 'tool_use';

-- Time-based queries
CREATE INDEX IF NOT EXISTS ix_conv_timestamp ON agent_conversations(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_conv_created ON agent_conversations(created_at DESC);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS ix_conv_tool_input ON agent_conversations USING GIN (tool_input);
CREATE INDEX IF NOT EXISTS ix_conv_metadata ON agent_conversations USING GIN (metadata);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE agent_conversations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see conversations from their projects
CREATE POLICY "Users see agent_conversations from own projects"
ON agent_conversations FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = agent_conversations.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Policy: Users can insert conversations for their projects
CREATE POLICY "Users insert agent_conversations for own projects"
ON agent_conversations FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM audit_projects p
        WHERE p.id = agent_conversations.project_id
        AND (
            auth.uid()::text = (p.metadata->>'created_by')
            OR auth.jwt()->>'role' = 'admin'
        )
    )
);

-- Note: Updates and deletes typically not allowed for audit trail integrity
-- If needed, add policies with appropriate conditions

-- ============================================================================
-- REALTIME PUBLICATION
-- ============================================================================
-- Enable Realtime for live conversation streaming in frontend

ALTER PUBLICATION supabase_realtime ADD TABLE agent_conversations;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get conversation thread
CREATE OR REPLACE FUNCTION get_conversation_thread(p_thread_id UUID)
RETURNS TABLE (
    id UUID,
    from_agent VARCHAR(100),
    to_agent VARCHAR(100),
    message_type VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMPTZ,
    parent_message_id UUID,
    depth INT
) AS $$
WITH RECURSIVE thread AS (
    -- Base case: root messages in thread
    SELECT
        ac.id,
        ac.from_agent,
        ac.to_agent,
        ac.message_type,
        ac.content,
        ac.timestamp,
        ac.parent_message_id,
        0 as depth
    FROM agent_conversations ac
    WHERE ac.conversation_thread_id = p_thread_id
        AND ac.parent_message_id IS NULL

    UNION ALL

    -- Recursive case: replies
    SELECT
        ac.id,
        ac.from_agent,
        ac.to_agent,
        ac.message_type,
        ac.content,
        ac.timestamp,
        ac.parent_message_id,
        t.depth + 1
    FROM agent_conversations ac
    JOIN thread t ON ac.parent_message_id = t.id
)
SELECT * FROM thread
ORDER BY timestamp ASC;
$$ LANGUAGE SQL STABLE;

-- Function to get agent activity summary for a project
CREATE OR REPLACE FUNCTION get_agent_activity_summary(p_project_id UUID)
RETURNS TABLE (
    agent_name VARCHAR(100),
    messages_sent BIGINT,
    messages_received BIGINT,
    tools_used BIGINT,
    errors_count BIGINT,
    escalations_count BIGINT,
    avg_response_time_ms NUMERIC
) AS $$
WITH sent AS (
    SELECT
        from_agent,
        COUNT(*) as messages_sent,
        COUNT(*) FILTER (WHERE message_type = 'tool_use') as tools_used,
        COUNT(*) FILTER (WHERE message_type = 'error') as errors_count,
        COUNT(*) FILTER (WHERE message_type = 'escalation') as escalations_count
    FROM agent_conversations
    WHERE project_id = p_project_id
    GROUP BY from_agent
),
received AS (
    SELECT
        to_agent,
        COUNT(*) as messages_received
    FROM agent_conversations
    WHERE project_id = p_project_id
    GROUP BY to_agent
),
response_times AS (
    SELECT
        ac2.from_agent,
        AVG(EXTRACT(EPOCH FROM (ac2.timestamp - ac1.timestamp)) * 1000)::NUMERIC as avg_response_time_ms
    FROM agent_conversations ac1
    JOIN agent_conversations ac2 ON ac2.parent_message_id = ac1.id
    WHERE ac1.project_id = p_project_id
    GROUP BY ac2.from_agent
)
SELECT
    COALESCE(s.from_agent, r.to_agent) as agent_name,
    COALESCE(s.messages_sent, 0) as messages_sent,
    COALESCE(r.messages_received, 0) as messages_received,
    COALESCE(s.tools_used, 0) as tools_used,
    COALESCE(s.errors_count, 0) as errors_count,
    COALESCE(s.escalations_count, 0) as escalations_count,
    ROUND(rt.avg_response_time_ms, 2) as avg_response_time_ms
FROM sent s
FULL OUTER JOIN received r ON s.from_agent = r.to_agent
LEFT JOIN response_times rt ON COALESCE(s.from_agent, r.to_agent) = rt.from_agent
ORDER BY messages_sent DESC NULLS LAST;
$$ LANGUAGE SQL STABLE;

-- Function to get tool usage statistics
CREATE OR REPLACE FUNCTION get_tool_usage_stats(p_project_id UUID)
RETURNS TABLE (
    tool_name VARCHAR(100),
    usage_count BIGINT,
    success_count BIGINT,
    error_count BIGINT,
    avg_duration_ms NUMERIC,
    min_duration_ms INT,
    max_duration_ms INT
) AS $$
SELECT
    tool_name,
    COUNT(*) as usage_count,
    COUNT(*) FILTER (WHERE NOT (tool_output ? 'error')) as success_count,
    COUNT(*) FILTER (WHERE tool_output ? 'error') as error_count,
    ROUND(AVG(tool_duration_ms)::NUMERIC, 2) as avg_duration_ms,
    MIN(tool_duration_ms) as min_duration_ms,
    MAX(tool_duration_ms) as max_duration_ms
FROM agent_conversations
WHERE project_id = p_project_id
    AND message_type = 'tool_use'
    AND tool_name IS NOT NULL
GROUP BY tool_name
ORDER BY usage_count DESC;
$$ LANGUAGE SQL STABLE;

-- Function to get recent conversation history for a task
CREATE OR REPLACE FUNCTION get_task_conversation_history(
    p_task_id UUID,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    from_agent VARCHAR(100),
    to_agent VARCHAR(100),
    message_type VARCHAR(50),
    content TEXT,
    tool_name VARCHAR(100),
    timestamp TIMESTAMPTZ
) AS $$
SELECT
    ac.id,
    ac.from_agent,
    ac.to_agent,
    ac.message_type,
    ac.content,
    ac.tool_name,
    ac.timestamp
FROM agent_conversations ac
WHERE ac.task_id = p_task_id
ORDER BY ac.timestamp DESC
LIMIT p_limit;
$$ LANGUAGE SQL STABLE;

-- Function to search conversations by content
CREATE OR REPLACE FUNCTION search_conversations(
    p_project_id UUID,
    p_search_term TEXT,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    from_agent VARCHAR(100),
    to_agent VARCHAR(100),
    message_type VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMPTZ,
    task_id UUID,
    relevance REAL
) AS $$
SELECT
    ac.id,
    ac.from_agent,
    ac.to_agent,
    ac.message_type,
    ac.content,
    ac.timestamp,
    ac.task_id,
    ts_rank(to_tsvector('english', ac.content), plainto_tsquery('english', p_search_term)) as relevance
FROM agent_conversations ac
WHERE ac.project_id = p_project_id
    AND to_tsvector('english', ac.content) @@ plainto_tsquery('english', p_search_term)
ORDER BY relevance DESC, ac.timestamp DESC
LIMIT p_limit;
$$ LANGUAGE SQL STABLE;

-- Create text search index for full-text search
CREATE INDEX IF NOT EXISTS ix_conv_content_search
ON agent_conversations USING GIN (to_tsvector('english', content));

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE agent_conversations IS 'Comprehensive logging of all inter-agent communications for audit trail';
COMMENT ON COLUMN agent_conversations.from_agent IS 'Sender agent identifier (e.g., Partner, Manager, Staff:Excel)';
COMMENT ON COLUMN agent_conversations.to_agent IS 'Recipient agent identifier (can be broadcast for multi-agent)';
COMMENT ON COLUMN agent_conversations.message_type IS 'Message type: instruction, response, question, answer, error, escalation, feedback, tool_use';
COMMENT ON COLUMN agent_conversations.conversation_thread_id IS 'Groups related messages into a conversation thread';
COMMENT ON COLUMN agent_conversations.tool_name IS 'Name of tool invoked (for message_type=tool_use)';
COMMENT ON COLUMN agent_conversations.tool_duration_ms IS 'Tool execution duration in milliseconds';
COMMENT ON FUNCTION get_conversation_thread(UUID) IS 'Returns all messages in a conversation thread with threading depth';
COMMENT ON FUNCTION get_agent_activity_summary(UUID) IS 'Returns activity metrics for each agent in a project';
COMMENT ON FUNCTION get_tool_usage_stats(UUID) IS 'Returns tool usage statistics for a project';
COMMENT ON FUNCTION get_task_conversation_history(UUID, INT) IS 'Returns recent conversation history for a specific task';
COMMENT ON FUNCTION search_conversations(UUID, TEXT, INT) IS 'Full-text search across conversation content';
