/**
 * E2E Test Data Fixtures
 *
 * Provides mock audit data for testing backend-frontend integration.
 * All data is designed to be realistic but non-sensitive for testing purposes.
 */

/**
 * Sample audit projects for testing
 */
export const SAMPLE_PROJECTS = {
  smallCompany: {
    project_name: 'E2E Test - Small Company Audit 2024',
    client_name: 'Acme Corp',
    audit_type: 'financial',
    fiscal_year_end: '2024-12-31',
    expected_materiality: 50000,
  },
  mediumCompany: {
    project_name: 'E2E Test - Medium Company Audit 2024',
    client_name: 'TechStart Inc',
    audit_type: 'compliance',
    fiscal_year_end: '2024-12-31',
    expected_materiality: 250000,
  },
  largeCompany: {
    project_name: 'E2E Test - Large Company Audit 2024',
    client_name: 'Global Enterprises Ltd',
    audit_type: 'integrated',
    fiscal_year_end: '2024-12-31',
    expected_materiality: 1000000,
  },
};

/**
 * Sample financial statements for testing
 */
export const SAMPLE_FINANCIAL_STATEMENTS = {
  balanceSheet: {
    assets: {
      current: {
        cash: 500000,
        accounts_receivable: 300000,
        inventory: 200000,
      },
      non_current: {
        property_plant_equipment: 1500000,
        intangible_assets: 250000,
      },
    },
    liabilities: {
      current: {
        accounts_payable: 200000,
        short_term_debt: 100000,
      },
      non_current: {
        long_term_debt: 800000,
      },
    },
    equity: {
      common_stock: 1000000,
      retained_earnings: 650000,
    },
  },
  incomeStatement: {
    revenue: 2500000,
    cost_of_goods_sold: 1500000,
    operating_expenses: 600000,
    net_income: 400000,
  },
};

/**
 * Sample audit tasks for testing
 */
export const SAMPLE_TASKS = {
  planning: {
    task_id: 'task_planning_001',
    title: 'Audit Planning and Risk Assessment',
    description: 'Develop comprehensive audit plan and assess client risks',
    status: 'pending',
    priority: 'high',
    assigned_to: 'partner',
  },
  fieldwork: {
    task_id: 'task_fieldwork_001',
    title: 'Revenue Testing - Sample Selection',
    description: 'Select revenue samples for substantive testing',
    status: 'in_progress',
    priority: 'medium',
    assigned_to: 'staff',
  },
  review: {
    task_id: 'task_review_001',
    title: 'Workpaper Review - Revenue Section',
    description: 'Review completed revenue testing workpapers',
    status: 'pending_approval',
    priority: 'medium',
    assigned_to: 'manager',
  },
};

/**
 * Sample audit issues for testing
 */
export const SAMPLE_ISSUES = {
  controlDeficiency: {
    issue_id: 'issue_001',
    title: 'Segregation of Duties Weakness',
    description: 'Same employee approves and processes payments',
    severity: 'moderate',
    status: 'open',
    category: 'internal_controls',
  },
  materialMisstatement: {
    issue_id: 'issue_002',
    title: 'Revenue Recognition Timing',
    description: 'Revenue recognized before delivery in some cases',
    severity: 'high',
    status: 'open',
    category: 'financial_reporting',
  },
};

/**
 * Sample engagement team for testing
 */
export const SAMPLE_ENGAGEMENT_TEAM = {
  partner: {
    id: 'partner_001',
    name: 'Sarah Johnson',
    role: 'Engagement Partner',
    email: 'sarah.johnson@test.audit',
  },
  manager: {
    id: 'manager_001',
    name: 'Michael Chen',
    role: 'Audit Manager',
    email: 'michael.chen@test.audit',
  },
  staff: [
    {
      id: 'staff_001',
      name: 'Emily Rodriguez',
      role: 'Senior Auditor',
      email: 'emily.rodriguez@test.audit',
    },
    {
      id: 'staff_002',
      name: 'David Kim',
      role: 'Staff Auditor',
      email: 'david.kim@test.audit',
    },
  ],
};

/**
 * Sample SSE events for testing stream functionality
 */
export const SAMPLE_SSE_EVENTS = {
  taskStarted: {
    event: 'task_started',
    data: {
      task_id: 'task_001',
      timestamp: new Date().toISOString(),
      message: 'Task processing started',
    },
  },
  agentMessage: {
    event: 'agent_message',
    data: {
      agent: 'partner',
      message: 'Analyzing audit risk factors...',
      timestamp: new Date().toISOString(),
    },
  },
  taskCompleted: {
    event: 'task_completed',
    data: {
      task_id: 'task_001',
      timestamp: new Date().toISOString(),
      result: 'success',
    },
  },
};

/**
 * Helper to generate unique test project names
 */
export function generateTestProjectName(prefix: string = 'E2E Test'): string {
  const timestamp = new Date().getTime();
  return `${prefix} - ${timestamp}`;
}

/**
 * Helper to generate unique task IDs
 */
export function generateTaskId(prefix: string = 'task'): string {
  const timestamp = new Date().getTime();
  const random = Math.floor(Math.random() * 1000);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * Complete test scenario data
 */
export const TEST_SCENARIOS = {
  quickHealthCheck: {
    name: 'Quick Health Check',
    description: 'Verify both servers are running and responsive',
  },
  basicProjectCreation: {
    name: 'Basic Project Creation',
    project: SAMPLE_PROJECTS.smallCompany,
    expected_duration: 5000, // 5 seconds
  },
  fullAuditWorkflow: {
    name: 'Full Audit Workflow',
    project: SAMPLE_PROJECTS.mediumCompany,
    tasks: [SAMPLE_TASKS.planning, SAMPLE_TASKS.fieldwork, SAMPLE_TASKS.review],
    expected_duration: 30000, // 30 seconds
  },
};
