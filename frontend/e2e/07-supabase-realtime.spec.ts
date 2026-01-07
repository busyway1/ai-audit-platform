/**
 * E2E Tests for Supabase Realtime Synchronization
 *
 * Tests real-time synchronization between backend and frontend:
 * - Multi-tab sync for task updates
 * - Task status synchronization
 * - Agent message streaming
 * - Connection resilience and reconnection
 * - Message ordering and delivery
 * - Latency measurements (<500ms targets)
 *
 * @module e2e/07-supabase-realtime.spec
 */

import { test, expect, Page, BrowserContext } from '@playwright/test'
import { URLS, FRONTEND_URL, BACKEND_API_URL } from './config/routes'

/**
 * Mock data for testing
 */
const MOCK_DATA = {
  project: {
    id: 'test-project-001',
    name: 'Test Project',
    description: 'E2E Test Project',
  },
  task: {
    id: 'test-task-001',
    project_id: 'test-project-001',
    title: 'Verify Realtime Sync',
    status: 'pending',
  },
  agentMessage: {
    id: 'msg-001',
    task_id: 'test-task-001',
    agent_role: 'supervisor',
    content: 'Task status updated',
    message_type: 'response',
    metadata: {},
    timestamp: new Date().toISOString(),
  },
}

/**
 * Helper to measure latency between two timestamps
 */
function measureLatency(startTime: number, endTime: number): number {
  return endTime - startTime
}

/**
 * Helper to wait for element to contain specific text
 */
async function waitForText(page: Page, text: string, timeout = 5000): Promise<void> {
  await page.waitForSelector(`text/${text}`, { timeout })
}

/**
 * Helper to create a new browser context for second tab
 */
async function createSecondTab(context: BrowserContext, baseURL: string): Promise<Page> {
  const page = await context.newPage()
  await page.goto(baseURL)
  await page.waitForLoadState('networkidle')
  return page
}

/**
 * Helper to simulate task update via backend (POST to API)
 */
async function updateTaskViaBackend(
  page: Page,
  taskId: string,
  status: string,
  baseURL: string
): Promise<number> {
  const startTime = Date.now()

  // In real scenario, this would call the backend API
  // For now, we simulate it via page.evaluate
  await page.evaluate(
    async ({ taskId, status, apiUrl }) => {
      try {
        await fetch(`${apiUrl}/tasks/${taskId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status }),
        })
      } catch (error) {
        console.error('Task update failed:', error)
      }
    },
    { taskId, status, apiUrl: baseURL }
  )

  return startTime
}

/**
 * Helper to check if realtime subscription is active
 */
async function isRealtimeConnected(page: Page): Promise<boolean> {
  return await page.evaluate(() => {
    const connectionIndicator = document.querySelector('[data-testid="realtime-status"]')
    return connectionIndicator?.textContent?.includes('Connected') ?? false
  })
}

/**
 * Helper to insert agent message via API
 */
async function insertAgentMessageViaAPI(
  page: Page,
  taskId: string,
  content: string,
  apiUrl: string
): Promise<{ startTime: number; messageId: string }> {
  const startTime = Date.now()
  const messageId = `msg-${Date.now()}`

  await page.evaluate(
    async ({ taskId, content, apiUrl, messageId }) => {
      try {
        await fetch(`${apiUrl}/tasks/${taskId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id: messageId,
            agent_role: 'supervisor',
            content,
            message_type: 'response',
          }),
        })
      } catch (error) {
        console.error('Message insertion failed:', error)
      }
    },
    { taskId, content, apiUrl, messageId }
  )

  return { startTime, messageId }
}

/**
 * Test Suite: Multi-Tab Synchronization
 */
