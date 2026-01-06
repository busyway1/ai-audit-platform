import { 
  Task, 
  Agent, 
  AgentMessage, 
  FinancialStatementItem, 
  RiskHeatmapItem,
  EngagementMessage,
  Document,
  EngagementPlanSummary,
  WorkingPaper,
  Issue,
  AgentTool
} from '../types/audit';

export const agents: Agent[] = [
  {
    id: 'partner-001',
    name: 'Partner AI',
    role: 'partner',
    status: 'working',
    currentTask: 'Engagement Planning'
  },
  {
    id: 'manager-001',
    name: 'Revenue Cycle Manager',
    role: 'manager',
    status: 'working',
    currentTask: 'T-001'
  },
  {
    id: 'manager-002',
    name: 'Inventory Manager',
    role: 'manager',
    status: 'working',
    currentTask: 'T-015'
  },
  {
    id: 'manager-003',
    name: 'Cash Manager',
    role: 'manager',
    status: 'idle'
  },
  {
    id: 'staff-001',
    name: 'Confirmation Staff',
    role: 'staff',
    status: 'working',
    currentTask: 'T-001'
  },
  {
    id: 'staff-002',
    name: 'Sampling Staff',
    role: 'staff',
    status: 'working',
    currentTask: 'T-001'
  },
  {
    id: 'staff-003',
    name: 'Analytics Staff',
    role: 'staff',
    status: 'working',
    currentTask: 'T-015'
  },
  {
    id: 'staff-004',
    name: 'Document Review Staff',
    role: 'staff',
    status: 'idle'
  }
];

export const tasks: Task[] = [
  {
    id: 'T-001',
    taskNumber: 'T-001',
    title: '매출채권 조회서 발송 및 회수',
    description: '주요 매출채권에 대한 외부조회 절차 수행',
    status: 'pending-review',
    phase: 'substantive-procedures',
    accountCategory: 'Trade Receivables',
    businessProcess: 'Revenue Cycle',
    assignedManager: 'manager-001',
    assignedStaff: ['staff-001', 'staff-002'],
    progress: 85,
    riskLevel: 'high',
    requiresReview: true,
    dueDate: '2026-01-15',
    createdAt: '2026-01-02'
  },
  {
    id: 'T-002',
    taskNumber: 'T-002',
    title: '매출채권 연령분석',
    description: '매출채권 장기체류 분석 및 대손충당금 적정성 검토',
    status: 'in-progress',
    phase: 'substantive-procedures',
    accountCategory: 'Trade Receivables',
    businessProcess: 'Revenue Cycle',
    assignedManager: 'manager-001',
    assignedStaff: ['staff-002'],
    progress: 45,
    riskLevel: 'medium',
    requiresReview: false,
    dueDate: '2026-01-16',
    createdAt: '2026-01-03'
  },
  {
    id: 'T-003',
    taskNumber: 'T-003',
    title: '수익인식 정책 검토',
    description: 'IFRS 15 준수 여부 및 수익인식 시점 적정성 평가',
    status: 'completed',
    phase: 'substantive-procedures',
    accountCategory: 'Revenue',
    businessProcess: 'Revenue Cycle',
    assignedManager: 'manager-001',
    assignedStaff: ['staff-001'],
    progress: 100,
    riskLevel: 'high',
    requiresReview: false,
    dueDate: '2026-01-10',
    createdAt: '2026-01-01',
    completedAt: '2026-01-09'
  },
  {
    id: 'T-004',
    taskNumber: 'T-004',
    title: '매출 실증절차 - 표본추출',
    description: '매출거래 표본 선정 및 증빙 검토',
    status: 'in-progress',
    phase: 'substantive-procedures',
    accountCategory: 'Revenue',
    businessProcess: 'Revenue Cycle',
    assignedManager: 'manager-001',
    assignedStaff: ['staff-002', 'staff-003'],
    progress: 60,
    riskLevel: 'medium',
    requiresReview: false,
    dueDate: '2026-01-17',
    createdAt: '2026-01-04'
  },
  {
    id: 'T-015',
    taskNumber: 'T-015',
    title: '재고실사 참관 및 평가',
    description: '기말재고실사 참관 및 재고자산 평가절차',
    status: 'in-progress',
    phase: 'substantive-procedures',
    accountCategory: 'Inventory',
    businessProcess: 'Inventory & Production',
    assignedManager: 'manager-002',
    assignedStaff: ['staff-003', 'staff-004'],
    progress: 30,
    riskLevel: 'critical',
    requiresReview: true,
    dueDate: '2026-01-20',
    createdAt: '2026-01-05'
  },
  {
    id: 'T-016',
    taskNumber: 'T-016',
    title: '재고평가충당금 검토',
    description: '저가법 적용 적정성 및 평가충당금 계산 검증',
    status: 'not-started',
    phase: 'substantive-procedures',
    accountCategory: 'Inventory',
    businessProcess: 'Inventory & Production',
    assignedManager: 'manager-002',
    assignedStaff: ['staff-003'],
    progress: 0,
    riskLevel: 'high',
    requiresReview: false,
    dueDate: '2026-01-22',
    createdAt: '2026-01-05'
  },
  {
    id: 'T-030',
    taskNumber: 'T-030',
    title: '현금 및 현금성자산 실사',
    description: '기말 현금실사 및 은행잔액 확인',
    status: 'not-started',
    phase: 'substantive-procedures',
    accountCategory: 'Cash',
    businessProcess: 'Treasury',
    assignedManager: 'manager-003',
    assignedStaff: ['staff-001'],
    progress: 0,
    riskLevel: 'low',
    requiresReview: false,
    dueDate: '2026-01-12',
    createdAt: '2026-01-02'
  },
  {
    id: 'T-050',
    taskNumber: 'T-050',
    title: '매입채무 확인서 발송',
    description: '주요 매입채무에 대한 외부조회 절차',
    status: 'in-progress',
    phase: 'substantive-procedures',
    accountCategory: 'Trade Payables',
    businessProcess: 'Procurement',
    assignedManager: 'manager-001',
    assignedStaff: ['staff-001', 'staff-002'],
    progress: 50,
    riskLevel: 'medium',
    requiresReview: false,
    dueDate: '2026-01-18',
    createdAt: '2026-01-04'
  }
];

