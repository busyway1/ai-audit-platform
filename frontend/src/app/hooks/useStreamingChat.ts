/**
 * SSE Streaming Chat Hook
 *
 * This hook provides a streaming chat interface that simulates real-time AI responses
 * and artifact generation. It uses Server-Sent Events (SSE) for streaming updates
 * and integrates with the chat and artifact stores.
 *
 * Features:
 * - Detects artifact type from user query keywords
 * - Streams AI responses with mock data
 * - Creates and updates artifacts in real-time
 * - Integrates with useChatStore and useArtifactStore
 *
 * @module hooks/useStreamingChat
 */

import { useState, useCallback } from 'react'
import { nanoid } from 'nanoid'
import { useChatStore } from '../stores/useChatStore'
import { useArtifactStore } from '../stores/useArtifactStore'
import type { ChatMessage, Artifact } from '../types/audit'

/**
 * Mock data generators for different artifact types
 */
const mockDataGenerators = {
  dashboard: () => ({
    agents: [
      {
        id: nanoid(),
        name: 'Senior Partner AI',
        role: 'partner' as const,
        status: 'working' as const,
        currentTask: 'Revenue Recognition Analysis',
      },
      {
        id: nanoid(),
        name: 'Manager AI',
        role: 'manager' as const,
        status: 'idle' as const,
      },
    ],
    tasks: [
      {
        id: nanoid(),
        status: 'completed' as const,
        riskLevel: 'low' as const,
        phase: 'Planning',
      },
      {
        id: nanoid(),
        status: 'in-progress' as const,
        riskLevel: 'high' as const,
        phase: 'Risk Assessment',
      },
    ],
    riskHeatmap: [
      {
        category: 'Revenue',
        process: 'Sales Recognition',
        riskScore: 85,
        riskLevel: 'high' as const,
        taskCount: 12,
        completedTasks: 8,
      },
      {
        category: 'Inventory',
        process: 'Valuation',
        riskScore: 60,
        riskLevel: 'medium' as const,
        taskCount: 8,
        completedTasks: 3,
      },
    ],
  }),

  'financial-statements': () => ({
    items: [
      {
        id: nanoid(),
        category: 'Assets',
        account: 'Cash and Equivalents',
        currentYear: 1500000,
        priorYear: 1200000,
        variance: 300000,
        variancePercent: 25.0,
        taskCount: 5,
        completedTasks: 5,
        riskLevel: 'low' as const,
      },
      {
        id: nanoid(),
        category: 'Revenue',
        account: 'Sales Revenue',
        currentYear: 5000000,
        priorYear: 4500000,
        variance: 500000,
        variancePercent: 11.11,
        taskCount: 8,
        completedTasks: 6,
        riskLevel: 'medium' as const,
      },
    ],
    selectedAccount: null,
    relatedTasks: [],
  }),

  'issue-details': () => ({
    id: nanoid(),
    taskId: nanoid(),
    taskNumber: 'A-100',
    title: 'Revenue Recognition Timing Issue',
    description: 'Potential revenue recognized before delivery of goods.',
    accountCategory: 'Revenue',
    impact: 'high' as const,
    status: 'open' as const,
    identifiedBy: 'Staff AI',
    identifiedDate: '2024-01-15',
    financialImpact: 250000,
    requiresAdjustment: true,
    includeInManagementLetter: true,
  }),

  'task-status': () => ({
    task: {
      id: nanoid(),
      taskNumber: 'A-100',
      title: 'Revenue Recognition Testing',
      description: 'Test revenue recognition timing and completeness.',
      status: 'in-progress' as const,
      phase: 'substantive-procedures' as const,
      accountCategory: 'Revenue',
      businessProcess: 'Sales',
      assignedManager: 'Manager AI',
      assignedStaff: ['Staff AI 1', 'Staff AI 2'],
      progress: 65,
      riskLevel: 'high' as const,
      requiresReview: true,
      dueDate: '2024-02-15',
      createdAt: '2024-01-10',
    },
    messages: [
      {
        id: nanoid(),
        taskId: nanoid(),
        agentId: nanoid(),
        agentName: 'Staff AI 1',
        agentRole: 'staff' as const,
        content: 'Initiating revenue recognition testing.',
        timestamp: '2024-01-10T09:00:00Z',
        type: 'instruction' as const,
      },
      {
        id: nanoid(),
        taskId: nanoid(),
        agentId: nanoid(),
        agentName: 'Manager AI',
        agentRole: 'manager' as const,
        content: 'Sample selection completed.',
        timestamp: '2024-01-11T14:30:00Z',
        type: 'response' as const,
      },
    ],
  }),

  'engagement-plan': () => ({
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
        id: nanoid(),
        matter: 'Revenue Recognition',
        riskLevel: 'high' as const,
        response: 'Detailed substantive testing of revenue cutoff.',
      },
    ],
    timeline: [
      {
        phase: 'Planning',
        startDate: '2024-01-15',
        endDate: '2024-02-15',
        status: 'in-progress' as const,
      },
    ],
    resources: {
      humanTeam: [
        {
          name: 'John Smith',
          role: 'Engagement Partner',
          allocation: '20%',
        },
      ],
      aiAgents: [
        {
          name: 'Partner AI',
          role: 'partner' as const,
          assignedTasks: 5,
        },
      ],
    },
    approvalStatus: 'draft' as const,
  }),
}

