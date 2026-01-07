# useRealtimeSync Hook Documentation

Real-time synchronization hook for Supabase Realtime subscriptions with agent messages.

## Overview

The `useRealtimeSync` hook provides a robust solution for subscribing to real-time agent messages from Supabase. It automatically handles:

- Subscription lifecycle management
- Message transformation and storage
- Error handling and recovery
- Connection status monitoring
- Cleanup on unmount

## Files

- **useRealtimeSync.ts** - Main hook implementation (5.7 KB)
- **useRealtimeSync.test.ts** - Comprehensive test suite (11 KB)
- **useRealtimeSync.example.tsx** - Usage examples (12 KB)

## Core Features

### 1. Single Task Subscription

Subscribe to a single task's real-time messages:

```tsx
import { useRealtimeSync } from './hooks/useRealtimeSync'

function TaskChat({ taskId }: { taskId: string }) {
  useRealtimeSync(taskId)
  // Component automatically receives real-time updates
}
```

### 2. Error Handling

Handle subscription errors gracefully:

```tsx
useRealtimeSync(taskId, {
  onError: (error) => {
    console.error('Sync failed:', error)
    showErrorNotification(error.message)
  }
})
```

### 3. Status Monitoring

Track connection status:

```tsx
useRealtimeSync(taskId, {
  onStatusChange: (status) => {
    if (status === 'SUBSCRIBED') {
      setConnected(true)
    } else if (status === 'CLOSED') {
      setConnected(false)
    }
  }
})
```

### 4. Message Notifications

React to new messages:

```tsx
useRealtimeSync(taskId, {
  onMessageReceived: (message) => {
    console.log('New message:', message)
    playNotificationSound()
  }
})
```

### 5. Conditional Subscriptions

Enable/disable subscriptions dynamically:

```tsx
const [isSyncEnabled, setIsSyncEnabled] = useState(true)

useRealtimeSync(taskId, {
  enabled: isSyncEnabled
})

// Toggle sync on/off
<button onClick={() => setIsSyncEnabled(!isSyncEnabled)}>
  Toggle Sync
</button>
```

### 6. Multiple Task Subscriptions

Subscribe to multiple tasks simultaneously:

```tsx
import { useRealtimeSyncMultiple } from './hooks/useRealtimeSync'

function MultiTaskDashboard({ taskIds }: { taskIds: string[] }) {
  useRealtimeSyncMultiple(taskIds, {
    enabled: true,
    onError: handleError
  })
}
```

## API Reference

### useRealtimeSync

Main hook for single task real-time synchronization.

#### Signature

```typescript
function useRealtimeSync(
  taskId: string,
  options?: UseRealtimeSyncOptions
): void
```

#### Parameters

- **taskId** (string, required) - The task ID to subscribe to
- **options** (UseRealtimeSyncOptions, optional) - Configuration options

#### Options

```typescript
interface UseRealtimeSyncOptions {
  enabled?: boolean                                    // Default: true
  onMessageReceived?: (message: ChatMessage) => void  // Called when new message arrives
  onError?: (error: Error) => void                    // Called on subscription error
  onStatusChange?: (status: SubscriptionStatus) => void // Called on status change
}

type SubscriptionStatus = 'SUBSCRIBED' | 'CLOSED' | 'CHANNEL_ERROR'
```

### useRealtimeSyncMultiple

Utility hook for subscribing to multiple tasks.

#### Signature

```typescript
function useRealtimeSyncMultiple(
  taskIds: string[],
  options?: UseRealtimeSyncOptions
): void
```

#### Parameters

- **taskIds** (string[], required) - Array of task IDs to subscribe to
- **options** (UseRealtimeSyncOptions, optional) - Configuration options passed to each subscription

## Implementation Details

### Architecture