export const agentMessages: AgentMessage[] = [
  {
    id: 'msg-001',
    taskId: 'T-001',
    agentId: 'manager-001',
    agentName: 'Revenue Cycle Manager',
    agentRole: 'manager',
    content: '매출채권 조회서 발송 절차를 시작합니다. 전체 매출채권 중 상위 80% 커버리지를 목표로 샘플을 선정해주세요.',
    timestamp: '2026-01-06T09:00:00Z',
    type: 'instruction'
  },
  {
    id: 'msg-002',
    taskId: 'T-001',
    agentId: 'staff-002',
    agentName: 'Sampling Staff',
    agentRole: 'staff',
    content: '매출채권 원장 데이터를 분석하여 샘플링을 수행했습니다. 총 150개 거래처 중 45개를 선정했으며, 금액 기준 82% 커버리지를 달성했습니다.',
    timestamp: '2026-01-06T10:30:00Z',
    type: 'response',
    attachments: [
      {
        name: 'AR_Sampling_List.xlsx',
        type: 'spreadsheet'
      }
    ]
  },
  {
    id: 'msg-003',
    taskId: 'T-001',
    agentId: 'manager-001',
    agentName: 'Revenue Cycle Manager',
    agentRole: 'manager',
    content: '샘플 리스트를 검토했습니다. 상위 10개 거래처 중 2개가 누락되었습니다. 해당 거래처를 추가로 포함해주세요.',
    timestamp: '2026-01-06T11:00:00Z',
    type: 'instruction'
  },
  {
    id: 'msg-004',
    taskId: 'T-001',
    agentId: 'staff-002',
    agentName: 'Sampling Staff',
    agentRole: 'staff',
    content: '샘플 리스트를 업데이트했습니다. 총 47개 거래처로 확장되었으며, 커버리지는 85%입니다.',
    timestamp: '2026-01-06T11:45:00Z',
    type: 'response',
    attachments: [
      {
        name: 'AR_Sampling_List_v2.xlsx',
        type: 'spreadsheet'
      }
    ]
  },
  {
    id: 'msg-005',
    taskId: 'T-001',
    agentId: 'staff-001',
    agentName: 'Confirmation Staff',
    agentRole: 'staff',
    content: '조회서 초안을 작성했습니다. 이메일 발송 템플릿과 함께 준비되었습니다.',
    timestamp: '2026-01-06T14:00:00Z',
    type: 'tool-use',
    attachments: [
      {
        name: 'Confirmation_Template.docx',
        type: 'document'
      },
      {
        name: 'Email_Draft.txt',
        type: 'text'
      }
    ]
  },
  {
    id: 'msg-006',
    taskId: 'T-001',
    agentId: 'manager-001',
    agentName: 'Revenue Cycle Manager',
    agentRole: 'manager',
    content: '조회서 발송을 승인합니다. 2주 이내 회신을 목표로 하며, 미회신 건에 대해서는 추가 절차를 진행하겠습니다.',
    timestamp: '2026-01-06T15:00:00Z',
    type: 'instruction'
  },
  {
    id: 'msg-007',
    taskId: 'T-001',
    agentId: 'staff-001',
    agentName: 'Confirmation Staff',
    agentRole: 'staff',
    content: '47개 거래처에 조회서를 발송 완료했습니다. 현재까지 38개 회신 수신(81%), 9개 미회신 상태입니다.',
    timestamp: '2026-01-13T16:00:00Z',
    type: 'response'
  },
  {
    id: 'msg-008',
    taskId: 'T-001',
    agentId: 'human',
    agentName: 'Senior Auditor',
    agentRole: 'manager',
    content: '미회신 거래처 중 ABC Corporation과 XYZ Ltd.는 중요성이 높습니다. 전화 통화 후 재발송해주시고, 필요시 대체절차를 준비해주세요.',
    timestamp: '2026-01-13T17:30:00Z',
    type: 'human-feedback'
  }
];

