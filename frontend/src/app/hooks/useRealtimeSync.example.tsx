/**
 * Example usage of useRealtimeSync hook
 *
 * This file demonstrates various ways to use the useRealtimeSync hook
 * for real-time synchronization of agent messages from Supabase.
 *
 * @module hooks/useRealtimeSync.example
 */

import React, { useState, useCallback } from 'react'
import { useRealtimeSync, useRealtimeSyncMultiple } from './useRealtimeSync'
import { useChatStore } from '../stores/useChatStore'
import type { ChatMessage } from '../types/audit'

/**
 * Example 1: Basic usage with a single task
 */
export function BasicTaskChat({ taskId }: { taskId: string }) {
  const messages = useChatStore((state) => state.messages)

  // Subscribe to realtime messages for this task
  useRealtimeSync(taskId, {
    enabled: true,
  })

  return (
    <div className="space-y-2">
      <h2>Task Chat</h2>
      {messages.map((msg) => (
        <div key={msg.id} className="p-2 border rounded">
          <p className="text-sm font-semibold">{msg.sender}</p>
          <p>{msg.content}</p>
          <p className="text-xs text-gray-500">
            {msg.timestamp.toLocaleTimeString()}
          </p>
        </div>
      ))}
    </div>
  )
}

/**
 * Example 2: With error handling
 */
