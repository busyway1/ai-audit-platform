import { nanoid } from 'nanoid';
import { useChatStore } from '@/app/stores/useChatStore';
import { useArtifactStore } from '@/app/stores/useArtifactStore';
import type { ChatMessage, Artifact } from '@/app/types/audit';

/**
 * Hook for SSE streaming with artifact parsing
 *
 * Features:
 * - Sends user messages to chat store
 * - Simulates AI streaming responses (mock SSE for Phase 2)
 * - Parses JSON blocks from AI responses to create artifacts
 * - Updates both chat and artifact stores
 * - Supports 5 artifact types based on query keywords
 *
 * Phase 2: Mock implementation with simulated streaming
 * Future: Real SSE backend integration
 */
export function useStreamingChat() {
  const { addMessage, updateMessage } = useChatStore();
  const { addArtifact, updateArtifact } = useArtifactStore();

  /**
   * Detect artifact type from user query
   * @param query - User message content
   * @returns Artifact type based on keywords
   */
  const detectArtifactType = (query: string): Artifact['type'] => {
    const lowerQuery = query.toLowerCase();

    // Order matters: more specific patterns first
    if (lowerQuery.includes('dashboard')) {
      return 'dashboard';
    }
    if (lowerQuery.includes('financial') || lowerQuery.includes('statement')) {
      return 'financial-statements';
    }
    if (lowerQuery.includes('issue')) {
      return 'issue-details';
    }
    if (lowerQuery.includes('task')) {
      return 'task-status';
    }
    if (lowerQuery.includes('engagement') || lowerQuery.includes('plan')) {
      return 'engagement-plan';
    }

    // Default fallback
    return 'engagement-plan';
  };

  /**
   * Generate mock artifact data based on type
   * @param type - Artifact type
   * @returns Mock artifact data
   */
  const generateMockArtifact = (type: Artifact['type']): Artifact => {
    const baseId = nanoid();
    const now = new Date();

    switch (type) {
      case 'dashboard':
        return {
          id: baseId,
          type: 'dashboard',
          title: 'Dashboard Overview',
          data: {
            agents: [
              {
                id: 'agent-1',
                name: 'Partner Agent',
                role: 'partner',
                status: 'working',
                currentTask: 'Revenue Recognition Analysis',
              },
              {
                id: 'agent-2',
                name: 'Senior Manager',
                role: 'manager',
                status: 'idle',
              },
            ],
            tasks: [
              {
                id: 'task-1',
                status: 'completed',
                riskLevel: 'low',
                phase: 'planning',
              },
              {
                id: 'task-2',
                status: 'in-progress',
                riskLevel: 'high',
                phase: 'substantive-procedures',
              },
            ],
            riskHeatmap: [
              {
                category: 'Revenue',
                process: 'Sales Recognition',
                riskScore: 85,
                riskLevel: 'high',
                taskCount: 5,
                completedTasks: 2,
              },
              {
                category: 'Cash',
                process: 'Bank Reconciliation',
                riskScore: 30,
                riskLevel: 'low',
                taskCount: 3,
                completedTasks: 3,
              },
            ],
          },
          createdAt: now,
          updatedAt: now,
          status: 'streaming',
        };

      case 'financial-statements':
        return {
          id: baseId,
          type: 'financial-statements',
          title: 'Financial Statements Overview',
          data: {
            items: [
              {
                id: 'fs-1',
                category: 'Assets',
                account: 'Cash and Equivalents',
                currentYear: 1500000,
                priorYear: 1200000,
                variance: 300000,
                variancePercent: 25.0,
                taskCount: 3,
                completedTasks: 2,
                riskLevel: 'low',
              },
              {
                id: 'fs-2',
                category: 'Revenue',
                account: 'Product Sales',
                currentYear: 5000000,
                priorYear: 4200000,
                variance: 800000,
                variancePercent: 19.05,
                taskCount: 8,
                completedTasks: 3,
                riskLevel: 'high',
              },
            ],
            selectedAccount: null,
            relatedTasks: [],
          },
          createdAt: now,
          updatedAt: now,
          status: 'streaming',
        };

      case 'issue-details':
        return {
          id: baseId,
          type: 'issue-details',
          title: 'Issue Details',
          data: {
            id: 'issue-1',
            taskId: 'task-1',
            taskNumber: 'A-100',
            title: 'Revenue Recognition Timing Issue',
            description:
              'Client recognized revenue in Q4 that should have been deferred to Q1 next year.',
            accountCategory: 'Revenue',
            impact: 'high',
            status: 'open',
            identifiedBy: 'Senior Auditor - AI Agent',
            identifiedDate: '2024-12-15',
            financialImpact: 250000,
            requiresAdjustment: true,
            includeInManagementLetter: true,
          },
          createdAt: now,
          updatedAt: now,
          status: 'streaming',
        };

      case 'task-status':
        return {
          id: baseId,
          type: 'task-status',
          title: 'Task Status Details',
          data: {
            task: {
              id: 'task-1',
              taskNumber: 'A-100',
              title: 'Revenue Recognition Testing',
              description: 'Perform substantive testing on revenue recognition policies.',
              status: 'in-progress',
              phase: 'substantive-procedures',
              accountCategory: 'Revenue',
              businessProcess: 'Sales',
              assignedManager: 'AI Manager Agent',
              assignedStaff: ['AI Staff 1', 'AI Staff 2'],
              progress: 65,
              riskLevel: 'high',
              requiresReview: true,
              dueDate: '2024-12-31',
              createdAt: '2024-12-01',
            },
            messages: [
              {
                id: 'msg-1',
                taskId: 'task-1',
                agentId: 'agent-1',
                agentName: 'AI Manager',
                agentRole: 'manager',
                content: 'Starting revenue recognition analysis using data extraction tools.',
                timestamp: '2024-12-01T10:00:00Z',
                type: 'instruction',
              },
              {
                id: 'msg-2',
                taskId: 'task-1',
                agentId: 'agent-2',
                agentName: 'AI Staff 1',
                agentRole: 'staff',
                content: 'Extracted 1,247 sales transactions from Q4. Analyzing revenue cut-off.',
                timestamp: '2024-12-02T14:30:00Z',
                type: 'response',
              },
            ],
          },
          createdAt: now,
          updatedAt: now,
          status: 'streaming',
        };

      case 'engagement-plan':
      default:
        return {
          id: baseId,
          type: 'engagement-plan',
          title: 'Engagement Plan',
          data: {
            clientName: 'Mock Client Corporation',
            fiscalYear: '2024',
            auditPeriod: {
              start: '2024-01-01',
              end: '2024-12-31',
            },
            materiality: {
              overall: 1000000,
              performance: 750000,
              trivial: 50000,
            },
            keyAuditMatters: [
              {
                id: 'kam-1',
                matter: 'Revenue Recognition',
                riskLevel: 'high',
                response: 'Perform detailed substantive testing on revenue cut-off.',
              },
            ],
            timeline: [
              {
                phase: 'Planning',
                startDate: '2024-11-01',
                endDate: '2024-11-30',
                status: 'completed',
              },
              {
                phase: 'Fieldwork',
                startDate: '2024-12-01',
                endDate: '2025-01-31',
                status: 'in-progress',
              },
            ],
            resources: {
              humanTeam: [
                { name: 'John Partner', role: 'Engagement Partner', allocation: '20%' },
                { name: 'Sarah Manager', role: 'Manager', allocation: '80%' },
              ],
              aiAgents: [
                { name: 'Partner AI Agent', role: 'partner', assignedTasks: 5 },
                { name: 'Manager AI Agent', role: 'manager', assignedTasks: 15 },
              ],
            },
            approvalStatus: 'draft',
          },
          createdAt: now,
          updatedAt: now,
          status: 'streaming',
        };
    }
  };

  /**
   * Get AI response message based on artifact type
   * @param type - Artifact type
   * @returns AI response message
   */
  const getAIResponseMessage = (type: Artifact['type']): string => {
    switch (type) {
      case 'dashboard':
        return "I've created a dashboard overview for you. Check the artifact panel →";
      case 'financial-statements':
        return "I've prepared the financial statements analysis. Check the artifact panel →";
      case 'issue-details':
        return "I've documented the issue details. Check the artifact panel →";
      case 'task-status':
        return "I've retrieved the task status and agent messages. Check the artifact panel →";
      case 'engagement-plan':
      default:
        return "I've created an engagement plan for you. Check the artifact panel →";
    }
  };

  /**
   * Send a message and handle the streaming AI response
   *
   * @param content - User message content
   */
  const sendMessage = async (content: string): Promise<void> => {
    // Add user message to chat
    const userMsg: ChatMessage = {
      id: nanoid(),
      sender: 'user',
      content,
      timestamp: new Date(),
    };
    addMessage(userMsg);

    // Create AI message with streaming state
    const aiMsgId = nanoid();
    const aiMsg: ChatMessage = {
      id: aiMsgId,
      sender: 'ai',
      content: 'Analyzing your request...',
      timestamp: new Date(),
      streaming: true,
    };
    addMessage(aiMsg);

    // Simulate streaming delay (mock SSE)
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Detect artifact type from query
    const artifactType = detectArtifactType(content);

    // Generate mock artifact based on type
    const mockArtifact = generateMockArtifact(artifactType);

    // Add artifact to store
    addArtifact(mockArtifact);

    // Update AI message with final content and artifact reference
    updateMessage(aiMsgId, {
      content: getAIResponseMessage(artifactType),
      streaming: false,
      artifactId: mockArtifact.id,
    });

    // Simulate artifact completion delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Mark artifact as complete
    updateArtifact(mockArtifact.id, { status: 'complete' });
  };

  return { sendMessage };
}