export const financialStatementItems: FinancialStatementItem[] = [
  {
    id: 'fs-001',
    category: 'Assets',
    account: 'Cash and Cash Equivalents',
    currentYear: 12500000000,
    priorYear: 10800000000,
    variance: 1700000000,
    variancePercent: 15.7,
    taskCount: 2,
    completedTasks: 0,
    riskLevel: 'low'
  },
  {
    id: 'fs-002',
    category: 'Assets',
    account: 'Trade Receivables',
    currentYear: 25300000000,
    priorYear: 22100000000,
    variance: 3200000000,
    variancePercent: 14.5,
    taskCount: 4,
    completedTasks: 1,
    riskLevel: 'high'
  },
  {
    id: 'fs-003',
    category: 'Assets',
    account: 'Inventory',
    currentYear: 18700000000,
    priorYear: 16200000000,
    variance: 2500000000,
    variancePercent: 15.4,
    taskCount: 3,
    completedTasks: 0,
    riskLevel: 'critical'
  },
  {
    id: 'fs-004',
    category: 'Assets',
    account: 'Property, Plant & Equipment',
    currentYear: 45600000000,
    priorYear: 43800000000,
    variance: 1800000000,
    variancePercent: 4.1,
    taskCount: 5,
    completedTasks: 2,
    riskLevel: 'medium'
  },
  {
    id: 'fs-005',
    category: 'Liabilities',
    account: 'Trade Payables',
    currentYear: 15200000000,
    priorYear: 13900000000,
    variance: 1300000000,
    variancePercent: 9.4,
    taskCount: 2,
    completedTasks: 0,
    riskLevel: 'medium'
  },
  {
    id: 'fs-006',
    category: 'Liabilities',
    account: 'Long-term Debt',
    currentYear: 28500000000,
    priorYear: 25000000000,
    variance: 3500000000,
    variancePercent: 14.0,
    taskCount: 4,
    completedTasks: 1,
    riskLevel: 'high'
  },
  {
    id: 'fs-007',
    category: 'Equity',
    account: 'Share Capital',
    currentYear: 20000000000,
    priorYear: 20000000000,
    variance: 0,
    variancePercent: 0,
    taskCount: 1,
    completedTasks: 1,
    riskLevel: 'low'
  },
  {
    id: 'fs-008',
    category: 'Equity',
    account: 'Retained Earnings',
    currentYear: 38400000000,
    priorYear: 34000000000,
    variance: 4400000000,
    variancePercent: 12.9,
    taskCount: 2,
    completedTasks: 1,
    riskLevel: 'low'
  },
  {
    id: 'fs-009',
    category: 'Income',
    account: 'Revenue',
    currentYear: 95600000000,
    priorYear: 82300000000,
    variance: 13300000000,
    variancePercent: 16.2,
    taskCount: 8,
    completedTasks: 2,
    riskLevel: 'high'
  },
  {
    id: 'fs-010',
    category: 'Income',
    account: 'Cost of Sales',
    currentYear: 58400000000,
    priorYear: 50100000000,
    variance: 8300000000,
    variancePercent: 16.6,
    taskCount: 6,
    completedTasks: 1,
    riskLevel: 'medium'
  }
];

