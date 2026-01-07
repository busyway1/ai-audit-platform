/**
 * Usage Examples for useTaskActions Hook
 *
 * This file demonstrates how to use the useTaskActions hook
 * for task approval workflows (HITL - Human-in-the-Loop)
 */

import { useTaskActions } from './useTaskActions'

/**
 * Example 1: Simple Approval Button
 * Basic usage in a task card component
 */
export function TaskApprovalButton({ taskId, threadId }: { taskId: string; threadId: string }) {
  const { approveTask, isApproving, error } = useTaskActions()

  const handleApprove = async () => {
    const result = await approveTask(threadId, true)
    if (result?.success) {
      console.log('Task approved:', result.data)
      // Update UI, refresh task status, etc.
    }
  }

  const handleReject = async () => {
    const result = await approveTask(threadId, false)
    if (result?.success) {
      console.log('Task rejected:', result.data)
      // Update UI, refresh task status, etc.
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={handleApprove}
        disabled={isApproving}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
      >
        {isApproving ? 'Approving...' : 'Approve'}
      </button>
      <button
        onClick={handleReject}
        disabled={isApproving}
        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
      >
        {isApproving ? 'Rejecting...' : 'Reject'}
      </button>
      {error && <div className="text-red-600 text-sm">{error}</div>}
    </div>
  )
}

/**
 * Example 2: Approval with Feedback
 * Collect user feedback when approving/rejecting
 */
export function TaskApprovalWithFeedback({
  threadId,
  onApprovalComplete,
}: {
  threadId: string
  onApprovalComplete?: (approved: boolean) => void
}) {
  const [feedback, setFeedback] = React.useState('')
  const { approveTask, isApproving, error } = useTaskActions()

  const handleSubmit = async (approved: boolean) => {
    // Send approval with feedback to backend
    const result = await approveTask(threadId, approved)

    if (result?.success) {
      // Here you might send feedback separately or it could be included in the request
      console.log('Approval submitted with feedback:', feedback)
      setFeedback('')
      onApprovalComplete?.(approved)
    }
  }

  return (
    <div className="space-y-4">
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Add optional feedback..."
        className="w-full p-2 border rounded"
        rows={3}
        disabled={isApproving}
      />
      <div className="flex gap-2">
        <button
          onClick={() => handleSubmit(true)}
          disabled={isApproving}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          {isApproving ? 'Processing...' : 'Approve'}
        </button>
        <button
          onClick={() => handleSubmit(false)}
          disabled={isApproving}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
        >
          {isApproving ? 'Processing...' : 'Reject'}
        </button>
      </div>
      {error && <div className="text-red-600 text-sm">{error}</div>}
    </div>
  )
}

/**
 * Example 3: Batch Approval
 * Approve multiple tasks in sequence or parallel
 */
export function TaskBatchApproval({ threadIds }: { threadIds: string[] }) {
  const [approvalStatus, setApprovalStatus] = React.useState<
    Record<string, 'pending' | 'approved' | 'rejected' | 'error'>
  >({})
  const { approveTask, isApproving } = useTaskActions()

  const handleBatchApprove = async (approved: boolean) => {
    // Track status for each thread
    const statuses: typeof approvalStatus = {}

    for (const threadId of threadIds) {
      statuses[threadId] = 'pending'
    }
    setApprovalStatus(statuses)

    // Process each approval sequentially
    for (const threadId of threadIds) {
      const result = await approveTask(threadId, approved)

      if (result?.success) {
        setApprovalStatus((prev) => ({
          ...prev,
          [threadId]: approved ? 'approved' : 'rejected',
        }))
      } else {
        setApprovalStatus((prev) => ({
          ...prev,
          [threadId]: 'error',
        }))
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => handleBatchApprove(true)}
          disabled={isApproving}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          Approve All
        </button>
        <button
          onClick={() => handleBatchApprove(false)}
          disabled={isApproving}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
        >
          Reject All
        </button>
      </div>

      {/* Status display */}
      <div className="space-y-2">
        {threadIds.map((threadId) => {
          const status = approvalStatus[threadId] || 'pending'
          const statusColor = {
            pending: 'gray',
            approved: 'green',
            rejected: 'yellow',
            error: 'red',
          }[status]

          return (
            <div
              key={threadId}
              className={`p-2 bg-${statusColor}-100 border border-${statusColor}-300 rounded`}
            >
              <div className="font-medium">{threadId}</div>
              <div className="text-sm capitalize">{status}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Example 4: Integration with Task Store
 * Update global state after approval
 */
import React from 'react'
// Assuming you have a task store
// import { useTaskStore } from '../stores/useTaskStore'

export function TaskApprovalWithStore({ threadId }: { threadId: string }) {
  // const { updateTaskStatus } = useTaskStore()
  const { approveTask, isApproving, error } = useTaskActions()

  const handleApprove = async () => {
    const result = await approveTask(threadId, true)

    if (result?.success) {
      // Update store with new status
      // updateTaskStatus(threadId, 'approved')

      // Or trigger a refetch of task data
      console.log('Approval successful, consider refetching task data')
    }
  }

  return (
    <button onClick={handleApprove} disabled={isApproving}>
      {isApproving ? 'Approving...' : 'Approve Task'}
      {error && <span className="text-red-600"> - {error}</span>}
    </button>
  )
}

/**
 * Return Type Definition
 *
 * The hook returns an object with these properties:
 *
 * {
 *   // Function to approve/reject a task
 *   approveTask: (threadId: string, approved: boolean) => Promise<TaskApprovalResponse | null>
 *
 *   // Loading state while approval is in progress
 *   isApproving: boolean
 *
 *   // Error message if approval failed
 *   error: string | null
 * }
 *
 * TaskApprovalResponse structure:
 * {
 *   success: boolean
 *   message: string
 *   data?: {
 *     threadId: string
 *     approved: boolean
 *     approvedAt: string (ISO timestamp)
 *   }
 * }
 */
