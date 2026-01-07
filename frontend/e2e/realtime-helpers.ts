/**
 * Helper utilities for Supabase Realtime E2E testing
 *
 * Provides utilities for:
 * - Connection management
 * - Message tracking and verification
 * - Latency measurement
 * - Network simulation
 * - Data validation
 *
 * @module e2e/realtime-helpers
 */

import { Page, BrowserContext } from '@playwright/test'

/**
 * Configuration for Realtime test helpers
 */
export interface RealtimeHelperConfig {
  /** Base URL for the application */
  baseUrl: string
  /** API base URL (may differ from frontend) */
  apiUrl: string
  /** Default timeout for operations (ms) */
  defaultTimeout?: number
  /** Enable verbose logging */
  verbose?: boolean
}

/**
 * Message tracker for E2E tests
 */
export class MessageTracker {
  private messages: Map<string, MessageRecord> = new Map()
  private receivedMessages: MessageRecord[] = []

  interface MessageRecord {
    id: string
    content: string
    sentAt: number
    receivedAt?: number
    status: 'sent' | 'received' | 'rendered'
  }

  /**
   * Track a sent message
   */
  trackSent(id: string, content: string): void {
    const record: MessageRecord = {
      id,
      content,
      sentAt: Date.now(),
      status: 'sent',
    }
    this.messages.set(id, record)
  }

  /**
   * Mark message as received (from backend)
   */
  markReceived(id: string): void {
    const record = this.messages.get(id)
    if (record) {
      record.receivedAt = Date.now()
      record.status = 'received'
    }
  }

  /**
   * Mark message as rendered (in UI)
   */
  markRendered(id: string): void {
    const record = this.messages.get(id)
    if (record) {
      record.status = 'rendered'
    }
  }

  /**
   * Get latency for a message (sent to received)
   */
  getLatency(id: string): number | null {
    const record = this.messages.get(id)
    if (record && record.receivedAt) {
      return record.receivedAt - record.sentAt
    }
    return null
  }

  /**
   * Get all messages
   */
  getAll(): MessageRecord[] {
    return Array.from(this.messages.values())
  }

  /**
   * Clear tracker
   */
  clear(): void {
    this.messages.clear()
    this.receivedMessages = []
  }

  /**
   * Get summary statistics
   */
  getSummary(): {
    total: number
    received: number
    rendered: number
    avgLatency: number
    maxLatency: number
    minLatency: number
  } {
    const messages = Array.from(this.messages.values())
    const received = messages.filter((m) => m.receivedAt).length
    const rendered = messages.filter((m) => m.status === 'rendered').length

    const latencies = messages
      .filter((m) => m.receivedAt)
      .map((m) => (m.receivedAt! - m.sentAt))

    return {
      total: messages.length,
      received,
      rendered,
      avgLatency: latencies.length > 0 ?
        latencies.reduce((a, b) => a + b, 0) / latencies.length
        : 0,
      maxLatency: latencies.length > 0 ? Math.max(...latencies) : 0,
      minLatency: latencies.length > 0 ? Math.min(...latencies) : 0,
    }
  }
}

/**
 * Helper class for Realtime connection management
 */
export class RealtimeConnectionHelper {
  constructor(private page: Page, private config: RealtimeHelperConfig) {}

  /**
   * Wait for realtime to be connected
   */
  async waitForConnected(timeout = 5000): Promise<void> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      const isConnected = await this.isConnected()
      if (isConnected) {
        return
      }
      await this.page.waitForTimeout(100)
    }

    throw new Error(`Realtime connection not established within ${timeout}ms`)
  }

  /**
   * Check if realtime is currently connected
   */
  async isConnected(): Promise<boolean> {
    try {
      return await this.page.evaluate(() => {
        const indicator = document.querySelector('[data-testid="realtime-status"]')
        return indicator?.textContent?.includes('Connected') ?? false
      })
    } catch {
      return false
    }
  }

  /**
   * Get current connection status
   */
  async getStatus(): Promise<string> {
    return await this.page.evaluate(() => {
      return document.querySelector('[data-testid="realtime-status"]')?.textContent || 'Unknown'
    })
  }

  /**
   * Simulate network disconnect
   */
  async disconnect(): Promise<void> {
    await this.page.context().setOffline(true)
  }

  /**
   * Simulate network reconnect
   */
  async reconnect(): Promise<void> {
    await this.page.context().setOffline(false)
  }

  /**
   * Toggle network on/off
   */
  async toggleNetwork(count = 1, delayMs = 500): Promise<void> {
    for (let i = 0; i < count; i++) {
      await this.disconnect()
      await this.page.waitForTimeout(delayMs / 2)
      await this.reconnect()
      await this.page.waitForTimeout(delayMs / 2)
    }
  }
}