export const riskHeatmap: RiskHeatmapItem[] = [
  {
    category: 'Revenue',
    process: 'Revenue Recognition',
    riskScore: 85,
    riskLevel: 'critical',
    taskCount: 8,
    completedTasks: 2
  },
  {
    category: 'Trade Receivables',
    process: 'Credit Management',
    riskScore: 78,
    riskLevel: 'high',
    taskCount: 4,
    completedTasks: 1
  },
  {
    category: 'Inventory',
    process: 'Inventory Valuation',
    riskScore: 82,
    riskLevel: 'critical',
    taskCount: 3,
    completedTasks: 0
  },
  {
    category: 'Fixed Assets',
    process: 'Asset Depreciation',
    riskScore: 45,
    riskLevel: 'medium',
    taskCount: 5,
    completedTasks: 2
  },
  {
    category: 'Payables',
    process: 'Procurement',
    riskScore: 52,
    riskLevel: 'medium',
    taskCount: 2,
    completedTasks: 0
  },
  {
    category: 'Cash',
    process: 'Treasury Operations',
    riskScore: 25,
    riskLevel: 'low',
    taskCount: 2,
    completedTasks: 0
  },
  {
    category: 'Debt',
    process: 'Debt Covenants',
    riskScore: 68,
    riskLevel: 'high',
    taskCount: 4,
    completedTasks: 1
  },
  {
    category: 'Equity',
    process: 'Share Transactions',
    riskScore: 20,
    riskLevel: 'low',
    taskCount: 1,
    completedTasks: 1
  }
];

export const engagementMessages: EngagementMessage[] = [
  {
    id: 'eng-001',
    sender: 'user',
    content: '2025년도 ABC 주식회사 감사를 시작하려고 합니다. 제조업이며, 주요 사업은 전자부품 제조 및 판매입니다. 전년도 매출액은 823억원입니다.',
    timestamp: '2026-01-02T09:00:00Z'
  },
  {
    id: 'eng-002',
    sender: 'partner-agent',
    content: '안녕하세요. ABC 주식회사의 2025년도 감사를 담당할 Partner AI입니다. 제공해주신 정보를 바탕으로 다음 정보를 추가로 확인하고 싶습니다:\n\n1. 회사의 주요 고객 및 공급업체 집중도\n2. 재고자산 규모 및 재고관리 시스템\n3. 수출 비중 및 외환 익스포저\n4. 전년도 감사에서 지적된 주요 사항\n5. 경영진이 우려하는 회계 이슈',
    timestamp: '2026-01-02T09:05:00Z'
  },
  {
    id: 'eng-003',
    sender: 'user',
    content: '1. 상위 5개 고객이 매출의 65%를 차지합니다. 주요 공급업체 3곳이 원재료의 70% 공급\n2. 기말재고 약 187억원, ERP 시스템 사용 중\n3. 수출 비중 40%, 주로 USD 거래\n4. 전년도 수익인식 시점 관련 검토의견 있었음\n5. 신규 IFRS 15 적용 및 장기공급계약 회계처리',
    timestamp: '2026-01-02T10:30:00Z'
  },
  {
    id: 'eng-004',
    sender: 'partner-agent',
    content: '제공해주신 정보를 바탕으로 위험평가를 완료했습니다. 다음과 같은 감사계획을 제안드립니다:\n\n**주요 위험영역:**\n1. 수익인식 (Critical) - IFRS 15 적용 및 장기계약\n2. 재고자산 평가 (Critical) - 높은 재고 회전율 및 기술적 진부화\n3. 매출채권 회수가능성 (High) - 고객 집중도\n4. 외환 위험 (High) - 높은 수출 비중\n\n**제안 감사절차:**\n- 총 95개 태스크로 구성\n- 8개 주요 업무 사이클\n- 예상 소요시간: 6주\n\n승인하시겠습니까?',
    timestamp: '2026-01-02T11:00:00Z',
    status: 'pending-approval',
    attachments: [
      {
        name: 'Audit_Plan_ABC_2025.pdf',
        type: 'pdf'
      }
    ]
  },
  {
    id: 'eng-005',
    sender: 'user',
    content: '감사계획을 승인합니다. 다만 재고자산 실사는 12월 31일이 아닌 1월 5일에 진행될 예정이니 이를 반영해주세요.',
    timestamp: '2026-01-02T14:00:00Z'
  },
  {
    id: 'eng-006',
    sender: 'partner-agent',
    content: '감사계획이 승인되었습니다. 재고실사 일정을 1월 5일로 조정했습니다. 이제 각 Manager AI에게 업무를 배분하고 태스크 실행을 시작하겠습니다.\n\n**업무 배분:**\n- Revenue Cycle Manager: 35개 태스크\n- Inventory Manager: 18개 태스크\n- Cash & Treasury Manager: 12개 태스크\n- Fixed Assets Manager: 15개 태스크\n- Payables & Procurement Manager: 15개 태스크\n\n태스크 실행 화면에서 진행상황을 확인하실 수 있습니다.',
    timestamp: '2026-01-02T14:15:00Z',
    status: 'approved'
  }
];