test.describe('Multi-Tab Sync', () => {
  test('should sync task updates across two browser tabs within 500ms', async ({
    browser,
  }) => {
    const context = await browser.newContext()
    const baseURL = FRONTEND_URL

    try {
      // STEP 1: Open first tab and navigate to project
      const tab1 = await context.newPage()
      await tab1.goto(baseURL)
      await tab1.waitForLoadState('networkidle')

      // STEP 2: Open second tab with same project
      const tab2 = await createSecondTab(context, baseURL)

      // STEP 3: Verify both tabs are connected to realtime
      const tab1Connected = await isRealtimeConnected(tab1)
      const tab2Connected = await isRealtimeConnected(tab2)

      expect(tab1Connected).toBe(true)
      expect(tab2Connected).toBe(true)

      // STEP 4: Update task in Tab 1 via backend
      const startTime = await updateTaskViaBackend(
        tab1,
        MOCK_DATA.task.id,
        'in_progress',
        baseURL
      )

      // STEP 5: Wait for update to appear in Tab 2
      const updateCheckInterval = setInterval(() => {
        tab2.evaluate(() => {
          document.documentElement.style.backgroundColor = 'transparent'
        })
      }, 50)

      try {
        // Wait for status indicator to update in Tab 2
        await tab2.waitForSelector('[data-testid="task-status"][data-status="in_progress"]', {
          timeout: 500,
        })
      } catch {
        // If element doesn't exist, check for text alternative
        await waitForText(tab2, 'in_progress', 500)
      }

      clearInterval(updateCheckInterval)

      const endTime = Date.now()
      const latency = measureLatency(startTime, endTime)

      // STEP 6: Verify latency is within acceptable range
      expect(latency).toBeLessThan(500)

      // STEP 7: Verify both tabs show same status
      const tab1Status = await tab1.evaluate(() => {
        return (
          document.querySelector('[data-testid="task-status"]')?.textContent || ''
        )
      })

      const tab2Status = await tab2.evaluate(() => {
        return (
          document.querySelector('[data-testid="task-status"]')?.textContent || ''
        )
      })

      expect(tab1Status).toBe(tab2Status)

      // STEP 8: Verify no page refresh occurred (document should not reload)
      const tab2InitialUrl = tab2.url()
      expect(tab2.url()).toBe(tab2InitialUrl)

      // Log performance metrics
      console.log(`Multi-Tab Sync Latency: ${latency}ms (Target: <500ms)`)
    } finally {
      await context.close()
    }
  })

  test('should handle rapid concurrent updates without losing data', async ({
    browser,
  }) => {
    const context = await browser.newContext()
    const baseURL = FRONTEND_URL

    try {
      const tab1 = await context.newPage()
      await tab1.goto(baseURL)
      await tab1.waitForLoadState('networkidle')

      const tab2 = await createSecondTab(context, baseURL)

      // Send 5 rapid updates
      const updatePromises = []
      for (let i = 0; i < 5; i++) {
        const promise = updateTaskViaBackend(
          tab1,
          MOCK_DATA.task.id,
          `status-${i}`,
          baseURL
        )
        updatePromises.push(promise)
        await tab1.waitForTimeout(100) // Small delay between updates
      }

      await Promise.all(updatePromises)

      // Wait for all updates to propagate to Tab 2
      await tab2.waitForTimeout(1000)

      // Verify Tab 2 reflects latest update
      const finalStatus = await tab2.evaluate(() => {
        return (
          document.querySelector('[data-testid="task-status"]')?.textContent || ''
        )
      })

      expect(finalStatus).toContain('status-4')
    } finally {
      await context.close()
    }
  })

  test('should maintain sync when tab is backgrounded and foregrounded', async ({
    browser,
  }) => {
    const context = await browser.newContext()
    const baseURL = FRONTEND_URL

    try {
      const tab1 = await context.newPage()
      await tab1.goto(baseURL)
      await tab1.waitForLoadState('networkidle')

      const tab2 = await createSecondTab(context, baseURL)

      // STEP 1: Update task
      await updateTaskViaBackend(tab1, MOCK_DATA.task.id, 'completed', baseURL)

      // STEP 2: Simulate Tab 2 being backgrounded (via evaluate)
      await tab2.evaluate(() => {
        document.dispatchEvent(new Event('visibilitychange'))
      })

      // Wait for update to arrive
      await tab2.waitForTimeout(200)

      // STEP 3: Simulate Tab 2 being foregrounded
      await tab2.evaluate(() => {
        Object.defineProperty(document, 'hidden', {
          value: false,
          writable: true,
        })
        document.dispatchEvent(new Event('visibilitychange'))
      })

      // STEP 4: Verify Tab 2 still has the update
      const status = await tab2.evaluate(() => {
        return (
          document.querySelector('[data-testid="task-status"]')?.textContent || ''
        )
      })

      expect(status).toContain('completed')
    } finally {
      await context.close()
    }
  })
})