/**
 * Helper for message operations
 */
export class MessageHelper {
  constructor(private page: Page, private config: RealtimeHelperConfig) {}

  /**
   * Insert a message via API
   */
  async insertMessage(
    taskId: string,
    content: string,
    options?: {
      role?: string
      type?: string
      metadata?: Record<string, any>
    }
  ): Promise<{ id: string; insertedAt: number }> {
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const insertedAt = Date.now()

    await this.page.evaluate(
      async ({ apiUrl, taskId, messageId, content, options }) => {
        const response = await fetch(`${apiUrl}/tasks/${taskId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id: messageId,
            agent_role: options?.role || 'supervisor',
            content,
            message_type: options?.type || 'response',
            metadata: options?.metadata || {},
          }),
        })

        if (!response.ok) {
          throw new Error(`Failed to insert message: ${response.statusText}`)
        }
      },
      { apiUrl: this.config.apiUrl, taskId, messageId, content, options }
    )

    return { id: messageId, insertedAt }
  }

  /**
   * Wait for message to appear in UI
   */
  async waitForMessage(
    messageId: string,
    timeout = 5000
  ): Promise<{ appearTime: number; latency: number }> {
    const startTime = Date.now()

    try {
      await this.page.waitForSelector(`[data-testid="message-${messageId}"]`, {
        timeout,
      })

      const appearTime = Date.now()
      return {
        appearTime,
        latency: appearTime - startTime,
      }
    } catch {
      throw new Error(`Message ${messageId} did not appear within ${timeout}ms`)
    }
  }

  /**
   * Get message content from UI
   */
  async getMessageContent(messageId: string): Promise<string> {
    return await this.page.evaluate((id) => {
      const element = document.querySelector(`[data-testid="message-${id}"]`)
      return element?.textContent || ''
    }, messageId)
  }

  /**
   * Count total messages in chat
   */
  async getMessageCount(): Promise<number> {
    return await this.page.evaluate(() => {
      return document.querySelectorAll('[data-testid*="message-"]').length
    })
  }

  /**
   * Get all message IDs in order
   */
  async getMessageIds(): Promise<string[]> {
    return await this.page.evaluate(() => {
      const messages = document.querySelectorAll('[data-testid*="message-"]')
      const ids: string[] = []

      messages.forEach((msg) => {
        const id = msg.getAttribute('data-testid')?.replace('message-', '')
        if (id) {
          ids.push(id)
        }
      })

      return ids
    })
  }

  /**
   * Verify message ordering
   */
  async verifyMessageOrder(expectedMessages: string[]): Promise<boolean> {
    const ids = await this.getMessageIds()
    return JSON.stringify(ids) === JSON.stringify(expectedMessages)
  }

  /**
   * Verify no duplicate messages
   */
  async verifyNoDuplicates(): Promise<boolean> {
    const ids = await this.getMessageIds()
    return ids.length === new Set(ids).size
  }
}

/**
 * Helper for task operations
 */
export class TaskHelper {
  constructor(private page: Page, private config: RealtimeHelperConfig) {}

  /**
   * Update task status via API
   */
  async updateStatus(taskId: string, status: string): Promise<number> {
    const startTime = Date.now()

    await this.page.evaluate(
      async ({ apiUrl, taskId, status }) => {
        const response = await fetch(`${apiUrl}/tasks/${taskId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status }),
        })

        if (!response.ok) {
          throw new Error(`Failed to update status: ${response.statusText}`)
        }
      },
      { apiUrl: this.config.apiUrl, taskId, status }
    )

    return startTime
  }

  /**
   * Wait for status change in UI
   */
  async waitForStatusChange(
    expectedStatus: string,
    timeout = 5000
  ): Promise<{ changeTime: number; latency: number }> {
    const startTime = Date.now()

    try {
      await this.page.waitForSelector(
        `[data-testid="task-status"][data-status="${expectedStatus}"]`,
        { timeout }
      )

      const changeTime = Date.now()
      return {
        changeTime,
        latency: changeTime - startTime,
      }
    } catch {
      // Fallback: check text content
      await this.page.waitForFunction(
        (status) => {
          const element = document.querySelector('[data-testid="task-status"]')
          return element?.textContent?.includes(status)
        },
        expectedStatus,
        { timeout }
      )

      const changeTime = Date.now()
      return {
        changeTime,
        latency: changeTime - startTime,
      }
    }
  }

  /**
   * Get current task status
   */
  async getStatus(): Promise<string> {
    return await this.page.evaluate(() => {
      return document.querySelector('[data-testid="task-status"]')?.textContent || 'Unknown'
    })
  }

  /**
   * Update multiple task properties
   */
  async updateMultiple(
    taskId: string,
    updates: Record<string, any>
  ): Promise<number> {
    const startTime = Date.now()

    await this.page.evaluate(
      async ({ apiUrl, taskId, updates }) => {
        const response = await fetch(`${apiUrl}/tasks/${taskId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updates),
        })

        if (!response.ok) {
          throw new Error(`Failed to update task: ${response.statusText}`)
        }
      },
      { apiUrl: this.config.apiUrl, taskId, updates }
    )

    return startTime
  }
}

/**
 * Performance measurement helper
 */
export class PerformanceHelper {
  private measurements: Map<string, number[]> = new Map()

  /**
   * Record a measurement
   */
  record(label: string, value: number): void {
    if (!this.measurements.has(label)) {
      this.measurements.set(label, [])
    }
    this.measurements.get(label)!.push(value)
  }

  /**
   * Get statistics for a measurement
   */
  getStats(label: string): {
    count: number
    min: number
    max: number
    avg: number
    p95: number
    p99: number
  } {
    const values = this.measurements.get(label) || []

    if (values.length === 0) {
      return {
        count: 0,
        min: 0,
        max: 0,
        avg: 0,
        p95: 0,
        p99: 0,
      }
    }

    const sorted = [...values].sort((a, b) => a - b)
    const sum = sorted.reduce((a, b) => a + b, 0)

    return {
      count: values.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: sum / values.length,
      p95: sorted[Math.ceil(values.length * 0.95) - 1],
      p99: sorted[Math.ceil(values.length * 0.99) - 1],
    }
  }

  /**
   * Get all measurements
   */
  getAll(): Record<string, number[]> {
    const result: Record<string, number[]> = {}
    this.measurements.forEach((values, label) => {
      result[label] = values
    })
    return result
  }

  /**
   * Clear all measurements
   */
  clear(): void {
    this.measurements.clear()
  }

  /**
   * Generate report
   */
  generateReport(): string {
    let report = '\n=== Performance Report ===\n'

    this.measurements.forEach((values, label) => {
      const stats = this.getStats(label)
      report += `\n${label}:\n`
      report += `  Count: ${stats.count}\n`
      report += `  Min: ${stats.min.toFixed(2)}ms\n`
      report += `  Max: ${stats.max.toFixed(2)}ms\n`
      report += `  Avg: ${stats.avg.toFixed(2)}ms\n`
      report += `  P95: ${stats.p95.toFixed(2)}ms\n`
      report += `  P99: ${stats.p99.toFixed(2)}ms\n`
    })

    return report
  }
}

/**
 * Create all helpers for a test
 */
export function createRealtimeHelpers(
  page: Page,
  config: RealtimeHelperConfig
): {
  connection: RealtimeConnectionHelper
  message: MessageHelper
  task: TaskHelper
  performance: PerformanceHelper
  tracker: MessageTracker
} {
  return {
    connection: new RealtimeConnectionHelper(page, config),
    message: new MessageHelper(page, config),
    task: new TaskHelper(page, config),
    performance: new PerformanceHelper(),
    tracker: new MessageTracker(),
  }
}