export const documents: Document[] = [
  {
    id: 'doc-001',
    name: '2025_Trial_Balance.xlsx',
    type: 'spreadsheet',
    uploadedBy: 'user',
    uploadedAt: '2026-01-02T09:00:00Z',
    size: '2.4 MB',
    category: 'Financial Data',
    linkedTasks: ['T-001', 'T-002', 'T-003', 'T-015']
  },
  {
    id: 'doc-002',
    name: 'AR_Ledger_2025.xlsx',
    type: 'spreadsheet',
    uploadedBy: 'user',
    uploadedAt: '2026-01-02T09:15:00Z',
    size: '5.8 MB',
    category: 'Financial Data',
    linkedTasks: ['T-001', 'T-002']
  },
  {
    id: 'doc-003',
    name: 'Revenue_Recognition_Policy.pdf',
    type: 'pdf',
    uploadedBy: 'user',
    uploadedAt: '2026-01-02T10:00:00Z',
    size: '1.2 MB',
    category: 'Policies',
    linkedTasks: ['T-003', 'T-004']
  },
  {
    id: 'doc-004',
    name: 'Inventory_Count_Sheet.xlsx',
    type: 'spreadsheet',
    uploadedBy: 'staff-003',
    uploadedAt: '2026-01-05T14:00:00Z',
    size: '3.1 MB',
    category: 'Working Papers',
    linkedTasks: ['T-015']
  },
  {
    id: 'doc-005',
    name: 'AR_Sampling_List_v2.xlsx',
    type: 'spreadsheet',
    uploadedBy: 'staff-002',
    uploadedAt: '2026-01-06T11:45:00Z',
    size: '890 KB',
    category: 'Working Papers',
    linkedTasks: ['T-001']
  },
  {
    id: 'doc-006',
    name: 'Confirmation_Template.docx',
    type: 'document',
    uploadedBy: 'staff-001',
    uploadedAt: '2026-01-06T14:00:00Z',
    size: '125 KB',
    category: 'Templates',
    linkedTasks: ['T-001', 'T-050']
  }
];

export const engagementPlanSummary: EngagementPlanSummary = {
  clientName: 'ABC Corporation',
  fiscalYear: '2025',
  auditPeriod: {
    start: '2025-01-01',
    end: '2025-12-31'
  },
  materiality: {
    overall: 956000000, // 0.1% of revenue (95.6B * 0.01)
    performance: 717000000, // 75% of overall
    trivial: 47800000 // 5% of overall
  },
  keyAuditMatters: [
    {
      id: 'kam-001',
      matter: 'Revenue Recognition - IFRS 15 Application',
      riskLevel: 'critical',
      response: '장기공급계약에 대한 수행의무 식별 및 거래가격 배분의 적정성 집중 검토. 계약별 5단계 모델 적용 검증.'
    },
    {
      id: 'kam-002',
      matter: 'Inventory Valuation & NRV Assessment',
      riskLevel: 'critical',
      response: '기술적 진부화 위험이 높은 전자부품 재고에 대한 순실현가능가치 평가 강화. 기말 재고실사 참관 및 평가충당금 재계산.'
    },
    {
      id: 'kam-003',
      matter: 'Trade Receivables Recoverability',
      riskLevel: 'high',
      response: '상위 거래처 집중도로 인한 신용위험. 주요 거래처 외부조회 및 후속 입금 검토. 대손충당금 설정 기준의 합리성 평가.'
    },
    {
      id: 'kam-004',
      matter: 'Foreign Exchange Risk Management',
      riskLevel: 'high',
      response: '수출 비중 40%로 인한 환율 변동 익스포저. 파생상품 회계처리 및 헷지회계 요건 충족 여부 검토.'
    }
  ],
  timeline: [
    {
      phase: 'Planning & Risk Assessment',
      startDate: '2026-01-02',
      endDate: '2026-01-10',
      status: 'completed'
    },
    {
      phase: 'Interim Audit (Controls Testing)',
      startDate: '2026-01-11',
      endDate: '2026-01-25',
      status: 'in-progress'
    },
    {
      phase: 'Year-end Audit (Substantive Procedures)',
      startDate: '2026-01-26',
      endDate: '2026-02-20',
      status: 'planned'
    },
    {
      phase: 'Completion & Reporting',
      startDate: '2026-02-21',
      endDate: '2026-02-28',
      status: 'planned'
    }
  ],
  resources: {
    humanTeam: [
      { name: 'Kim Audit (Senior Partner)', role: 'Engagement Partner', allocation: '20%' },
      { name: 'Lee Manager', role: 'Audit Manager', allocation: '80%' },
      { name: 'Park Senior', role: 'Senior Auditor', allocation: '100%' },
      { name: 'Choi Staff', role: 'Staff Auditor', allocation: '100%' }
    ],
    aiAgents: [
      { name: 'Partner AI', role: 'partner', assignedTasks: 0 },
      { name: 'Revenue Cycle Manager', role: 'manager', assignedTasks: 35 },
      { name: 'Inventory Manager', role: 'manager', assignedTasks: 18 },
      { name: 'Cash Manager', role: 'manager', assignedTasks: 12 },
      { name: 'Staff Agents (4)', role: 'staff', assignedTasks: 95 }
    ]
  },
  approvalStatus: 'approved',
  approvedBy: 'Kim Audit',
  approvedAt: '2026-01-02T14:15:00Z'
};