export function TaskChatWithErrorHandling({
  taskId,
}: {
  taskId: string
}) {
  const [error, setError] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('connecting')
  const messages = useChatStore((state) => state.messages)

  const handleError = useCallback((error: Error) => {
    console.error('Realtime sync error:', error)
    setError(error.message)
    setConnectionStatus('error')
  }, [])

  const handleStatusChange = useCallback(
    (status: 'SUBSCRIBED' | 'CLOSED' | 'CHANNEL_ERROR') => {
      if (status === 'SUBSCRIBED') {
        setConnectionStatus('connected')
        setError(null)
      } else if (status === 'CLOSED') {
        setConnectionStatus('disconnected')
      } else if (status === 'CHANNEL_ERROR') {
        setConnectionStatus('error')
      }
    },
    []
  )

  // Subscribe with error and status callbacks
  useRealtimeSync(taskId, {
    enabled: true,
    onError: handleError,
    onStatusChange: handleStatusChange,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2>Task Chat</h2>
        <span
          className={`inline-block w-2 h-2 rounded-full \${
            connectionStatus === 'connected'
              ? 'bg-green-500'
              : connectionStatus === 'connecting'
                ? 'bg-yellow-500'
                : connectionStatus === 'disconnected'
                  ? 'bg-gray-500'
                  : 'bg-red-500'
          }`}
        />
        <span className="text-xs text-gray-500">{connectionStatus}</span>
      </div>

      {error && (
        <div className="p-2 bg-red-100 border border-red-400 rounded text-red-700">
          Error: {error}
        </div>
      )}

      <div className="space-y-2">
        {messages.map((msg) => (
          <div key={msg.id} className="p-2 border rounded">
            <p className="text-sm font-semibold">{msg.sender}</p>
            <p>{msg.content}</p>
            <p className="text-xs text-gray-500">
              {msg.timestamp.toLocaleTimeString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Example 3: With message notification
 */
export function TaskChatWithNotifications({
  taskId,
}: {
  taskId: string
}) {
  const [messageCount, setMessageCount] = useState(0)
  const messages = useChatStore((state) => state.messages)

  const handleMessageReceived = useCallback((message: ChatMessage) => {
    console.log('New message received:', message)
    setMessageCount((prev) => prev + 1)

    // Show notification (example with browser notification API)
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('New Message', {
        body: message.content.substring(0, 100),
        tag: 'task-message',
      })
    }
  }, [])

  // Subscribe with message callback
  useRealtimeSync(taskId, {
    enabled: true,
    onMessageReceived: handleMessageReceived,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2>Task Chat</h2>
        <div className="bg-blue-100 px-3 py-1 rounded-full text-sm">
          {messageCount} new messages
        </div>
      </div>

      <div className="space-y-2">
        {messages.map((msg) => (
          <div key={msg.id} className="p-2 border rounded">
            <p className="text-sm font-semibold">{msg.sender}</p>
            <p>{msg.content}</p>
            <p className="text-xs text-gray-500">
              {msg.timestamp.toLocaleTimeString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Example 4: Conditionally enable/disable sync
 */
export function TaskChatWithToggle({
  taskId,
}: {
  taskId: string
}) {
  const [isSyncEnabled, setIsSyncEnabled] = useState(true)
  const messages = useChatStore((state) => state.messages)

  // Subscribe only when enabled
  useRealtimeSync(taskId, {
    enabled: isSyncEnabled,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2>Task Chat</h2>
        <button
          onClick={() => setIsSyncEnabled(!isSyncEnabled)}
          className={`px-3 py-1 rounded text-sm font-medium \${
            isSyncEnabled
              ? 'bg-green-500 text-white'
              : 'bg-gray-300 text-gray-700'
          }`}
        >
          {isSyncEnabled ? 'Sync Enabled' : 'Sync Disabled'}
        </button>
      </div>

      <div className="space-y-2">
        {messages.map((msg) => (
          <div key={msg.id} className="p-2 border rounded">
            <p className="text-sm font-semibold">{msg.sender}</p>
            <p>{msg.content}</p>
            <p className="text-xs text-gray-500">
              {msg.timestamp.toLocaleTimeString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Example 5: Multiple task synchronization
 */
export function MultiTaskChat({
  taskIds,
}: {
  taskIds: string[]
}) {
  const messages = useChatStore((state) => state.messages)

  // Subscribe to multiple tasks simultaneously
  useRealtimeSyncMultiple(taskIds, {
    enabled: true,
  })

  return (
    <div className="space-y-4">
      <h2>All Tasks Chat</h2>
      <p className="text-sm text-gray-600">
        Syncing {taskIds.length} tasks: {taskIds.join(', ')}
      </p>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {messages.length === 0 ? (
          <p className="text-gray-500">No messages yet</p>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="p-2 border rounded">
              <p className="text-sm font-semibold">{msg.sender}</p>
              <p>{msg.content}</p>
              <p className="text-xs text-gray-500">
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

/**
 * Example 6: Complete dashboard with all features
 */
export function AdvancedTaskDashboard({
  taskId,
}: {
  taskId: string
}) {
  const [error, setError] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('connecting')
  const [messageCount, setMessageCount] = useState(0)
  const [isSyncEnabled, setIsSyncEnabled] = useState(true)
  const messages = useChatStore((state) => state.messages)
  const clearMessages = useChatStore((state) => state.clearMessages)

  const handleMessageReceived = useCallback((message: ChatMessage) => {
    setMessageCount((prev) => prev + 1)
  }, [])

  const handleError = useCallback((error: Error) => {
    console.error('Realtime sync error:', error)
    setError(error.message)
    setConnectionStatus('error')
  }, [])

  const handleStatusChange = useCallback(
    (status: 'SUBSCRIBED' | 'CLOSED' | 'CHANNEL_ERROR') => {
      if (status === 'SUBSCRIBED') {
        setConnectionStatus('connected')
        setError(null)
      } else if (status === 'CLOSED') {
        setConnectionStatus('disconnected')
      } else if (status === 'CHANNEL_ERROR') {
        setConnectionStatus('error')
      }
    },
    []
  )

  useRealtimeSync(taskId, {
    enabled: isSyncEnabled,
    onMessageReceived: handleMessageReceived,
    onError: handleError,
    onStatusChange: handleStatusChange,
  })

  return (
    <div className="p-4 space-y-4 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Task: {taskId}</h1>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-3 h-3 rounded-full \${
              connectionStatus === 'connected'
                ? 'bg-green-500'
                : connectionStatus === 'connecting'
                  ? 'bg-yellow-500'
                  : connectionStatus === 'disconnected'
                    ? 'bg-gray-500'
                    : 'bg-red-500'
            }`}
          />
          <span className="text-sm font-medium">{connectionStatus}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-2">
        <button
          onClick={() => setIsSyncEnabled(!isSyncEnabled)}
          className={`px-3 py-2 rounded font-medium text-sm \${
            isSyncEnabled
              ? 'bg-green-500 text-white'
              : 'bg-gray-300 text-gray-700'
          }`}
        >
          {isSyncEnabled ? 'Sync: ON' : 'Sync: OFF'}
        </button>
        <button
          onClick={() => clearMessages()}
          className="px-3 py-2 rounded font-medium text-sm bg-gray-500 text-white hover:bg-gray-600"
        >
          Clear Messages
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-100 border border-red-400 rounded text-red-700">
          <p className="font-medium">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Message Count */}
      <div className="p-3 bg-blue-100 border border-blue-400 rounded">
        <p className="text-sm font-medium">
          Total Messages: {messages.length}
        </p>
        <p className="text-xs text-blue-700">
          New messages since page load: {messageCount}
        </p>
      </div>

      {/* Messages */}
      <div className="border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-4">Messages</h2>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No messages yet. Waiting for agent messages...
            </p>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`p-3 rounded border \${
                  msg.sender === 'ai'
                    ? 'bg-gray-50 border-gray-200'
                    : 'bg-blue-50 border-blue-200'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-semibold capitalize">
                    {msg.sender}
                  </p>
                  <p className="text-xs text-gray-500">
                    {msg.timestamp.toLocaleTimeString()}
                  </p>
                </div>
                <p className="text-sm">{msg.content}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
