/**
 * SSE Streaming Chat Hook
 *
 * This hook provides a streaming chat interface with real SSE connection
 * for real-time AI responses and artifact generation.
 *
 * Features:
 * - Real SSE connection to backend streaming endpoint
 * - Automatic reconnection with exponential backoff (max 30s)
 * - Handles message, heartbeat, artifact_update, artifact_complete, and error events
 * - Fallback mock mode for demo/testing
 * - Integrates with useChatStore and useArtifactStore
 *
 * @module hooks/useStreamingChat
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { nanoid } from 'nanoid'
import { useChatStore } from '../stores/useChatStore'
import { useArtifactStore } from '../stores/useArtifactStore'
import type { ChatMessage, Artifact, ArtifactType } from '../types/audit'

/**
 * SSE Event types from backend
 */
interface SSEEventData {
  type: 'message' | 'artifact_start' | 'artifact_update' | 'artifact_complete' | 'error' | 'heartbeat' | 'done'
  content?: string
  artifactId?: string
  artifactType?: ArtifactType
  artifactTitle?: string
  artifactData?: Record<string, unknown>
  error?: string
  timestamp?: string
}

/**
 * Connection status types
 */
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

/**
 * Hook options for configuring SSE behavior
 */
interface UseStreamingChatOptions {
  /** API base URL for SSE endpoint */
  baseUrl?: string
  /** Enable mock mode for demo/testing (default: false) */
  mockMode?: boolean
  /** Maximum reconnection attempts before giving up (default: 10) */
  maxReconnectAttempts?: number
  /** Initial delay before first reconnect in ms (default: 1000) */
  initialReconnectDelay?: number
  /** Maximum delay between reconnects in ms (default: 30000 = 30s) */
  maxReconnectDelay?: number
}

/**
 * Hook return type
 */
interface UseStreamingChatReturn {
  /** Send a message and start streaming response */
  sendMessage: (content: string, taskId?: string) => Promise<void>
  /** Whether the hook is currently streaming a response */
  isStreaming: boolean
  /** Current SSE connection status */
  connectionStatus: ConnectionStatus
  /** Manually disconnect from SSE stream */
  disconnect: () => void
  /** Current reconnection attempt count */
  reconnectAttempts: number
  /** Any connection error message */
  connectionError: string | null
}

/**
 * Mock data generators for different artifact types (used in mock mode)
 */
