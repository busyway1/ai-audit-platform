// Core types for the audit platform

export type TaskStatus = 'not-started' | 'in-progress' | 'pending-review' | 'completed' | 'rejected';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type AgentRole = 'partner' | 'manager' | 'staff';
export type AuditPhase = 'planning' | 'risk-assessment' | 'controls-testing' | 'substantive-procedures' | 'completion';
export type IssueImpact = 'low' | 'medium' | 'high' | 'critical';
export type IssueStatus = 'open' | 'client-responded' | 'resolved' | 'waived';

export interface Agent {
  id: string;
  name: string;
  role: AgentRole;
  status: 'idle' | 'working' | 'waiting';
  currentTask?: string;
}

export interface Task {
  id: string;
  taskNumber: string;
  title: string;
  description: string;
  status: TaskStatus;
  phase: AuditPhase;
  accountCategory: string;
  businessProcess: string;
  assignedManager: string;
  assignedStaff: string[];
  progress: number;
  riskLevel: RiskLevel;
  requiresReview: boolean;
  dueDate: string;
  createdAt: string;
  completedAt?: string;
}

export interface AgentMessage {
  id: string;
  taskId: string;
  agentId: string;
  agentName: string;
  agentRole: AgentRole;
  content: string;
  timestamp: string;
  type: 'instruction' | 'response' | 'tool-use' | 'file-upload' | 'human-feedback';
  attachments?: {
    name: string;
    type: string;
    url?: string;
  }[];
}

export interface FinancialStatementItem {
  id: string;
  category: string;
  account: string;
  currentYear: number;
  priorYear: number;
  variance: number;
  variancePercent: number;
  taskCount: number;
  completedTasks: number;
  riskLevel: RiskLevel;
}

export interface RiskHeatmapItem {
  category: string;
  process: string;
  riskScore: number;
  riskLevel: RiskLevel;
  taskCount: number;
  completedTasks: number;
}

export interface EngagementMessage {
  id: string;
  sender: 'user' | 'partner-agent';
  content: string;
  timestamp: string;
  status?: 'pending-approval' | 'approved' | 'rejected';
  attachments?: {
    name: string;
    type: string;
  }[];
}

export interface Document {
  id: string;
  name: string;
  type: string;
  uploadedBy: string;
  uploadedAt: string;
  size: string;
  category: string;
  linkedTasks: string[];
}

export interface EngagementPlanSummary {
  clientName: string;
  fiscalYear: string;
  auditPeriod: {
    start: string;
    end: string;
  };
  materiality: {
    overall: number;
    performance: number;
    trivial: number;
  };
  keyAuditMatters: {
    id: string;
    matter: string;
    riskLevel: RiskLevel;
    response: string;
  }[];
  timeline: {
    phase: string;
    startDate: string;
    endDate: string;
    status: 'planned' | 'in-progress' | 'completed';
  }[];
  resources: {
    humanTeam: { name: string; role: string; allocation: string }[];
    aiAgents: { name: string; role: AgentRole; assignedTasks: number }[];
  };
  approvalStatus: 'draft' | 'pending-approval' | 'approved' | 'rejected';
  approvedBy?: string;
  approvedAt?: string;
}

export interface WorkingPaper {
  id: string;
  taskId: string;
  taskNumber: string;
  clientName: string;
  fiscalYear: string;
  accountCategory: string;
  preparedBy: string;
  preparedDate: string;
  reviewedBy?: string;
  reviewedDate?: string;
  signedOffBy?: string;
  signedOffDate?: string;
  purpose: string;
  procedures: string[];
  results: {
    description: string;
    value?: string;
    exception: boolean;
  }[];
  conclusion: string;
  conclusionType: 'satisfactory' | 'adjustment-required' | 'further-investigation';
  attachments: {
    name: string;
    type: string;
    url?: string;
  }[];
  version: number;
  status: 'draft' | 'prepared' | 'reviewed' | 'signed-off';
}

export interface Issue {
  id: string;
  taskId: string;
  taskNumber: string;
  title: string;
  description: string;
  accountCategory: string;
  impact: IssueImpact;
  status: IssueStatus;
  identifiedBy: string;
  identifiedDate: string;
  financialImpact?: number;
  clientResponse?: string;
  clientResponseDate?: string;
  resolution?: string;
  resolvedDate?: string;
  requiresAdjustment: boolean;
  includeInManagementLetter: boolean;
}

export interface AgentTool {
  id: string;
  name: string;
  description: string;
  category: 'data-extraction' | 'analysis' | 'communication' | 'integration' | 'verification';
  enabled: boolean;
  assignedAgents: string[];
  usageCount: number;
  lastUsed?: string;
  permissions: string[];
}

// Chat-First Interface Types
export type ChatSender = 'user' | 'ai' | 'system';

export interface ChatMessage {
  id: string;
  sender: ChatSender;
  content: string;
  timestamp: Date;
  streaming?: boolean;  // True while AI is still generating
  artifactId?: string;  // Link to artifact if this message created one
}

export type ArtifactType =
  | 'engagement-plan'
  | 'task-status'
  | 'issue-details'
  | 'financial-statements'
  | 'dashboard'
  | 'working-paper'
  | 'document';

export interface Artifact {
  id: string;
  type: ArtifactType;
  title: string;
  data: any;  // Type varies by artifact type
  createdAt: Date;
  updatedAt: Date;
  status: 'streaming' | 'complete' | 'error';
}

export interface ArtifactTab {
  id: string;
  artifact: Artifact;
  isPinned: boolean;
}

export type SplitLayout = 'none' | 'horizontal' | 'vertical';