```
Component Mounts
    |
    v
useRealtimeSync Hook
    |
    +-- Create Supabase Channel
    |       |
    |       +-- Listen for postgres_changes (INSERT events)
    |       +-- Listen for status changes
    |
    +-- Subscribe to Channel
    |
    +-- Message Handler
    |       |
    |       +-- Receive payload from Supabase
    |       +-- Transform to ChatMessage format
    |       +-- Add to useChatStore
    |       +-- Call onMessageReceived callback
    |
    +-- Status Handler
    |       |
    |       +-- Track connection status
    |       +-- Call onStatusChange callback
    |
Component Unmounts
    |
    v
Cleanup
    |
    +-- Unsubscribe from Channel
    +-- Clear channel reference
```

### Message Flow

1. **Supabase Realtime** - Agent message inserted in database
2. **Postgres Change Event** - Supabase sends INSERT notification
3. **Message Handler** - Hook receives payload
4. **Transformation** - Payload converted to ChatMessage format:
   - Supabase timestamp (string) → Date object
   - agent_role preserved for future use
   - sender set to 'ai'
   - streaming flag set to false
5. **Storage** - Message added to useChatStore
6. **Callbacks** - Optional callbacks fired
   - onMessageReceived with transformed message
   - Component re-renders with new message

### Data Mapping

Supabase `agent_messages` table → Chat Store format:

```typescript
// Supabase (Database)
{
  id: string
  task_id: string
  agent_role: 'supervisor' | 'research' | 'analysis' | 'documentation'
  content: string
  message_type: 'request' | 'response' | 'notification' | 'error'
  metadata: Json
  timestamp: string // ISO-8601
}

// Transformed to ChatMessage
{
  id: string
  sender: 'ai' // Fixed for all agent messages
  content: string
  timestamp: Date // Converted from ISO string
  streaming: boolean // Always false on initial sync
}
```

## Test Coverage

Comprehensive test suite with 18 test cases covering:

### useRealtimeSync Tests (14 tests)
- Channel initialization and naming
- Event listener setup
- Subscribe/unsubscribe lifecycle
- Message handling and transformation
- Timestamp conversion
- Error handling
- Status change monitoring
- Cleanup behavior
- Conditional enabling
- Resubscription on taskId change

### useRealtimeSyncMultiple Tests (4 tests)
- Multiple task subscription
- Empty task array handling
- Option propagation
- Array iteration

### Test Commands

```bash
# Run all tests
npm test

# Run only useRealtimeSync tests
npm test useRealtimeSync

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

## Integration Examples

### Example 1: Basic Chat Interface

```tsx
function TaskChat({ taskId }: { taskId: string }) {
  const messages = useChatStore((state) => state.messages)

  useRealtimeSync(taskId)

  return (
    <div className="chat-container">
      {messages.map((msg) => (
        <div key={msg.id} className="message">
          {msg.content}
        </div>
      ))}
    </div>
  )
}
```

### Example 2: With Connection Status

```tsx
function TaskChatWithStatus({ taskId }: { taskId: string }) {
  const [status, setStatus] = useState('connecting')

  useRealtimeSync(taskId, {
    onStatusChange: setStatus
  })

  return (
    <div>
      <div className={`status-badge ${status}`}>
        {status}
      </div>
      {/* Chat content */}
    </div>
  )
}
```

### Example 3: Complete Dashboard

See `useRealtimeSync.example.tsx` for 6 complete working examples:
- BasicTaskChat - Simple usage
- TaskChatWithErrorHandling - Error and status handling
- TaskChatWithNotifications - Message notifications
- TaskChatWithToggle - Enable/disable sync
- MultiTaskChat - Multiple task subscriptions
- AdvancedTaskDashboard - All features combined

## Best Practices

### 1. Always Provide a TaskId

```tsx
// Good - taskId is defined
useRealtimeSync(taskId)

// Bad - empty string won't subscribe
useRealtimeSync('')