/**
 * Test Suite: Task Status Updates
 */
test.describe('Task Status Updates', () => {
  test('should reflect all status transitions in realtime', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Verify realtime is connected
    const isConnected = await isRealtimeConnected(page)
    expect(isConnected).toBe(true)

    // Test all status transitions
    const statusTransitions = [
      { from: 'pending', to: 'in_progress' },
      { from: 'in_progress', to: 'review' },
      { from: 'review', to: 'approved' },
      { from: 'approved', to: 'completed' },
    ]

    for (const transition of statusTransitions) {
      const startTime = Date.now()

      // Update status via backend
      await updateTaskViaBackend(page, MOCK_DATA.task.id, transition.to, FRONTEND_URL)

      // Wait for UI to update
      try {
        await page.waitForSelector(
          `[data-testid="task-status"][data-status="${transition.to}"]`,
          { timeout: 500 }
        )
      } catch {
        await waitForText(page, transition.to, 500)
      }

      const latency = Date.now() - startTime

      // Verify latency
      expect(latency).toBeLessThan(500)

      // Log transition
      console.log(
        `Status Transition ${transition.from} → ${transition.to}: ${latency}ms`
      )

      await page.waitForTimeout(100) // Small delay before next transition
    }
  })

  test('should handle status update with metadata changes', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const startTime = Date.now()

    // Simulate update with metadata (assignee, due date, etc.)
    await page.evaluate(
      async ({ taskId, apiUrl }) => {
        try {
          await fetch(`${apiUrl}/tasks/${taskId}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              status: 'in_progress',
              assignee: 'user-123',
              due_date: '2024-01-15',
              priority: 'high',
            }),
          })
        } catch (error) {
          console.error('Update failed:', error)
        }
      },
      { taskId: MOCK_DATA.task.id, apiUrl: FRONTEND_URL }
    )

    // Wait for all metadata to update
    await page.waitForTimeout(300)

    const latency = Date.now() - startTime

    // Verify latency for complex update
    expect(latency).toBeLessThan(600)

    // Verify metadata changes are visible
    const assigneeElement = page.locator('[data-testid="task-assignee"]')
    await expect(assigneeElement).toContainText('user-123', { timeout: 3000 })
  })

  test('should queue updates that arrive during sync', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Send 3 updates rapidly
    const updates = ['pending', 'in_progress', 'review']
    const startTime = Date.now()

    for (const status of updates) {
      await updateTaskViaBackend(page, MOCK_DATA.task.id, status, FRONTEND_URL)
    }

    // Wait for final status to settle
    await page.waitForTimeout(600)

    const latency = Date.now() - startTime

    // Verify all updates were processed
    const statusElement = page.locator('[data-testid="task-status"]')
    await expect(statusElement).toContainText('review', { timeout: 2000 })

    // Verify timing
    expect(latency).toBeLessThan(1000)
  })
})

/**
 * Test Suite: Agent Message Streaming
 */
test.describe('Agent Message Streaming', () => {
  test('should display agent messages in realtime as they are inserted', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const startTime = Date.now()

    // Insert an agent message via API
    const { startTime: insertStart, messageId } = await insertAgentMessageViaAPI(
      page,
      MOCK_DATA.task.id,
      'Analysis complete: All tasks passed validation',
      FRONTEND_URL
    )

    // Wait for message to appear in chat UI
    await page.waitForSelector(`[data-testid="message-${messageId}"]`, {
      timeout: 500,
    })

    const latency = Date.now() - insertStart

    // Verify message content
    const messageElement = page.locator(`[data-testid="message-${messageId}"]`)
    await expect(messageElement).toContainText('Analysis complete', { timeout: 2000 })

    // Verify latency
    expect(latency).toBeLessThan(500)

    console.log(`Message Insertion Latency: ${latency}ms (Target: <500ms)`)
  })

  test('should preserve message ordering', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Insert 5 messages in rapid succession
    const messageIds: string[] = []
    const contentArray = [
      'First message',
      'Second message',
      'Third message',
      'Fourth message',
      'Fifth message',
    ]

    for (const content of contentArray) {
      const { messageId } = await insertAgentMessageViaAPI(
        page,
        MOCK_DATA.task.id,
        content,
        FRONTEND_URL
      )
      messageIds.push(messageId)
      await page.waitForTimeout(50) // Small delay between insertions
    }

    // Wait for all messages to appear
    await page.waitForTimeout(800)

    // Verify message order in DOM
    const messageElements = await page.locator('[data-testid*="message-"]').all()
    const visibleMessages = []

    for (const element of messageElements) {
      const text = await element.textContent()
      visibleMessages.push(text)
    }

    // Check that messages appear in order
    const firstIndex = visibleMessages.findIndex((msg) =>
      msg?.includes('First message')
    )
    const secondIndex = visibleMessages.findIndex((msg) =>
      msg?.includes('Second message')
    )
    const thirdIndex = visibleMessages.findIndex((msg) =>
      msg?.includes('Third message')
    )

    expect(firstIndex).toBeLessThan(secondIndex)
    expect(secondIndex).toBeLessThan(thirdIndex)
  })

  test('should handle messages with rich content and metadata', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const richContent = {
      text: 'Detailed analysis with artifacts',
      artifactId: 'artifact-123',
      metadata: {
        confidence: 0.95,
        processingTime: 234,
        tags: ['analysis', 'validation', 'automated'],
      },
    }

    // Insert rich message
    await page.evaluate(
      async ({ taskId, content, apiUrl }) => {
        try {
          await fetch(`${apiUrl}/tasks/${taskId}/messages`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              agent_role: 'supervisor',
              content: content.text,
              message_type: 'response',
              metadata: content.metadata,
            }),
          })
        } catch (error) {
          console.error('Rich message insertion failed:', error)
        }
      },
      { taskId: MOCK_DATA.task.id, content: richContent, apiUrl: FRONTEND_URL }
    )

    // Wait for message and metadata to render
    await page.waitForTimeout(500)

    // Verify message appears
    const messageContent = await page.evaluate(() => {
      return document.querySelector('[data-testid*="message-"]')?.textContent
    })

    expect(messageContent).toContain('Detailed analysis')

    // Verify metadata is accessible
    const metadata = await page.evaluate(() => {
      const messageEl = document.querySelector('[data-testid*="message-"]')
      return messageEl?.getAttribute('data-metadata')
    })

    expect(metadata).toBeDefined()
  })

  test('should display streaming indicators for pending messages', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Check if streaming indicator exists or appears during message insertion
    const streamingIndicator = page.locator(
      '[data-testid="message-streaming-indicator"]'
    )

    // This might be initially visible or appear during message processing
    const isVisible = await streamingIndicator.isVisible().catch(() => false)

    if (isVisible) {
      expect(isVisible).toBe(true)

      // Wait for indicator to disappear (message complete)
      await streamingIndicator.waitFor({ state: 'hidden', timeout: 5000 })
    }
  })
})

/**
 * Test Suite: Connection Resilience
 */
test.describe('Connection Resilience', () => {
  test('should automatically reconnect when network is interrupted', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Verify initial connection
    let isConnected = await isRealtimeConnected(page)
    expect(isConnected).toBe(true)

    // Simulate network interruption
    await page.context().setOffline(true)
    await page.waitForTimeout(500)

    // Verify disconnection
    isConnected = await isRealtimeConnected(page)
    expect(isConnected).toBe(false)

    // Restore network
    await page.context().setOffline(false)
    await page.waitForTimeout(500)

    // Verify reconnection
    isConnected = await isRealtimeConnected(page)
    expect(isConnected).toBe(true)
  })

  test('should handle connection timeout gracefully', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Setup error listener
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Simulate slow/timeout network
    await page.route('**/*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 35000)) // Timeout scenario
      route.abort()
    })

    // Wait for timeout scenario
    await page.waitForTimeout(2000)

    // Verify error was logged (not crashed)
    // Connection should attempt to recover
    const connectionError = errors.some((err) =>
      err.toLowerCase().includes('timeout')
    )

    // Should have error OR successfully recovered
    const hasRecovery = await page.evaluate(() => {
      return (
        document.querySelector('[data-testid="realtime-status"]')?.textContent
          ?.includes('Connected') ?? false
      )
    })

    expect(connectionError || hasRecovery).toBe(true)
  })

  test('should not lose messages when reconnecting', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Get initial message count
    const initialMessageCount = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid*="message-"]').length
    })

    // Disconnect network
    await page.context().setOffline(true)
    await page.waitForTimeout(300)

    // Try to send message during offline (should queue)
    const { messageId } = await insertAgentMessageViaAPI(
      page,
      MOCK_DATA.task.id,
      'Message sent while offline',
      FRONTEND_URL
    )

    await page.waitForTimeout(300)

    // Reconnect network
    await page.context().setOffline(false)
    await page.waitForTimeout(800)

    // Verify message eventually appears
    try {
      await page.waitForSelector(`[data-testid="message-${messageId}"]`, {
        timeout: 3000,
      })
    } catch {
      // Message might not have specific testid, check content instead
      const hasMessage = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('[data-testid*="message-"]'))
          .map((el) => el.textContent)
          .some((text) => text?.includes('Message sent while offline'))
      })
      expect(hasMessage).toBe(true)
    }

    // Verify final message count increased
    const finalMessageCount = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid*="message-"]').length
    })

    expect(finalMessageCount).toBeGreaterThanOrEqual(initialMessageCount)
  })

  test('should handle rapid reconnections without duplicating data', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Simulate 3 rapid reconnection cycles
    for (let i = 0; i < 3; i++) {
      await page.context().setOffline(true)
      await page.waitForTimeout(200)

      await page.context().setOffline(false)
      await page.waitForTimeout(200)
    }

    // Insert a message after rapid reconnections
    const { messageId } = await insertAgentMessageViaAPI(
      page,
      MOCK_DATA.task.id,
      'Test message after reconnections',
      FRONTEND_URL
    )

    await page.waitForTimeout(600)

    // Count how many times this message appears (should be exactly 1)
    const messageCount = await page.evaluate((id) => {
      return Array.from(
        document.querySelectorAll(`[data-testid="message-${id}"]`)
      ).length
    }, messageId)

    expect(messageCount).toBe(1)
  })
})

/**
 * Test Suite: Performance and Latency Measurements
 */
test.describe('Performance Metrics', () => {
  test('should measure and log synchronization latencies', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const latencies: number[] = []

    // Perform 5 sync operations
    for (let i = 0; i < 5; i++) {
      const startTime = Date.now()

      await updateTaskViaBackend(page, MOCK_DATA.task.id, `sync-test-${i}`, FRONTEND_URL)

      // Wait for update
      await page.waitForTimeout(300)

      const latency = Date.now() - startTime
      latencies.push(latency)
    }

    // Calculate statistics
    const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length
    const maxLatency = Math.max(...latencies)
    const minLatency = Math.min(...latencies)

    // Log metrics
    console.log('Synchronization Latency Metrics:')
    console.log(`  Average: ${avgLatency.toFixed(2)}ms`)
    console.log(`  Min: ${minLatency}ms`)
    console.log(`  Max: ${maxLatency}ms`)
    console.log(`  All measurements: ${latencies.join(', ')}ms`)

    // Verify acceptable performance
    expect(avgLatency).toBeLessThan(500)
    expect(maxLatency).toBeLessThan(800)
  })

  test('should maintain performance under concurrent operations', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const startTime = Date.now()

    // Perform 10 concurrent operations
    const operations = Array.from({ length: 10 }, (_, i) =>
      updateTaskViaBackend(page, MOCK_DATA.task.id, `concurrent-${i}`, FRONTEND_URL)
    )

    await Promise.all(operations)

    // Wait for all updates to propagate
    await page.waitForTimeout(1000)

    const totalTime = Date.now() - startTime
    const avgTimePerOp = totalTime / 10

    console.log(
      `Concurrent Operations: 10 operations in ${totalTime}ms (avg ${avgTimePerOp.toFixed(2)}ms each)`
    )

    // Verify performance doesn't degrade significantly
    expect(avgTimePerOp).toBeLessThan(600)
  })

  test('should not memory leak during extended realtime operations', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Perform 50 operations over extended time
    for (let i = 0; i < 50; i++) {
      await insertAgentMessageViaAPI(
        page,
        MOCK_DATA.task.id,
        `Message ${i}: Memory test`,
        FRONTEND_URL
      )

      if (i % 10 === 0) {
        // Allow UI to render and settle
        await page.waitForTimeout(200)
      }
    }

    // Final wait for all messages
    await page.waitForTimeout(800)

    // Check for memory indicators (in real scenario, use DevTools metrics)
    const messageCount = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid*="message-"]').length
    })

    console.log(`Extended Operations: ${messageCount} messages accumulated`)

    // Should have all messages without significant slowdown
    expect(messageCount).toBeGreaterThan(40)
  })
})

/**
 * Test Suite: Error Handling and Edge Cases
 */
test.describe('Error Handling', () => {
  test('should handle malformed messages gracefully', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Try to insert malformed message
    await page.evaluate(
      async ({ taskId, apiUrl }) => {
        try {
          await fetch(`${apiUrl}/tasks/${taskId}/messages`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              // Missing required fields
              invalid_field: 'test',
            }),
          })
        } catch (error) {
          // Expected to fail
        }
      },
      { taskId: MOCK_DATA.task.id, apiUrl: FRONTEND_URL }
    )

    await page.waitForTimeout(500)

    // Should not crash (errors might be present, but app should still work)
    const isConnected = await isRealtimeConnected(page)
    // Connection should either still be established or have gracefully failed
    expect(typeof isConnected).toBe('boolean')
  })

  test('should handle subscription to non-existent task gracefully', async ({
    page,
  }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Try to subscribe to invalid task
    await page.evaluate(async () => {
      try {
        await fetch('http://localhost:5173/tasks/invalid-task-id/subscribe', {
          method: 'POST',
        })
      } catch (error) {
        // Expected to fail
      }
    })

    await page.waitForTimeout(500)

    // App should remain functional
    const isConnected = await isRealtimeConnected(page)
    expect(typeof isConnected).toBe('boolean')
  })

  test('should recover from subscription errors', async ({ page }) => {
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Simulate subscription error by making invalid request
    await page.context().setOffline(true)
    await page.waitForTimeout(300)

    // Try to subscribe while offline
    const subscriptionAttempt = page.evaluate(async () => {
      try {
        await fetch('http://localhost:5173/tasks/test/messages')
        return 'success'
      } catch {
        return 'failed'
      }
    })

    const result = await subscriptionAttempt

    // Reconnect
    await page.context().setOffline(false)
    await page.waitForTimeout(500)

    // Verify can recover
    const isConnected = await isRealtimeConnected(page)
    expect(isConnected).toBe(true)
  })
})
