/**
 * Audit hierarchy types for 3-level task structure
 *
 * These types support the hierarchical organization of audit tasks
 * following K-GAAS (Korean Generally Accepted Auditing Standards) requirements.
 */

/**
 * Levels in the audit hierarchy
 * - high: Major audit areas (e.g., Revenue, Expenses)
 * - mid: Sub-areas within major areas (e.g., Sales Revenue, Service Revenue)
 * - low: Specific accounts or line items
 * - task: Individual audit procedures/tasks
 */
export type HierarchyLevel = 'high' | 'mid' | 'low' | 'task';

/**
 * Status of a hierarchy item
 */
export type HierarchyStatus =
  | 'not_started'
  | 'in_progress'
  | 'pending_review'
  | 'completed'
  | 'blocked';

/**
 * A single item in the audit hierarchy tree
 */
export interface HierarchyItem {
  /** Unique identifier */
  id: string;
  /** Project this item belongs to */
  projectId: string;
  /** Level in the hierarchy */
  level: HierarchyLevel;
  /** Parent item ID (undefined for root items) */
  parentId?: string;
  /** Display name */
  name: string;
  /** Current status */
  status: HierarchyStatus;
  /** Number of conversations related to this item */
  conversationCount: number;
  /** Total number of child tasks (for non-task items) */
  taskCount?: number;
  /** Number of completed child tasks */
  completedTaskCount?: number;
  /** Reference number (e.g., from audit program) */
  refNo?: string;
  /** Source column from imported data */
  sourceColumn?: string;
  /** Source row number from imported data */
  sourceRow?: number;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Child items in the hierarchy */
  children?: HierarchyItem[];
}

/**
 * State management for the hierarchy tree component
 */
export interface HierarchyTreeState {
  /** All hierarchy items */
  items: HierarchyItem[];
  /** Currently selected item ID */
  selectedId: string | null;
  /** Set of expanded item IDs */
  expandedIds: Set<string>;
  /** Active filter settings */
  filter: HierarchyFilter;
}

/**
 * Filter criteria for hierarchy items
 */
export interface HierarchyFilter {
  /** Filter by hierarchy levels */
  levels?: HierarchyLevel[];
  /** Filter by statuses */
  statuses?: HierarchyStatus[];
  /** Text search term */
  searchTerm?: string;
  /** Show completed items */
  showCompleted?: boolean;
  /** Show only items with conversations */
  showOnlyWithConversations?: boolean;
}

// ============================================================================
// Task Assertions (K-GAAS)
// ============================================================================

/**
 * Assertion types according to K-GAAS (Korean Generally Accepted Auditing Standards)
 *
 * - existence: 실재성/발생사실 - The asset, liability, or transaction exists
 * - completeness: 완전성 - All items that should be recorded are recorded
 * - valuation: 평가/배분 - Items are recorded at appropriate amounts
 * - rights: 권리와 의무 - The entity holds rights to assets and has obligations for liabilities
 * - presentation: 표시와 공시 - Items are properly classified, described, and disclosed
 */
export type AssertionType =
  | 'existence'      // 실재성/발생사실
  | 'completeness'   // 완전성
  | 'valuation'      // 평가/배분
  | 'rights'         // 권리와 의무
  | 'presentation';  // 표시와 공시

/**
 * An assertion test for a specific task
 */
export interface TaskAssertion {
  /** Unique identifier */
  id: string;
  /** Task this assertion belongs to */
  taskId: string;
  /** Type of assertion being tested */
  assertionType: AssertionType;
  /** Approach used to test the assertion */
  testApproach: string;
  /** Conclusion of the assertion test */
  conclusion: 'satisfied' | 'exception' | 'pending';
  /** References to supporting evidence documents */
  evidenceRefs: string[];
}

// ============================================================================
// Audit Exceptions
// ============================================================================

/**
 * Types of audit exceptions
 */
export type ExceptionType =
  | 'procedure_deviation'  // Deviation from planned audit procedure
  | 'control_deficiency'   // Identified control weakness
  | 'misstatement'         // Error or misstatement in financial data
  | 'scope_limitation';    // Limitation on audit scope

/**
 * Severity levels for exceptions
 */
export type ExceptionSeverity = 'minor' | 'significant' | 'material';

/**
 * Status of an exception
 */
export type ExceptionStatus = 'open' | 'addressed' | 'waived' | 'escalated';

/**
 * An audit exception identified during procedures
 */
export interface AuditException {
  /** Unique identifier */
  id: string;
  /** Task where the exception was identified */
  taskId: string;
  /** Type of exception */
  exceptionType: ExceptionType;
  /** Severity of the exception */
  severity: ExceptionSeverity;
  /** Description of the exception */
  description: string;
  /** Root cause analysis */
  rootCause?: string;
  /** Plan to address the exception */
  remediationPlan?: string;
  /** Current status */
  status: ExceptionStatus;
  /** Agent or user who identified the exception */
  identifiedBy: string;
  /** ISO timestamp of identification */
  identifiedAt: string;
  /** ISO timestamp of resolution */
  resolvedAt?: string;
  /** Notes on how the exception was resolved */
  resolutionNotes?: string;
}

// ============================================================================
// Evidence Links
// ============================================================================

/**
 * Source types that can be linked to evidence
 */
export type EvidenceSourceType = 'task' | 'workpaper' | 'assertion' | 'exception';

/**
 * Types of links between sources and evidence
 */
export type EvidenceLinkType = 'supporting' | 'referenced' | 'generated';

/**
 * A link between a source and supporting evidence document
 */
export interface EvidenceLink {
  /** Unique identifier */
  id: string;
  /** Type of source being linked */
  sourceType: EvidenceSourceType;
  /** ID of the source item */
  sourceId: string;
  /** ID of the evidence document */
  documentId: string;
  /** Type of link relationship */
  linkType: EvidenceLinkType;
  /** Specific page range in the document (e.g., "1-5", "3,7,12") */
  pageRange?: string;
  /** Description of the evidence relevance */
  description?: string;
  /** ISO timestamp of when the link was created */
  linkedAt: string;
  /** User or agent who created the link */
  linkedBy: string;
}

/**
 * A chain of evidence documents for traceability
 */
export interface EvidenceChain {
  /** Unique identifier for the chain */
  id: string;
  /** Name of the evidence chain */
  chainName: string;
  /** ID of the root document in the chain */
  rootDocumentId: string;
  /** Ordered list of document IDs in the chain */
  chainPath: string[];
}
