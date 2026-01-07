/**
 * Mock Audit Data for E2E Testing
 *
 * Provides consistent test data for backend-frontend integration tests.
 * Includes mock client info, audit responses, and expected agent behaviors.
 *
 * @module e2e/fixtures/mock-audit-data
 */

import type { AuditProject, AuditTask, AgentMessage } from '../../src/app/types/supabase';

/**
 * Mock Client Information
 */
export const mockClientInfo = {
  clientName: 'Acme Corporation',
  fiscalYear: 2024,
  overallMateriality: 1000000,
};

export const mockClientInfo2 = {
  clientName: 'Tech Startup Inc',
  fiscalYear: 2024,
  overallMateriality: 500000,
};

/**
 * Mock Thread IDs (generated from client info)
 */
export const mockThreadId = `project-${mockClientInfo.clientName.toLowerCase().replace(/\s+/g, '-')}-${mockClientInfo.fiscalYear}`;
export const mockThreadId2 = `project-${mockClientInfo2.clientName.toLowerCase().replace(/\s+/g, '-')}-${mockClientInfo2.fiscalYear}`;

/**
 * Mock Audit Project (expected from backend)
 */
export const mockAuditProject: Partial<AuditProject> = {
  client_name: mockClientInfo.clientName,
  fiscal_year: mockClientInfo.fiscalYear,
  overall_materiality: mockClientInfo.overallMateriality,
  status: 'Planning',
  metadata: {
    thread_id: mockThreadId,
  },
};

/**
 * Mock Audit Tasks (expected from Partner agent)
 */
export const mockAuditTasks: Partial<AuditTask>[] = [
  {
    thread_id: mockThreadId,
    category: 'Revenue Recognition',
    status: 'Pending',
    risk_score: 8.5,
    assignees: ['auditor-1'],
    metadata: {
      description: 'Perform substantive testing on revenue transactions',
      account: 'Sales Revenue',
    },
  },
  {
    thread_id: mockThreadId,
    category: 'Inventory Valuation',
    status: 'Pending',
    risk_score: 7.2,
    assignees: ['auditor-2'],
    metadata: {
      description: 'Test inventory count and valuation methods',
      account: 'Inventory',
    },
  },
  {
    thread_id: mockThreadId,
    category: 'Accounts Receivable',
    status: 'Pending',
    risk_score: 6.8,
    assignees: ['auditor-3'],
    metadata: {
      description: 'Verify receivables aging and collectibility',
      account: 'Accounts Receivable',
    },
  },
];

/**
 * Mock Agent Messages (expected from SSE stream)
 */
export const mockAgentMessages: Partial<AgentMessage>[] = [
  {
    agent_role: 'partner',
    content: 'Analyzing audit scope for Acme Corporation (FY2024)',
    message_type: 'instruction',
    metadata: {
      step: 'planning',
    },
  },
  {
    agent_role: 'partner',
    content: 'Identified 3 high-risk areas requiring substantive testing',
    message_type: 'response',
    metadata: {
      step: 'risk-assessment',
    },
  },
  {
    agent_role: 'manager',
    content: 'Assigning tasks to audit staff based on risk scores',
    message_type: 'instruction',
    metadata: {
      step: 'task-assignment',
    },
  },
  {
    agent_role: 'auditor',
    content: 'Performing substantive testing on revenue transactions',
    message_type: 'tool-use',
    metadata: {
      tool: 'financial_analyzer',
      step: 'execution',
    },
  },
  {
    agent_role: 'auditor',
    content: 'Completed revenue testing. No material misstatements detected.',
    message_type: 'response',
    metadata: {
      step: 'completion',
    },
  },
];

/**
 * Mock API Responses
 */
export const mockStartAuditResponse = {
  status: 'success',
  thread_id: mockThreadId,
  next_action: 'await_approval',
  message: `Audit project created for ${mockClientInfo.clientName} (FY${mockClientInfo.fiscalYear})`,
};

export const mockApprovalResponse = {
  status: 'resumed',
  thread_id: mockThreadId,
  task_status: 'In-Progress',
  message: 'Task approval processed. Workflow resumed with status: In-Progress',
};

/**
 * Mock Task Status Updates (Supabase Realtime)
 */
export const mockTaskStatusUpdates = [
  {
    id: 'task-1',
    status: 'Pending' as const,
    timestamp: new Date().toISOString(),
  },
  {
    id: 'task-1',
    status: 'In-Progress' as const,
    timestamp: new Date(Date.now() + 1000).toISOString(),
  },
  {
    id: 'task-1',
    status: 'Review-Required' as const,
    timestamp: new Date(Date.now() + 2000).toISOString(),
  },
  {
    id: 'task-1',
    status: 'Completed' as const,
    timestamp: new Date(Date.now() + 3000).toISOString(),
  },
];

/**
 * Expected Partner Agent Behavior
 */
export const expectedPartnerBehavior = {
  tasksCreated: 3,
  minRiskScore: 6.0,
  maxRiskScore: 10.0,
  statusAfterCreation: 'Pending' as const,
  requiresApproval: true,
};

/**
 * Expected Manager Agent Behavior
 */
export const expectedManagerBehavior = {
  spawnsStaffAgents: true,
  assignmentDelay: 500, // ms
  statusAfterAssignment: 'In-Progress' as const,
};

/**
 * Mock Excel File Data
 */
export const mockExcelData = {
  fileName: 'trial_balance.xlsx',
  content: 'base64-encoded-excel-content',
  accounts: [
    { account: 'Sales Revenue', amount: 5000000 },
    { account: 'Inventory', amount: 2000000 },
    { account: 'Accounts Receivable', amount: 1500000 },
  ],
};

/**
 * Helper: Generate unique thread ID for test
 */
export function generateTestThreadId(testName: string): string {
  const timestamp = Date.now();
  return `test-${testName.toLowerCase().replace(/\s+/g, '-')}-${timestamp}`;
}

/**
 * Helper: Wait for agent message with timeout
 */
export async function waitForAgentMessage(
  role: string,
  timeout: number = 5000
): Promise<void> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timeout waiting for agent message from ${role}`);
}
