/**
 * Real-time synchronization hook for Supabase agent messages
 *
 * Subscribes to Supabase Realtime channel for a specific task
 * and automatically adds new agent messages to the chat store.
 *
 * @module hooks/useRealtimeSync
 */

import { useEffect, useRef } from 'react'
import type { RealtimeChannel } from '@supabase/supabase-js'
import { supabase } from '../../lib/supabase'
import { useChatStore } from '../stores/useChatStore'
import type { ChatMessage } from '../types/audit'
import type { AgentMessage as SupabaseAgentMessage } from '../types/supabase'

/**
 * Configuration options for the useRealtimeSync hook
 */
interface UseRealtimeSyncOptions {
  /**
   * Whether to automatically start the subscription on mount
   * @default true
   */
  enabled?: boolean

  /**
   * Callback fired when a new message is received
   */
  onMessageReceived?: (message: ChatMessage) => void

  /**
   * Callback fired on subscription error
   */
  onError?: (error: Error) => void

  /**
   * Callback fired on subscription status change
   */
  onStatusChange?: (status: 'SUBSCRIBED' | 'CLOSED' | 'CHANNEL_ERROR') => void
}

/**
 * Hook for real-time synchronization of agent messages from Supabase
 *
 * Subscribes to the Supabase Realtime channel for a specific task ID
 * and automatically adds new messages to the chat store. Handles cleanup
 * on component unmount.
 *
 * @param taskId - The task ID to subscribe to
 * @param options - Configuration options for the subscription
 *
 * @example
 * ```tsx
 * function TaskChat({ taskId }: { taskId: string }) {
 *   useRealtimeSync(taskId, {
 *     enabled: true,
 *     onMessageReceived: (msg) => console.log('New message:', msg),
 *     onError: (error) => console.error('Sync error:', error)
 *   })
 *
 *   return <ChatInterface />
 * }
 * ```
 */
export function useRealtimeSync(
  taskId: string,
  options: UseRealtimeSyncOptions = {}
): void {
  const {
    enabled = true,
    onMessageReceived,
    onError,
    onStatusChange
  } = options

  const channelRef = useRef<RealtimeChannel | null>(null)
  const addMessage = useChatStore((state) => state.addMessage)

  useEffect(() => {
    // Early return if disabled or no taskId
    if (!enabled || !taskId) {
      return
    }

    /**
     * Handle new message from Supabase Realtime
     */
    const handleMessageInsert = (
      payload: {
        new: SupabaseAgentMessage
      }
    ) => {
      try {
        const newMessage = payload.new

        // Convert Supabase message to chat message format
        const chatMessage: ChatMessage = {
          id: newMessage.id,
          sender: 'ai',
          content: newMessage.content,
          timestamp: new Date(newMessage.created_at),
          streaming: false
        }

        // Add to chat store
        addMessage(chatMessage)

        // Call user callback if provided
        onMessageReceived?.(chatMessage)
      } catch (error) {
        const err = error instanceof Error
          ? error
          : new Error('Failed to process incoming message')

        onError?.(err)
      }
    }

    /**
     * Handle subscription status changes
     */
    const handleStatusChange = (status: string) => {
      if (
        status === 'SUBSCRIBED' ||
        status === 'CLOSED' ||
        status === 'CHANNEL_ERROR'
      ) {
        onStatusChange?.(status as 'SUBSCRIBED' | 'CLOSED' | 'CHANNEL_ERROR')
      }
    }

    /**
     * Initialize the subscription
     */
    const initializeSubscription = async () => {
      try {
        // Create channel with unique name based on taskId
        const channel = supabase
          .channel(`task-${taskId}`, {
            config: {
              broadcast: { self: false }
            }
          })
          .on(
            'postgres_changes',
            {
              event: 'INSERT',
              schema: 'public',
              table: 'agent_messages',
              filter: `task_id=eq.${taskId}`
            },
            handleMessageInsert
          )
          .on('status', handleStatusChange)

        // Store channel reference for cleanup
        channelRef.current = channel

        // Subscribe to the channel
        await channel.subscribe((status) => {
          if (status === 'CLOSED') {
            onStatusChange?.('CLOSED')
          }
        })
      } catch (error) {
        const err = error instanceof Error
          ? error
          : new Error('Failed to initialize Realtime subscription')

        onError?.(err)
      }
    }

    // Initialize the subscription
    initializeSubscription()

    // Cleanup on unmount or when taskId changes
    return () => {
      if (channelRef.current) {
        try {
          channelRef.current.unsubscribe()
          channelRef.current = null
        } catch (error) {
          const err = error instanceof Error
            ? error
            : new Error('Failed to unsubscribe from Realtime channel')

          console.error('Cleanup error:', err)
        }
      }
    }
  }, [taskId, enabled, addMessage, onMessageReceived, onError, onStatusChange])
}

/**
 * Utility hook for managing multiple task synchronizations
 *
 * Useful for scenarios where you need to sync multiple tasks simultaneously.
 *
 * @param taskIds - Array of task IDs to subscribe to
 * @param options - Configuration options passed to each subscription
 *
 * @example
 * ```tsx
 * function MultiTaskChat({ taskIds }: { taskIds: string[] }) {
 *   useRealTimeSyncMultiple(taskIds, {
 *     enabled: true,
 *     onError: (error) => toast.error(error.message)
 *   })
 *
 *   return <ChatInterface />
 * }
 * ```
 */
export function useRealtimeSyncMultiple(
  taskIds: string[],
  options: UseRealtimeSyncOptions = {}
): void {
  taskIds.forEach((taskId) => {
    useRealtimeSync(taskId, options)
  })
}