// Good - check taskId before hook
if (taskId) {
  useRealtimeSync(taskId)
}
```

### 2. Handle Errors Gracefully

```tsx
useRealtimeSync(taskId, {
  onError: (error) => {
    // Log for debugging
    console.error('Sync error:', error)

    // Show user-friendly message
    toast.error('Failed to sync messages')

    // Optional: Implement retry logic
    retrySubscription()
  }
})
```

### 3. Monitor Connection Status

```tsx
useRealtimeSync(taskId, {
  onStatusChange: (status) => {
    if (status === 'SUBSCRIBED') {
      // Green light - syncing works
      updateConnectionUI('connected')
    } else if (status === 'CHANNEL_ERROR') {
      // Red light - something wrong
      updateConnectionUI('error')
    }
  }
})
```

### 4. Avoid Dependencies in Callbacks

```tsx
// Bad - taskId changes cause re-subscription
const taskId = useParams().taskId
useRealtimeSync(taskId, {
  onMessageReceived: (message) => {
    processMessageForTask(taskId) // taskId is stale
  }
})

// Good - capture taskId in stable callback
const onMessageReceived = useCallback((message) => {
  processMessageForTask(message.taskId) // Use message data
}, [])

useRealtimeSync(taskId, { onMessageReceived })
```

### 5. Clean Up Store If Needed

```tsx
function TaskChat({ taskId }: { taskId: string }) {
  const clearMessages = useChatStore((state) => state.clearMessages)

  useRealtimeSync(taskId)

  // Clear old messages when task changes
  useEffect(() => {
    clearMessages()
  }, [taskId, clearMessages])
}
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing Supabase environment variables" | VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set | Check .env.local |
| "Task ID is empty" | taskId prop not provided | Ensure taskId is valid |
| "Subscription failed" | Network or Supabase issue | Retry with exponential backoff |
| "Failed to process incoming message" | Malformed payload | Check database schema |

### Error Recovery

```tsx
const [retryCount, setRetryCount] = useState(0)
const MAX_RETRIES = 3

useRealtimeSync(taskId, {
  enabled: retryCount < MAX_RETRIES,
  onError: (error) => {
    console.error('Attempt failed:', retryCount + 1)
    // Retry after delay
    setTimeout(() => {
      setRetryCount(retryCount + 1)
    }, Math.pow(2, retryCount) * 1000) // Exponential backoff
  }
})
```

## Performance Considerations

### Memory Management

- Channel reference stored in useRef - cleaned up on unmount
- Message handler function created once per render
- Status handler function created once per render

### Subscription Lifecycle

```
Component Mount
  |
  +-- initializeSubscription() [async]
  |       |
  |       +-- Create channel
  |       +-- Register handlers
  |       +-- Subscribe [network call]
  |
  +-- Listen for messages [Realtime stream]
  |
Component Unmount
  |
  +-- Unsubscribe [network call]
  +-- Clear channel reference
```

### Network Impact

- Creates 1 persistent WebSocket connection per taskId
- Sends INSERT events only (minimal bandwidth)
- No polling - event-driven model
- Automatic reconnection handled by Supabase SDK

## Troubleshooting

### Messages not appearing

1. Check taskId is correct
2. Verify Supabase connection (check browser console)
3. Confirm database has `agent_messages` table
4. Check that INSERT events are being triggered

### Subscription not connecting

1. Check .env.local has VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
2. Verify Supabase project is active
3. Check browser console for connection errors
4. Try refreshing the page

### Performance issues

1. Limit number of concurrent subscriptions (use useRealtimeSyncMultiple)
2. Check browser DevTools Network tab for message volume
3. Profile React components with Profiler
4. Consider pagination if many messages

## Future Enhancements

Potential improvements for v2:
- [ ] Message filtering and sorting
- [ ] Automatic message deduplication
- [ ] Configurable reconnection strategies
- [ ] Message history pagination
- [ ] Optimistic updates
- [ ] Offline support with fallback storage
- [ ] Message compression
- [ ] Type-safe message content union types

## Related Documentation

- [Supabase Realtime](https://supabase.com/docs/guides/realtime)
- [useChatStore](./useChatStore.ts)
- [ChatMessage Type](../types/audit.ts)
- [Supabase Types](../types/supabase.ts)

## Support

For issues or questions:
1. Check this documentation
2. Review example files
3. Check test cases for usage patterns
4. Inspect browser console for errors
5. Verify Supabase connectivity

---

**Created**: 2024-01-06  
**Last Updated**: 2024-01-06  
**Version**: 1.0.0
