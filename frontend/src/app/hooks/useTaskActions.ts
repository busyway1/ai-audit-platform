import { useState, useCallback } from 'react'

/**
 * Response type from task approval endpoint
 */
interface TaskApprovalResponse {
  success: boolean
  message: string
  data?: {
    threadId: string
    approved: boolean
    approvedAt: string
  }
}

/**
 * Hook for task approval actions (HITL - Human-in-the-Loop)
 *
 * Features:
 * - POST request to /api/tasks/approve endpoint
 * - Manages approval loading state
 * - Handles errors gracefully
 * - Type-safe response handling
 * - Returns structured approval result
 *
 * Usage:
 * ```typescript
 * const { approveTask, isApproving, error } = useTaskActions()
 * await approveTask(task.threadId, true)
 * ```
 */
export function useTaskActions() {
  const [isApproving, setIsApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const apiUrl = import.meta.env.VITE_API_URL

  const approveTask = useCallback(
    async (threadId: string, approved: boolean): Promise<TaskApprovalResponse | null> => {
      setIsApproving(true)
      setError(null)

      try {
        const response = await fetch(`${apiUrl}/api/tasks/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thread_id: threadId, approved }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          const errorMessage = errorData.message || `Approval failed with status ${response.status}`
          setError(errorMessage)
          throw new Error(errorMessage)
        }

        const result: TaskApprovalResponse = await response.json()
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        setError(errorMessage)
        return null
      } finally {
        setIsApproving(false)
      }
    },
    [apiUrl]
  )

  return { approveTask, isApproving, error }
}
