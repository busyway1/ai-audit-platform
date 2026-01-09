/**
 * HITL (Human-in-the-Loop) Type Definitions
 *
 * Types for the HITL request system that allows AI agents to request
 * human intervention for critical decisions, approvals, and clarifications.
 */

/**
 * Types of HITL requests that AI agents can create
 */
export type HITLRequestType =
  | 'agent_completion_review'     // Review of agent's completed work
  | 'critical_decision'           // Decision with significant business impact
  | 'task_assignment_approval'    // Approval for task delegation
  | 'final_report_approval'       // Sign-off on final deliverables
  | 'mid_conversation_query';     // Clarification needed during task execution

/**
 * Priority levels for HITL requests
 */
export type HITLPriority = 'low' | 'medium' | 'high' | 'critical';

/**
 * Status of an HITL request
 */
export type HITLStatus = 'pending' | 'approved' | 'rejected' | 'expired';

/**
 * Agent roles that can create HITL requests
 */
export type RequesterAgent = 'partner' | 'manager' | 'staff';

/**
 * Response options that can be provided for an HITL request
 */
export interface HITLResponseOption {
  id: string;
  label: string;
  icon?: string;
  variant?: 'default' | 'primary' | 'destructive' | 'outline';
}

/**
 * Context information for an HITL request
 */
export interface HITLContext {
  /** Related task information */
  task?: {
    id: string;
    title: string;
    status: string;
  };
  /** Related financial data */
  financialData?: {
    amount?: number;
    currency?: string;
    account?: string;
  };
  /** Audit procedure details */
  auditProcedure?: {
    name: string;
    phase: string;
    riskLevel: string;
  };
  /** Previous agent messages related to this request */
  relatedMessages?: string[];
  /** Any additional context data */
  [key: string]: unknown;
}

/**
 * Main HITL Request interface for chat interface components
 */
export interface HITLRequest {
  /** Unique identifier for the request */
  id: string;
  /** Type of HITL request */
  request_type: HITLRequestType;
  /** Priority level */
  priority: HITLPriority;
  /** Current status */
  status: HITLStatus;
  /** Agent that created the request */
  requester_agent: RequesterAgent;
  /** Display title */
  title: string;
  /** Detailed description */
  description: string;
  /** Additional context object */
  context?: HITLContext;
  /** Predefined response options */
  options?: string[];
  /** Deadline for response (ISO date string) */
  deadline?: string;
  /** Project ID */
  project_id?: string;
  /** Task ID */
  task_id?: string;
  /** Conversation ID */
  conversation_id?: string;
  /** User assigned to respond */
  assigned_to?: string;
  /** Response provided */
  response?: string | null;
  /** User who responded */
  responded_by?: string | null;
  /** When response was provided */
  responded_at?: string | null;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Creation timestamp */
  created_at: string;
  /** Last update timestamp */
  updated_at: string;
}

/**
 * Props for the HITLRequestCard component (chat interface version)
 */
export interface HITLRequestCardProps {
  /** The HITL request to display */
  request: {
    id: string;
    request_type: HITLRequestType;
    priority: HITLPriority;
    requester_agent: RequesterAgent;
    title: string;
    description: string;
    context?: HITLContext;
    options?: string[];
    deadline?: string;
    status?: HITLStatus;
  };
  /** Callback when user responds to the request */
  onRespond: (requestId: string, response: string) => void;
  /** Whether a response is being submitted */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Utility functions for HITL components
 */

/**
 * Get display label for request type
 */
export function getRequestTypeLabel(type: HITLRequestType): string {
  const labels: Record<HITLRequestType, string> = {
    agent_completion_review: 'Agent Completion Review',
    critical_decision: 'Critical Decision',
    task_assignment_approval: 'Task Assignment Approval',
    final_report_approval: 'Final Report Approval',
    mid_conversation_query: 'Clarification Needed',
  };
  return labels[type];
}

/**
 * Get Korean display label for request type
 */
export function getRequestTypeLabelKo(type: HITLRequestType): string {
  const labels: Record<HITLRequestType, string> = {
    agent_completion_review: '에이전트 완료 검토',
    critical_decision: '중요 결정',
    task_assignment_approval: '업무 배정 승인',
    final_report_approval: '최종 보고서 승인',
    mid_conversation_query: '추가 확인 필요',
  };
  return labels[type];
}

/**
 * Get display label for agent role
 */
export function getAgentRoleLabel(role: RequesterAgent): string {
  const labels: Record<RequesterAgent, string> = {
    partner: 'Partner',
    manager: 'Manager',
    staff: 'Staff',
  };
  return labels[role];
}

/**
 * Get priority configuration for styling
 */
export function getPriorityConfig(priority: HITLPriority): {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  iconColor: string;
} {
  const configs: Record<HITLPriority, {
    label: string;
    bgColor: string;
    textColor: string;
    borderColor: string;
    iconColor: string;
  }> = {
    critical: {
      label: 'Critical',
      bgColor: 'bg-red-50',
      textColor: 'text-red-700',
      borderColor: 'border-red-200',
      iconColor: 'text-red-600',
    },
    high: {
      label: 'High',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-700',
      borderColor: 'border-orange-200',
      iconColor: 'text-orange-600',
    },
    medium: {
      label: 'Medium',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-700',
      borderColor: 'border-yellow-200',
      iconColor: 'text-yellow-600',
    },
    low: {
      label: 'Low',
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
      iconColor: 'text-gray-500',
    },
  };
  return configs[priority];
}

/**
 * Format deadline for display
 */
export function formatDeadline(deadline: string): string {
  const deadlineDate = new Date(deadline);
  const now = new Date();
  const diffMs = deadlineDate.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMs < 0) {
    return 'Overdue';
  } else if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins}m left`;
  } else if (diffHours < 24) {
    return `${diffHours}h left`;
  } else {
    return `${diffDays}d left`;
  }
}

/**
 * Check if deadline is urgent (less than 2 hours)
 */
export function isDeadlineUrgent(deadline: string): boolean {
  const deadlineDate = new Date(deadline);
  const now = new Date();
  const diffMs = deadlineDate.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  return diffHours < 2 && diffHours >= 0;
}

/**
 * Check if deadline has passed
 */
export function isDeadlinePassed(deadline: string): boolean {
  const deadlineDate = new Date(deadline);
  const now = new Date();
  return deadlineDate.getTime() < now.getTime();
}