export const workingPapers: WorkingPaper[] = [
  {
    id: 'wp-001',
    taskId: 'T-001',
    taskNumber: 'T-001',
    clientName: 'ABC Corporation',
    fiscalYear: '2025',
    accountCategory: 'Trade Receivables',
    preparedBy: 'Revenue Cycle Manager AI',
    preparedDate: '2026-01-13T16:00:00Z',
    reviewedBy: 'Park Senior',
    reviewedDate: '2026-01-14T10:30:00Z',
    purpose: '주요 매출채권에 대한 외부조회 절차를 통해 매출채권 잔액의 실재성(Existence)과 평가의 정확성(Valuation)을 검증한다.',
    procedures: [
      '매출채권 원장에서 기말 잔액 기준 상위 80% 이상 커버하는 샘플 47개 거래처 선정',
      '표준 조회서 양식 작성 및 이메일/우편 발송 (2026년 1월 6일)',
      '회신 수령 및 장부금액과 대사 (회신율 81%, 38개 거래처)',
      '미회신 거래처에 대한 독촉 및 대체절차 수행 (후속 입금 확인)',
      '불일치 금액에 대한 원인 분석 및 조정 필요성 검토'
    ],
    results: [
      { 
        description: '총 조회 발송 거래처', 
        value: '47개 (금액 21,500백만원, 커버리지 85%)', 
        exception: false 
      },
      { 
        description: '회신 수령', 
        value: '38개 (회신율 81%)', 
        exception: false 
      },
      { 
        description: '금액 일치', 
        value: '35개', 
        exception: false 
      },
      { 
        description: '금액 불일치', 
        value: '3개 (총 차이 120백만원)', 
        exception: true 
      },
      { 
        description: '미회신 거래처', 
        value: '9개 - 후속 입금으로 85% 검증 완료', 
        exception: false 
      }
    ],
    conclusion: '외부조회 및 대체절차 결과, 매출채권 잔액은 전반적으로 적정하게 표시되어 있음. 단, ABC Ltd.와의 불일치 금액 85백만원(운송 중 재화)에 대해서는 회사에 Cut-off 재검토를 요청하였으며, 회사는 결산 수정분개를 반영하기로 함.',
    conclusionType: 'adjustment-required',
    attachments: [
      { name: 'AR_Confirmation_Sample_List.xlsx', type: 'spreadsheet' },
      { name: 'Confirmation_Responses.pdf', type: 'pdf' },
      { name: 'Reconciliation_Summary.xlsx', type: 'spreadsheet' }
    ],
    version: 2,
    status: 'reviewed'
  },
  {
    id: 'wp-002',
    taskId: 'T-003',
    taskNumber: 'T-003',
    clientName: 'ABC Corporation',
    fiscalYear: '2025',
    accountCategory: 'Revenue',
    preparedBy: 'Revenue Cycle Manager AI',
    preparedDate: '2026-01-09T15:00:00Z',
    reviewedBy: 'Lee Manager',
    reviewedDate: '2026-01-10T09:00:00Z',
    signedOffBy: 'Kim Audit',
    signedOffDate: '2026-01-10T16:00:00Z',
    purpose: 'IFRS 15 수익인식 기준 적용의 적정성을 평가하고, 특히 장기공급계약에 대한 5단계 모델 적용을 검증한다.',
    procedures: [
      '회사의 수익인식 회계정책 문서 입수 및 IFRS 15 요구사항 대비 검토',
      '주요 매출 유형별(제품 판매, 장기공급계약) 수익인식 시점 분석',
      '상위 10개 장기공급계약 샘플링 및 계약서 검토',
      '각 계약별 수행의무 식별, 거래가격 산정, 배분 방법의 적정성 평가',
      '진행기준 적용 계약의 진행률 측정 방법 및 원가 추정의 합리성 검토'
    ],
    results: [
      { 
        description: '회계정책 적정성', 
        value: 'IFRS 15 요구사항 충족', 
        exception: false 
      },
      { 
        description: '장기계약 샘플 검토', 
        value: '10개 계약 (총 계약금액 35,000백만원)', 
        exception: false 
      },
      { 
        description: '수행의무 식별', 
        value: '모든 계약에서 적절히 식별됨', 
        exception: false 
      },
      { 
        description: '거래가격 배분', 
        value: '독립판매가격 기준 합리적 배분', 
        exception: false 
      },
      { 
        description: '진행률 측정', 
        value: '투입법(원가기준) 적용 적정', 
        exception: false 
      }
    ],
    conclusion: '회사의 수익인식 정책은 IFRS 15 기준을 준수하고 있으며, 장기공급계약에 대한 5단계 모델 적용이 적절함. 재무제표에 표시된 수익금액이 적정하다고 판단됨.',
    conclusionType: 'satisfactory',
    attachments: [
      { name: 'Revenue_Policy_Analysis.pdf', type: 'pdf' },
      { name: 'Contract_Review_Summary.xlsx', type: 'spreadsheet' },
      { name: 'POC_Calculation_Verification.xlsx', type: 'spreadsheet' }
    ],
    version: 1,
    status: 'signed-off'
  }
];