/**
 * Detect artifact type from user query
 */
function detectArtifactType(query: string): keyof typeof mockDataGenerators {
  const lowerQuery = query.toLowerCase()

  if (lowerQuery.includes('dashboard')) return 'dashboard'
  if (lowerQuery.includes('financial') || lowerQuery.includes('statement')) return 'financial-statements'
  if (lowerQuery.includes('issue')) return 'issue-details'
  if (lowerQuery.includes('task')) return 'task-status'
  if (lowerQuery.includes('engagement') || lowerQuery.includes('plan')) return 'engagement-plan'

  // Default to engagement-plan
  return 'engagement-plan'
}

/**
 * Get artifact title based on type
 */
function getArtifactTitle(type: keyof typeof mockDataGenerators): string {
  const titles: Record<keyof typeof mockDataGenerators, string> = {
    dashboard: 'Dashboard Overview',
    'financial-statements': 'Financial Statements Overview',
    'issue-details': 'Issue Details',
    'task-status': 'Task Status Details',
    'engagement-plan': 'Engagement Plan',
  }
  return titles[type]
}

/**
 * Get AI response message based on artifact type
 */
function getAIResponse(type: keyof typeof mockDataGenerators): string {
  const responses: Record<keyof typeof mockDataGenerators, string> = {
    dashboard: "I've created a dashboard overview for you. Check the artifact panel →",
    'financial-statements': "I've prepared the financial statements analysis. Check the artifact panel →",
    'issue-details': "I've documented the issue details. Check the artifact panel →",
    'task-status': "I've retrieved the task status and agent messages. Check the artifact panel →",
    'engagement-plan': "I've created an engagement plan for you. Check the artifact panel →",
  }
  return responses[type]
}

/**
 * Hook for streaming chat with SSE
 *
 * This hook simulates a streaming AI chat interface that:
 * 1. Adds user message to chat store
 * 2. Creates streaming AI message
 * 3. Detects artifact type from query
 * 4. Generates mock data for artifact
 * 5. Updates AI message with final content
 * 6. Marks artifact as complete
 *
 * @returns Object with sendMessage function and streaming state
 *
 * @example
 * ```tsx
 * function ChatInterface() {
 *   const { sendMessage } = useStreamingChat()
 *
 *   const handleSend = async (message: string) => {
 *     await sendMessage(message)
 *   }
 *
 *   return <ChatInput onSend={handleSend} />
 * }
 * ```
 */
export function useStreamingChat() {
  const [isStreaming, setIsStreaming] = useState(false)
  const addMessage = useChatStore((state) => state.addMessage)
  const updateMessage = useChatStore((state) => state.updateMessage)
  const addArtifact = useArtifactStore((state) => state.addArtifact)
  const updateArtifact = useArtifactStore((state) => state.updateArtifact)

  const sendMessage = useCallback(
    async (content: string) => {
      setIsStreaming(true)

      try {
        // 1. Add user message
        const userMessage: ChatMessage = {
          id: nanoid(),
          sender: 'user',
          content,
          timestamp: new Date(),
        }
        addMessage(userMessage)

        // 2. Create initial AI message (streaming)
        const aiMessageId = nanoid()
        const aiMessage: ChatMessage = {
          id: aiMessageId,
          sender: 'ai',
          content: '',
          timestamp: new Date(),
          streaming: true,
        }
        addMessage(aiMessage)

        // 3. Detect artifact type
        const artifactType = detectArtifactType(content)

        // 4. Generate mock data
        const mockData = mockDataGenerators[artifactType]()

        // 5. Create artifact (streaming)
        const artifactId = nanoid()
        const artifact: Artifact = {
          id: artifactId,
          type: artifactType,
          title: getArtifactTitle(artifactType),
          data: mockData,
          createdAt: new Date(),
          updatedAt: new Date(),
          status: 'streaming',
        } as Artifact

        addArtifact(artifact)

        // 6. Simulate streaming delay
        await new Promise((resolve) => setTimeout(resolve, 1000))

        // 7. Update AI message with final content and artifact reference
        updateMessage(aiMessageId, {
          content: getAIResponse(artifactType),
          streaming: false,
          artifactId,
        })

        // 8. Mark artifact as complete
        await new Promise((resolve) => setTimeout(resolve, 500))
        updateArtifact(artifactId, { status: 'complete' })
      } finally {
        setIsStreaming(false)
      }
    },
    [addMessage, updateMessage, addArtifact, updateArtifact]
  )

  return {
    sendMessage,
    isStreaming,
  }
}