const mockDataGenerators: Record<string, () => Record<string, unknown>> = {
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
function detectArtifactType(query: string): ArtifactType {
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
function getArtifactTitle(type: ArtifactType): string {
  const titles: Record<ArtifactType, string> = {
    dashboard: 'Dashboard Overview',
    'financial-statements': 'Financial Statements Overview',
    'issue-details': 'Issue Details',
    'task-status': 'Task Status Details',
    'engagement-plan': 'Engagement Plan',
    'working-paper': 'Working Paper',
    document: 'Document',
  }
  return titles[type] || 'Artifact'
}

/**
 * Get AI response message based on artifact type
 */
function getAIResponse(type: ArtifactType): string {
  const responses: Record<ArtifactType, string> = {
    dashboard: "I've created a dashboard overview for you. Check the artifact panel.",
    'financial-statements': "I've prepared the financial statements analysis. Check the artifact panel.",
    'issue-details': "I've documented the issue details. Check the artifact panel.",
    'task-status': "I've retrieved the task status and agent messages. Check the artifact panel.",
    'engagement-plan': "I've created an engagement plan for you. Check the artifact panel.",
    'working-paper': "I've prepared the working paper. Check the artifact panel.",
    document: "I've retrieved the document. Check the artifact panel.",
  }
  return responses[type] || "I've created an artifact for you. Check the artifact panel."
}

/**
 * Calculate exponential backoff delay
 */
function calculateBackoffDelay(
  attempt: number,
  initialDelay: number,
  maxDelay: number
): number {
  // Exponential backoff: initialDelay * 2^attempt with jitter
  const exponentialDelay = initialDelay * Math.pow(2, attempt)
  const jitter = Math.random() * 0.3 * exponentialDelay // 0-30% jitter
  const delayWithJitter = exponentialDelay + jitter
  return Math.min(delayWithJitter, maxDelay)
}

/**
 * Hook for streaming chat with real SSE connection
 *
 * This hook provides:
 * 1. Real SSE connection to backend streaming endpoint
 * 2. Automatic reconnection with exponential backoff
 * 3. Message, artifact, and error event handling
 * 4. Fallback mock mode for demo/testing
 *
 * @param options - Configuration options
 * @returns Object with sendMessage function, connection state, and controls
 *
 * @example
 * ```tsx
 * function ChatInterface() {
 *   const { sendMessage, isStreaming, connectionStatus } = useStreamingChat({
 *     baseUrl: 'http://localhost:8000',
 *   })
 *
 *   const handleSend = async (message: string, taskId: string) => {
 *     await sendMessage(message, taskId)
 *   }
 *
 *   return (
 *     <div>
 *       <ChatInput onSend={handleSend} disabled={isStreaming} />
 *       <ConnectionIndicator status={connectionStatus} />
 *     </div>
 *   )
 * }
 * ```
 */
export function useStreamingChat(options: UseStreamingChatOptions = {}): UseStreamingChatReturn {
  const {
    baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    mockMode = false,
    maxReconnectAttempts = 10,
    initialReconnectDelay = 1000,
    maxReconnectDelay = 30000,
  } = options

  // State
  const [isStreaming, setIsStreaming] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Refs for cleanup and reconnection
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const currentAiMessageIdRef = useRef<string | null>(null)
  const currentArtifactIdRef = useRef<string | null>(null)
  const isUnmountedRef = useRef(false)

  // Store actions
  const addMessage = useChatStore((state) => state.addMessage)
  const updateMessage = useChatStore((state) => state.updateMessage)
  const addArtifact = useArtifactStore((state) => state.addArtifact)
  const updateArtifact = useArtifactStore((state) => state.updateArtifact)

  /**
   * Clean up EventSource and reconnect timeout
   */
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
  }, [])

  /**
   * Disconnect from SSE stream
   */
  const disconnect = useCallback(() => {
    cleanup()
    setConnectionStatus('disconnected')
    setIsStreaming(false)
    setReconnectAttempts(0)
    setConnectionError(null)
  }, [cleanup])

  // Cleanup on unmount
  useEffect(() => {
    isUnmountedRef.current = false
    return () => {
      isUnmountedRef.current = true
      cleanup()
    }
  }, [cleanup])

  /**
   * Handle SSE events
   */
  const handleSSEEvent = useCallback((event: MessageEvent) => {
    if (isUnmountedRef.current) return

    try {
      const data: SSEEventData = JSON.parse(event.data)

      switch (data.type) {
        case 'heartbeat':
          // Heartbeat event - connection is alive, no action needed
          break

        case 'message':
          // Streaming message content
          if (currentAiMessageIdRef.current && data.content) {
            updateMessage(currentAiMessageIdRef.current, {
              content: data.content,
              streaming: true,
            })
          }
          break

        case 'artifact_start':
          // New artifact being created
          if (data.artifactId && data.artifactType && data.artifactTitle) {
            currentArtifactIdRef.current = data.artifactId
            const artifact: Artifact = {
              id: data.artifactId,
              type: data.artifactType,
              title: data.artifactTitle,
              data: data.artifactData || {},
              createdAt: new Date(),
              updatedAt: new Date(),
              status: 'streaming',
            } as Artifact
            addArtifact(artifact)
          }
          break

        case 'artifact_update':
          // Update artifact data
          if (currentArtifactIdRef.current && data.artifactData) {
            updateArtifact(currentArtifactIdRef.current, {
              data: data.artifactData,
              updatedAt: new Date(),
            })
          }
          break

        case 'artifact_complete':
          // Artifact streaming complete
          if (currentArtifactIdRef.current) {
            updateArtifact(currentArtifactIdRef.current, {
              status: 'complete',
              updatedAt: new Date(),
              data: data.artifactData,
            })
          }
          break

        case 'done':
          // Streaming complete
          if (currentAiMessageIdRef.current) {
            updateMessage(currentAiMessageIdRef.current, {
              streaming: false,
              artifactId: currentArtifactIdRef.current || undefined,
            })
          }
          setIsStreaming(false)
          setConnectionStatus('disconnected')
          cleanup()
          break

        case 'error':
          // Error event
          setConnectionError(data.error || 'Unknown error occurred')
          if (currentAiMessageIdRef.current) {
            updateMessage(currentAiMessageIdRef.current, {
              content: data.error || 'An error occurred while processing your request.',
              streaming: false,
            })
          }
          if (currentArtifactIdRef.current) {
            updateArtifact(currentArtifactIdRef.current, {
              status: 'error',
            })
          }
          setIsStreaming(false)
          setConnectionStatus('error')
          cleanup()
          break
      }
    } catch {
      // JSON parse error - ignore malformed events
    }
  }, [addArtifact, cleanup, updateArtifact, updateMessage])

  /**
   * Schedule reconnection with exponential backoff
   */
  const scheduleReconnect = useCallback((taskId: string, content: string) => {
    if (isUnmountedRef.current) return
    if (reconnectAttempts >= maxReconnectAttempts) {
      setConnectionError(`Failed to connect after ${maxReconnectAttempts} attempts`)
      setConnectionStatus('error')
      setIsStreaming(false)
      return
    }

    const delay = calculateBackoffDelay(reconnectAttempts, initialReconnectDelay, maxReconnectDelay)

    reconnectTimeoutRef.current = setTimeout(() => {
      if (!isUnmountedRef.current) {
        setReconnectAttempts((prev) => prev + 1)
        connectSSE(taskId, content)
      }
    }, delay)
  }, [reconnectAttempts, maxReconnectAttempts, initialReconnectDelay, maxReconnectDelay])

  /**
   * Connect to SSE endpoint
   */
  const connectSSE = useCallback((taskId: string, content: string) => {
    if (isUnmountedRef.current) return

    cleanup()
    setConnectionStatus('connecting')
    setConnectionError(null)

    try {
      // Build SSE URL with query parameters
      const url = new URL(`${baseUrl}/api/stream/${taskId}`)
      url.searchParams.set('message', encodeURIComponent(content))

      const eventSource = new EventSource(url.toString())
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        if (isUnmountedRef.current) {
          eventSource.close()
          return
        }
        setConnectionStatus('connected')
        setReconnectAttempts(0)
        setConnectionError(null)
      }

      eventSource.onmessage = handleSSEEvent

      eventSource.onerror = () => {
        if (isUnmountedRef.current) {
          eventSource.close()
          return
        }

        eventSource.close()
        eventSourceRef.current = null

        // Only attempt reconnect if we were streaming
        if (isStreaming) {
          setConnectionStatus('connecting')
          scheduleReconnect(taskId, content)
        } else {
          setConnectionStatus('error')
          setConnectionError('Connection failed')
        }
      }
    } catch (error) {
      setConnectionStatus('error')
      setConnectionError(error instanceof Error ? error.message : 'Failed to connect')
      setIsStreaming(false)
    }
  }, [baseUrl, cleanup, handleSSEEvent, isStreaming, scheduleReconnect])

  /**
   * Send a message (mock mode)
   */
  const sendMessageMock = useCallback(
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
        currentAiMessageIdRef.current = aiMessageId
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
        const mockDataGenerator = mockDataGenerators[artifactType]
        const mockData = mockDataGenerator ? mockDataGenerator() : {}

        // 5. Create artifact (streaming)
        const artifactId = nanoid()
        currentArtifactIdRef.current = artifactId
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
        currentAiMessageIdRef.current = null
        currentArtifactIdRef.current = null
      }
    },
    [addMessage, updateMessage, addArtifact, updateArtifact]
  )

  /**
   * Send a message (real SSE mode)
   */
  const sendMessageSSE = useCallback(
    async (content: string, taskId?: string) => {
      const effectiveTaskId = taskId || nanoid()

      setIsStreaming(true)
      setReconnectAttempts(0)
      setConnectionError(null)

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
      currentAiMessageIdRef.current = aiMessageId
      const aiMessage: ChatMessage = {
        id: aiMessageId,
        sender: 'ai',
        content: '',
        timestamp: new Date(),
        streaming: true,
      }
      addMessage(aiMessage)

      // 3. Connect to SSE endpoint
      connectSSE(effectiveTaskId, content)
    },
    [addMessage, connectSSE]
  )

  /**
   * Send a message - dispatches to mock or real SSE mode
   */
  const sendMessage = useCallback(
    async (content: string, taskId?: string) => {
      if (mockMode) {
        return sendMessageMock(content)
      }
      return sendMessageSSE(content, taskId)
    },
    [mockMode, sendMessageMock, sendMessageSSE]
  )

  return {
    sendMessage,
    isStreaming,
    connectionStatus,
    disconnect,
    reconnectAttempts,
    connectionError,
  }
}

/**
 * Default export for convenience
 */
export default useStreamingChat