export const issues: Issue[] = [
  {
    id: 'issue-001',
    taskId: 'T-001',
    taskNumber: 'T-001',
    title: 'AR Confirmation - Cut-off Issue (ABC Ltd.)',
    description: 'ABC Ltd.와의 외부조회 결과 85백만원의 차이 발견. 원인 분석 결과, 12월 31일 운송 중인 재화를 회사는 매출로 인식했으나 고객은 1월 2일 입고분으로 인식. FOB 조건 검토 필요.',
    accountCategory: 'Trade Receivables',
    impact: 'medium',
    status: 'client-responded',
    identifiedBy: 'Confirmation Staff AI',
    identifiedDate: '2026-01-13T14:00:00Z',
    financialImpact: 85000000,
    clientResponse: '계약서 검토 결과 FOB Shipping Point 조건으로 회사의 인식이 적정함을 확인. 다만 보수적 관점에서 해당 거래를 2026년 1월로 이연하는 수정분개 반영 예정.',
    clientResponseDate: '2026-01-14T11:00:00Z',
    resolution: '회사가 자발적으로 수정분개 반영하기로 함. 2025년 매출 85백만원 감소, 매출채권 동일 금액 감소.',
    resolvedDate: '2026-01-14T15:00:00Z',
    requiresAdjustment: true,
    includeInManagementLetter: false
  },
  {
    id: 'issue-002',
    taskId: 'T-015',
    taskNumber: 'T-015',
    title: 'Inventory Obsolescence - Electronic Components (SKU-A205)',
    description: '재고실사 중 전자부품 SKU-A205 (장부가액 320백만원)가 18개월 이상 장기 체류 중이며, 기술 변화로 인해 향후 판매 가능성이 낮음. 순실현가능가치 평가 필요.',
    accountCategory: 'Inventory',
    impact: 'high',
    status: 'open',
    identifiedBy: 'Analytics Staff AI',
    identifiedDate: '2026-01-05T16:30:00Z',
    financialImpact: 320000000,
    requiresAdjustment: true,
    includeInManagementLetter: true
  },
  {
    id: 'issue-003',
    taskId: 'T-002',
    taskNumber: 'T-002',
    title: 'Allowance for Doubtful Accounts - XYZ Corporation',
    description: 'XYZ Corporation 매출채권 450백만원에 대해 3개월 이상 연체 중이나 대손충당금이 설정되지 않음. 고객의 최근 재무상태 악화 정황 포착.',
    accountCategory: 'Trade Receivables',
    impact: 'medium',
    status: 'open',
    identifiedBy: 'Sampling Staff AI',
    identifiedDate: '2026-01-12T10:00:00Z',
    financialImpact: 450000000,
    requiresAdjustment: true,
    includeInManagementLetter: true
  },
  {
    id: 'issue-004',
    taskId: 'T-004',
    taskNumber: 'T-004',
    title: 'Sales Invoice - Missing Supporting Documents',
    description: '표본 추출한 매출거래 중 3건(총 95백만원)에 대해 거래처 서명이 포함된 인수증 미비. 내부통제 미비사항.',
    accountCategory: 'Revenue',
    impact: 'low',
    status: 'client-responded',
    identifiedBy: 'Document Review Staff AI',
    identifiedDate: '2026-01-08T13:00:00Z',
    financialImpact: 95000000,
    clientResponse: '해당 거래처들로부터 인수증을 추가 징구하여 제출 완료. 향후 출고 시 인수증 필수 징구 절차를 내부통제에 반영하겠음.',
    clientResponseDate: '2026-01-10T14:00:00Z',
    resolution: '증빙 보완 완료. 내부통제 개선 권고사항으로 Management Letter에 포함 예정.',
    resolvedDate: '2026-01-10T16:00:00Z',
    requiresAdjustment: false,
    includeInManagementLetter: true
  }
];

