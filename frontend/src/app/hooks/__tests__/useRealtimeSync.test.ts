/**
 * Unit tests for useRealtimeSync hook
 *
 * Tests subscription management, message handling, error cases,
 * and cleanup behavior.
 *
 * @module hooks/__tests__/useRealtimeSync.test
 */

import { renderHook } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import type { RealtimeChannel } from '@supabase/supabase-js'
import { useRealtimeSync, useRealtimeSyncMultiple } from '../useRealtimeSync'
import { useChatStore } from '../../stores/useChatStore'
import * as supabaseModule from '../../../lib/supabase'

// Mock Supabase module
vi.mock('../../../lib/supabase', () => ({
  supabase: {
    channel: vi.fn(),
  },
}))

// Mock chat store
vi.mock('../../stores/useChatStore', () => ({
  useChatStore: vi.fn(),
}))

describe('useRealtimeSync', () => {
  let mockAddMessage: ReturnType<typeof vi.fn>
  let mockChannel: Partial<RealtimeChannel>

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()

    // Setup mock addMessage
    mockAddMessage = vi.fn()
    ;(useChatStore as ReturnType<typeof vi.fn>).mockReturnValue(mockAddMessage)

    // Setup mock channel
    mockChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockResolvedValue(undefined),
      unsubscribe: vi.fn().mockResolvedValue(undefined),
    }

    ;(supabaseModule.supabase.channel as ReturnType<typeof vi.fn>).mockReturnValue(
      mockChannel
    )
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize subscription with correct channel name', () => {
    const taskId = 'task-123'

    renderHook(() => useRealtimeSync(taskId))

    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      `task-${taskId}`,
      expect.any(Object)
    )
  })

  it('should set up INSERT event listener for agent_messages', () => {
    const taskId = 'task-123'

    renderHook(() => useRealtimeSync(taskId))

    expect(mockChannel.on).toHaveBeenCalledWith(
      'postgres_changes',
      expect.objectContaining({
        event: 'INSERT',
        schema: 'public',
        table: 'agent_messages',
        filter: `task_id=eq.${taskId}`,
      }),
      expect.any(Function)
    )
  })

  it('should set up status change listener', () => {
    const taskId = 'task-123'

    renderHook(() => useRealtimeSync(taskId))

    expect(mockChannel.on).toHaveBeenCalledWith('status', expect.any(Function))
  })

  it('should call subscribe on the channel', async () => {
    const taskId = 'task-123'

    renderHook(() => useRealtimeSync(taskId))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(mockChannel.subscribe).toHaveBeenCalled()
  })

  it('should add message to chat store on INSERT event', async () => {
    const taskId = 'task-123'
    let messageHandler: any

    ;(mockChannel.on as ReturnType<typeof vi.fn>).mockImplementation(
      (event, config, handler) => {
        if (event === 'postgres_changes' && config.event === 'INSERT') {
          messageHandler = handler
        }
        return mockChannel
      }
    )

    renderHook(() => useRealtimeSync(taskId))

    await new Promise((resolve) => setTimeout(resolve, 0))

    // Simulate incoming message
    const payload = {
      new: {
        id: 'msg-1',
        task_id: taskId,
        agent_role: 'supervisor' as const,
        content: 'Test message',
        message_type: 'response' as const,
        metadata: {},
        created_at: '2024-01-06T12:00:00.000Z',
      },
    }

    messageHandler(payload)

    expect(mockAddMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'msg-1',
        sender: 'ai',
        content: 'Test message',
        streaming: false,
      })
    )
  })

  it('should convert timestamp to Date object', async () => {
    const taskId = 'task-123'
    let messageHandler: any

    ;(mockChannel.on as ReturnType<typeof vi.fn>).mockImplementation(
      (event, config, handler) => {
        if (event === 'postgres_changes' && config.event === 'INSERT') {
          messageHandler = handler
        }
        return mockChannel
      }
    )

    renderHook(() => useRealtimeSync(taskId))

    await new Promise((resolve) => setTimeout(resolve, 0))

    const timestamp = '2024-01-06T12:30:45.000Z'
    const payload = {
      new: {
        id: 'msg-1',
        task_id: taskId,
        agent_role: 'supervisor' as const,
        content: 'Test message',
        message_type: 'response' as const,
        metadata: {},
        created_at: timestamp,
      },
    }

    messageHandler(payload)

    const addedMessage = mockAddMessage.mock.calls[0][0]
    expect(addedMessage.timestamp).toBeInstanceOf(Date)
    expect(addedMessage.timestamp.toISOString()).toBe(timestamp)
  })

  it('should call onMessageReceived callback when message arrives', async () => {
    const taskId = 'task-123'
    const onMessageReceived = vi.fn()
    let messageHandler: any

    ;(mockChannel.on as ReturnType<typeof vi.fn>).mockImplementation(
      (event, config, handler) => {
        if (event === 'postgres_changes' && config.event === 'INSERT') {
          messageHandler = handler
        }
        return mockChannel
      }
    )

    renderHook(() => useRealtimeSync(taskId, { onMessageReceived }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    const payload = {
      new: {
        id: 'msg-1',
        task_id: taskId,
        agent_role: 'supervisor' as const,
        content: 'Test message',
        message_type: 'response' as const,
        metadata: {},
        created_at: '2024-01-06T12:00:00.000Z',
      },
    }

    messageHandler(payload)

    expect(onMessageReceived).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'msg-1',
        content: 'Test message',
      })
    )
  })

  it('should call onError callback on message processing error', async () => {
    const taskId = 'task-123'
    const onError = vi.fn()
    let messageHandler: any

    ;(mockChannel.on as ReturnType<typeof vi.fn>).mockImplementation(
      (event, config, handler) => {
        if (event === 'postgres_changes' && config.event === 'INSERT') {
          messageHandler = handler
        }
        return mockChannel
      }
    )

    renderHook(() => useRealtimeSync(taskId, { onError }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    // Send invalid payload to trigger error
    messageHandler({ new: null })

    expect(onError).toHaveBeenCalled()
  })

  it('should call onStatusChange callback on status changes', async () => {
    const taskId = 'task-123'
    const onStatusChange = vi.fn()
    let statusHandler: any

    ;(mockChannel.on as ReturnType<typeof vi.fn>).mockImplementation(
      (event, handler) => {
        if (event === 'status') {
          statusHandler = handler
        }
        return mockChannel
      }
    )

    renderHook(() => useRealtimeSync(taskId, { onStatusChange }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    statusHandler('SUBSCRIBED')

    expect(onStatusChange).toHaveBeenCalledWith('SUBSCRIBED')
  })

  it('should unsubscribe on unmount', () => {
    const taskId = 'task-123'

    const { unmount } = renderHook(() => useRealtimeSync(taskId))

    unmount()

    expect(mockChannel.unsubscribe).toHaveBeenCalled()
  })

  it('should not subscribe if enabled is false', async () => {
    const taskId = 'task-123'

    renderHook(() => useRealtimeSync(taskId, { enabled: false }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(mockChannel.subscribe).not.toHaveBeenCalled()
  })

  it('should not subscribe if taskId is empty', async () => {
    renderHook(() => useRealtimeSync('', { enabled: true }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(mockChannel.subscribe).not.toHaveBeenCalled()
  })

  it('should resubscribe when taskId changes', async () => {
    const { rerender } = renderHook(
      ({ taskId }) => useRealtimeSync(taskId),
      { initialProps: { taskId: 'task-1' } }
    )

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      'task-task-1',
      expect.any(Object)
    )

    rerender({ taskId: 'task-2' })

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      'task-task-2',
      expect.any(Object)
    )
    expect(mockChannel.unsubscribe).toHaveBeenCalled()
  })

  it('should handle subscription error gracefully', async () => {
    const taskId = 'task-123'
    const onError = vi.fn()

    const subscribeError = new Error('Subscription failed')
    ;(mockChannel.subscribe as ReturnType<typeof vi.fn>).mockRejectedValue(
      subscribeError
    )

    renderHook(() => useRealtimeSync(taskId, { onError }))

    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(onError).toHaveBeenCalled()
  })

  it('should handle cleanup error gracefully', () => {
    const taskId = 'task-123'

    ;(mockChannel.unsubscribe as ReturnType<typeof vi.fn>).mockImplementation(
      () => {
        throw new Error('Unsubscribe failed')
      }
    )

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { unmount } = renderHook(() => useRealtimeSync(taskId))

    unmount()

    expect(consoleSpy).toHaveBeenCalled()

    consoleSpy.mockRestore()
  })
})

describe('useRealtimeSyncMultiple', () => {
  let mockAddMessage: ReturnType<typeof vi.fn>
  let mockChannel: Partial<RealtimeChannel>

  beforeEach(() => {
    vi.clearAllMocks()

    mockAddMessage = vi.fn()
    ;(useChatStore as ReturnType<typeof vi.fn>).mockReturnValue(mockAddMessage)

    mockChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockResolvedValue(undefined),
      unsubscribe: vi.fn().mockResolvedValue(undefined),
    }

    ;(supabaseModule.supabase.channel as ReturnType<typeof vi.fn>).mockReturnValue(
      mockChannel
    )
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should subscribe to multiple tasks', async () => {
    const taskIds = ['task-1', 'task-2', 'task-3']

    renderHook(() => useRealtimeSyncMultiple(taskIds))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(supabaseModule.supabase.channel).toHaveBeenCalledTimes(3)
    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      'task-task-1',
      expect.any(Object)
    )
    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      'task-task-2',
      expect.any(Object)
    )
    expect(supabaseModule.supabase.channel).toHaveBeenCalledWith(
      'task-task-3',
      expect.any(Object)
    )
  })

  it('should handle empty task array', async () => {
    renderHook(() => useRealtimeSyncMultiple([]))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(supabaseModule.supabase.channel).not.toHaveBeenCalled()
  })

  it('should pass options to all subscriptions', async () => {
    const taskIds = ['task-1', 'task-2']
    const onError = vi.fn()

    renderHook(() => useRealtimeSyncMultiple(taskIds, { onError }))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(supabaseModule.supabase.channel).toHaveBeenCalledTimes(2)
  })
})
