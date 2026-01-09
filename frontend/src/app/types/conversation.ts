/**
 * Agent conversation types for visibility system
 *
 * These types support the conversation visibility layer that allows
 * tracking and displaying agent-to-agent communications during audit tasks.
 */

/**
 * Types of messages exchanged between agents
 */
export type MessageType =
  | 'instruction'
  | 'response'
  | 'question'
  | 'answer'
  | 'error'
  | 'escalation'
  | 'feedback'
  | 'tool_use';

/**
 * Metadata attached to conversation messages for context and debugging
 */
export interface ConversationMetadata {
  /** Tool that was called (for tool_use messages) */
  toolCall?: string;
  /** File references involved in this message */
  fileRefs?: string[];
  /** Current loop attempt number (for ralph-wiggum tracking) */
  loopAttempt?: number;
  /** Strategy used in this attempt */
  strategyUsed?: string;
  /** Duration of the operation in milliseconds */
  duration?: number;
}

/**
 * A single conversation message between agents
 */
export interface AgentConversation {
  /** Unique identifier for the conversation message */
  id: string;
  /** Project this conversation belongs to */
  projectId: string;
  /** Optional hierarchy item this conversation is related to */
  hierarchyId?: string;
  /** Optional task this conversation is related to */
  taskId?: string;
  /** Agent that sent the message */
  fromAgent: string;
  /** Agent that received the message */
  toAgent: string;
  /** Type of message */
  messageType: MessageType;
  /** Message content */
  content: string;
  /** ISO timestamp of when the message was created */
  timestamp: string;
  /** Additional metadata for context */
  metadata?: ConversationMetadata;
}

/**
 * Filter criteria for querying conversations
 */
export interface ConversationFilter {
  /** Filter by hierarchy item */
  hierarchyId?: string;
  /** Filter by task */
  taskId?: string;
  /** Filter by agent types (e.g., 'partner', 'manager', 'staff') */
  agentTypes?: string[];
  /** Filter by message types */
  messageTypes?: MessageType[];
  /** Include error messages */
  includeErrors?: boolean;
  /** Start date for date range filter (ISO format) */
  startDate?: string;
  /** End date for date range filter (ISO format) */
  endDate?: string;
}

/**
 * Statistics about conversations for display in dashboards
 */
export interface ConversationStats {
  /** Total number of messages */
  totalMessages: number;
  /** Message count by agent */
  byAgent: Record<string, number>;
  /** Message count by type */
  byType: Record<MessageType, number>;
  /** Number of error messages */
  errorCount: number;
  /** Number of escalation messages */
  escalationCount: number;
}

// ============================================================================
// Ralph-wiggum Loop Types
// ============================================================================

/**
 * A single attempt in the ralph-wiggum loop recovery system
 */
export interface LoopAttempt {
  /** Sequential attempt number */
  attemptNumber: number;
  /** Strategy used in this attempt */
  strategy: string;
  /** Result of the attempt */
  result: 'success' | 'partial' | 'failure';
  /** Error message if attempt failed */
  error?: string;
  /** Duration of the attempt in milliseconds */
  duration: number;
}

/**
 * State of a ralph-wiggum loop recovery process
 */
export interface RalphLoopState {
  /** ID of the task being processed */
  taskId: string;
  /** Name of the agent in the loop */
  agentName: string;
  /** Maximum number of attempts allowed */
  maxAttempts: number;
  /** Current attempt number */
  currentAttempt: number;
  /** History of all attempts */
  attempts: LoopAttempt[];
  /** Current status of the loop recovery */
  status: 'running' | 'success' | 'hitl_required';
  /** Guidance provided by human if HITL was triggered */
  hitlGuidance?: string;
}

// ============================================================================
// HITL Types for Agent Loop Failure
// ============================================================================

/**
 * Suggested actions for resolving agent loop failures
 */
export type AgentLoopHITLAction =
  | 'provide_guidance'
  | 'skip_task'
  | 'manual_resolution'
  | 'change_approach';

/**
 * HITL request specifically for agent loop failures
 *
 * This is triggered when the ralph-wiggum system exhausts all automatic
 * recovery strategies and requires human intervention.
 */
export interface AgentLoopHITLRequest {
  /** Unique identifier for the request */
  id: string;
  /** Type of request (always 'agent_loop_failure' for this interface) */
  requestType: 'agent_loop_failure';
  /** ID of the task that triggered the loop failure */
  taskId: string;
  /** Name of the agent that failed */
  agentName: string;
  /** Number of attempts made before HITL */
  attemptsMade: number;
  /** List of strategies that were tried */
  strategiesTried: string[];
  /** Last error message encountered */
  lastError?: string;
  /** Full conversation log for context */
  conversationLog: AgentConversation[];
  /** Additional context data */
  context: Record<string, unknown>;
  /** Suggested actions for the human reviewer */
  suggestedActions: AgentLoopHITLAction[];
  /** Priority level of the request */
  priority: 'low' | 'medium' | 'high' | 'critical';
  /** ISO timestamp of when the request was created */
  createdAt: string;
}