export const agentTools: AgentTool[] = [
  {
    id: 'tool-001',
    name: 'OCR Document Reader',
    description: 'PDF 및 이미지 파일에서 텍스트를 추출하여 구조화된 데이터로 변환',
    category: 'data-extraction',
    enabled: true,
    assignedAgents: ['staff-001', 'staff-004'],
    usageCount: 127,
    lastUsed: '2026-01-13T15:30:00Z',
    permissions: ['read-files', 'extract-text']
  },
  {
    id: 'tool-002',
    name: 'SQL Query Engine',
    description: 'ERP 데이터베이스에 직접 쿼리를 실행하여 재무 데이터 추출',
    category: 'data-extraction',
    enabled: true,
    assignedAgents: ['staff-002', 'staff-003'],
    usageCount: 342,
    lastUsed: '2026-01-14T09:15:00Z',
    permissions: ['read-database', 'execute-query']
  },
  {
    id: 'tool-003',
    name: 'Statistical Sampling',
    description: 'MUS, Stratified Sampling 등 감사 표본추출 기법 자동 수행',
    category: 'analysis',
    enabled: true,
    assignedAgents: ['staff-002'],
    usageCount: 45,
    lastUsed: '2026-01-06T11:00:00Z',
    permissions: ['analyze-data']
  },
  {
    id: 'tool-004',
    name: 'Email Sender',
    description: '외부조회서 등 공식 문서를 이메일로 발송 (템플릿 기반)',
    category: 'communication',
    enabled: true,
    assignedAgents: ['staff-001'],
    usageCount: 52,
    lastUsed: '2026-01-06T14:00:00Z',
    permissions: ['send-email', 'use-templates']
  },
  {
    id: 'tool-005',
    name: 'Financial Ratio Calculator',
    description: '재무비율 자동 계산 및 산업 평균 대비 분석',
    category: 'analysis',
    enabled: true,
    assignedAgents: ['staff-002', 'staff-003'],
    usageCount: 28,
    lastUsed: '2026-01-12T16:00:00Z',
    permissions: ['analyze-data', 'access-benchmarks']
  },
  {
    id: 'tool-006',
    name: 'Web Scraper',
    description: '공시 사이트, 거래처 홈페이지 등에서 공개 정보 수집',
    category: 'data-extraction',
    enabled: true,
    assignedAgents: ['staff-003'],
    usageCount: 15,
    lastUsed: '2026-01-10T10:30:00Z',
    permissions: ['web-access', 'scrape-data']
  },
  {
    id: 'tool-007',
    name: 'XBRL Parser',
    description: 'XBRL 형식의 재무제표를 파싱하여 비교 분석',
    category: 'data-extraction',
    enabled: false,
    assignedAgents: [],
    usageCount: 0,
    permissions: ['read-files', 'parse-xbrl']
  },
  {
    id: 'tool-008',
    name: 'National Tax Service API',
    description: '국세청 시스템과 연동하여 사업자 정보 및 세금계산서 진위 확인',
    category: 'verification',
    enabled: false,
    assignedAgents: [],
    usageCount: 0,
    permissions: ['external-api', 'verify-tax-data']
  },
  {
    id: 'tool-009',
    name: 'Bank Confirmation API',
    description: '은행과 직접 연동하여 잔액증명서 자동 수령',
    category: 'verification',
    enabled: false,
    assignedAgents: [],
    usageCount: 0,
    permissions: ['external-api', 'bank-integration']
  },
  {
    id: 'tool-010',
    name: 'Inventory Matching Algorithm',
    description: 'ERP 재고와 실사 결과를 자동 매칭하여 차이 분석',
    category: 'analysis',
    enabled: true,
    assignedAgents: ['staff-003'],
    usageCount: 8,
    lastUsed: '2026-01-05T17:00:00Z',
    permissions: ['analyze-data', 'compare-datasets']
  }
];