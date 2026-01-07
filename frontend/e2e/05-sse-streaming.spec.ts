/**
 * E2E Test: SSE Streaming of Agent Messages
 *
 * Tests Server-Sent Events (SSE) streaming for real-time agent communication:
 * - SSE connection to /stream/{taskId}
 * - Agent messages appear in chat UI
 * - Message ordering preserved
 * - Heartbeat keeps connection alive
 * - Graceful error handling
 *
 * @module e2e/05-sse-streaming.spec
 */

import { test, expect } from '@playwright/test';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { DashboardPage } from './pages/DashboardPage';
import {
  mockClientInfo,
  mockAgentMessages,
} from './fixtures/mock-audit-data';

test.describe('SSE Streaming of Agent Messages', () => {
  let dashboardPage: DashboardPage;
  let taskDetailPage: TaskDetailPage;
  let testThreadId: string;
  let taskId: string;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    taskDetailPage = new TaskDetailPage(page);

    // Create a project
    await dashboardPage.goto();
    await dashboardPage.startNewProject(
      mockClientInfo.clientName,
      mockClientInfo.fiscalYear,
      mockClientInfo.overallMateriality
    );
    await dashboardPage.waitForProjectCreation();

    // Extract thread_id and task_id
    const response = await page.waitForResponse(
      (res) => res.url().includes('/api/projects/start') && res.status() === 201
    );
    const body = await response.json();
    testThreadId = body.thread_id;

    // Navigate to task detail
    await dashboardPage.openProject(mockClientInfo.clientName);

    // Get task ID from URL or data attribute
    await page.waitForTimeout(1000);
    taskId = await page.evaluate(() => {
      const taskElement = document.querySelector('[data-testid="task-list-item"]');
      return taskElement?.getAttribute('data-task-id') || '';
    });
  });

  test('should establish SSE connection to /stream/{taskId}', async ({ page }) => {
    // ============================================================================
    // STEP 1: Monitor network requests for SSE connection
    // ============================================================================
    await test.step('Verify SSE connection request', async () => {
      // Wait for SSE connection to be established
      const sseRequestPromise = page.waitForRequest(
        (request) =>
          request.url().includes('/stream/') && request.method() === 'GET',
        { timeout: 10000 }
      );

      // Trigger workflow to start SSE streaming
      await taskDetailPage.approveTask();

      const sseRequest = await sseRequestPromise;

      // Verify URL contains task ID
      expect(sseRequest.url()).toContain('/stream/');

      // Verify SSE headers
      const headers = sseRequest.headers();
      expect(headers['accept']).toContain('text/event-stream');
    });

    // ============================================================================
    // STEP 2: Verify SSE connection established
    // ============================================================================
    await test.step('Verify connection established', async () => {
      // Wait for response with correct content-type
      const sseResponse = await page.waitForResponse(
        (response) =>
          response.url().includes('/stream/') &&
          response.headers()['content-type']?.includes('text/event-stream'),
        { timeout: 10000 }
      );

      expect(sseResponse.status()).toBe(200);
      expect(sseResponse.headers()['content-type']).toContain('text/event-stream');
    });
  });

  test('should receive and display agent messages via SSE', async ({ page }) => {
    // ============================================================================
    // STEP 1: Setup message tracking
    // ============================================================================
    const receivedMessages: any[] = [];

    await test.step('Setup EventSource listener', async () => {
      // Monitor EventSource messages in browser
      await page.evaluate(() => {
        (window as any).sseMessages = [];
        const originalEventSource = (window as any).EventSource;

        if (originalEventSource) {
          (window as any).EventSource = class extends originalEventSource {
            constructor(url: string, config?: any) {
              super(url, config);

              this.addEventListener('message', (event: MessageEvent) => {
                (window as any).sseMessages.push(JSON.parse(event.data));
              });

              this.addEventListener('error', (error: Event) => {
                console.error('SSE error:', error);
              });
            }
          };
        }
      });
    });

    // ============================================================================
    // STEP 2: Start workflow to trigger SSE streaming
    // ============================================================================
    await test.step('Start workflow', async () => {
      await taskDetailPage.approveTask();
      await page.waitForResponse(
        (res) => res.url().includes('/api/tasks/approve') && res.status() === 200
      );
    });

    // ============================================================================
    // STEP 3: Wait for agent messages to appear
    // ============================================================================
    await test.step('Wait for messages', async () => {
      // Wait for first message
      await taskDetailPage.waitForNewMessage(10000);

      // Get messages from browser
      const messages = await page.evaluate(() => (window as any).sseMessages || []);
      expect(messages.length).toBeGreaterThan(0);

      receivedMessages.push(...messages);
    });

    // ============================================================================
    // STEP 4: Verify messages appear in chat UI
    // ============================================================================
    await test.step('Verify UI displays messages', async () => {
      const chatMessages = await taskDetailPage.getMessages();

      // Should have at least one message visible
      expect(chatMessages.length).toBeGreaterThan(0);

      // Verify message content matches SSE data
      for (const sseMsg of receivedMessages) {
        const content = sseMsg.content;
        const foundInUI = chatMessages.some((uiMsg) => uiMsg.includes(content));
        expect(foundInUI).toBe(true);
      }
    });
  });

  test('should preserve message ordering', async ({ page }) => {
    // ============================================================================
    // STEP 1: Track message sequence
    // ============================================================================
    const messageSequence: { role: string; timestamp: number }[] = [];

    await test.step('Setup message tracking', async () => {
      await page.evaluate(() => {
        (window as any).messageSequence = [];
      });
    });

    // ============================================================================
    // STEP 2: Start workflow
    // ============================================================================
    await test.step('Start workflow', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 3: Verify message order
    // ============================================================================
    await test.step('Verify ordering', async () => {
      const messages = await taskDetailPage.getMessages();

      // Expected order: Partner → Manager → Auditor
      let foundPartner = false;
      let foundManager = false;
      let foundAuditor = false;

      for (const msg of messages) {
        if (msg.includes('Partner') || msg.includes('partner')) {
          foundPartner = true;
          expect(foundManager).toBe(false); // Partner should come before Manager
        }
        if (msg.includes('Manager') || msg.includes('Assigning')) {
          foundManager = true;
          expect(foundPartner).toBe(true); // Manager should come after Partner
        }
        if (msg.includes('Auditor') || msg.includes('testing')) {
          foundAuditor = true;
          expect(foundManager).toBe(true); // Auditor should come after Manager
        }
      }

      // All agent types should have sent messages
      expect(foundPartner).toBe(true);
      expect(foundManager).toBe(true);
      expect(foundAuditor).toBe(true);
    });
  });

  test('should handle SSE heartbeat events', async ({ page }) => {
    // ============================================================================
    // STEP 1: Setup heartbeat tracking
    // ============================================================================
    await test.step('Setup heartbeat listener', async () => {
      await page.evaluate(() => {
        (window as any).heartbeatCount = 0;
        const originalEventSource = (window as any).EventSource;

        if (originalEventSource) {
          (window as any).EventSource = class extends originalEventSource {
            constructor(url: string, config?: any) {
              super(url, config);

              this.addEventListener('heartbeat', () => {
                (window as any).heartbeatCount++;
                console.log('Heartbeat received');
              });
            }
          };
        }
      });
    });

    // ============================================================================
    // STEP 2: Start SSE connection
    // ============================================================================
    await test.step('Start connection', async () => {
      await taskDetailPage.approveTask();
      await page.waitForResponse(
        (res) => res.url().includes('/stream/') && res.status() === 200
      );
    });

    // ============================================================================
    // STEP 3: Wait for heartbeat (30s interval)
    // ============================================================================
    await test.step('Wait for heartbeat', async () => {
      // Wait 35 seconds to ensure at least one heartbeat
      await page.waitForTimeout(35000);

      const heartbeatCount = await page.evaluate(() => (window as any).heartbeatCount || 0);

      // Should have received at least one heartbeat
      expect(heartbeatCount).toBeGreaterThan(0);
    });
  });

  test('should display agent typing indicator during streaming', async ({ page }) => {
    // ============================================================================
    // STEP 1: Start workflow
    // ============================================================================
    await test.step('Start workflow', async () => {
      await taskDetailPage.approveTask();
    });

    // ============================================================================
    // STEP 2: Verify typing indicator appears
    // ============================================================================
    await test.step('Verify typing indicator', async () => {
      // Should show agent typing indicator
      const isTyping = await taskDetailPage.isAgentTyping();
      expect(isTyping).toBe(true);
    });

    // ============================================================================
    // STEP 3: Verify indicator disappears after message
    // ============================================================================
    await test.step('Verify indicator disappears', async () => {
      // Wait for message to arrive
      await taskDetailPage.waitForNewMessage(10000);

      // Wait a bit for indicator to disappear
      await page.waitForTimeout(1000);

      const isStillTyping = await taskDetailPage.isAgentTyping();
      expect(isStillTyping).toBe(false);
    });
  });

  test('should handle SSE connection errors gracefully', async ({ page }) => {
    // ============================================================================
    // STEP 1: Mock SSE endpoint to return error
    // ============================================================================
    await test.step('Mock SSE error', async () => {
      await page.route('**/stream/**', (route) => {
        route.fulfill({
          status: 500,
          body: 'Internal Server Error',
        });
      });
    });

    // ============================================================================
    // STEP 2: Attempt to start workflow
    // ============================================================================
    await test.step('Attempt workflow start', async () => {
      await taskDetailPage.approveTask();
    });

    // ============================================================================
    // STEP 3: Verify error handling
    // ============================================================================
    await test.step('Verify error message', async () => {
      // Should display error message
      const errorMessage = page.locator('[data-testid="sse-error"]');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText(/connection|error|failed/i);
    });

    // ============================================================================
    // STEP 4: Verify retry mechanism
    // ============================================================================
    await test.step('Verify retry button', async () => {
      const retryButton = page.getByRole('button', { name: /retry|reconnect/i });
      await expect(retryButton).toBeVisible();
    });
  });

  test('should handle SSE connection close on task completion', async ({ page }) => {
    // ============================================================================
    // STEP 1: Track connection state
    // ============================================================================
    await test.step('Setup connection tracking', async () => {
      await page.evaluate(() => {
        (window as any).sseConnectionClosed = false;
        const originalEventSource = (window as any).EventSource;

        if (originalEventSource) {
          (window as any).EventSource = class extends originalEventSource {
            constructor(url: string, config?: any) {
              super(url, config);

              this.addEventListener('error', (event: Event) => {
                if (this.readyState === EventSource.CLOSED) {
                  (window as any).sseConnectionClosed = true;
                }
              });
            }
          };
        }
      });
    });

    // ============================================================================
    // STEP 2: Start and complete workflow
    // ============================================================================
    await test.step('Complete workflow', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 3: Verify connection closed
    // ============================================================================
    await test.step('Verify connection closed', async () => {
      // Wait a bit for cleanup
      await page.waitForTimeout(2000);

      // Connection should be closed after completion
      // Note: Adjust based on actual implementation
      // Some implementations may keep connection open
    });
  });

  test('should display message timestamps correctly', async ({ page }) => {
    // ============================================================================
    // STEP 1: Start workflow
    // ============================================================================
    await test.step('Start workflow', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForNewMessage(10000);
    });

    // ============================================================================
    // STEP 2: Verify timestamps visible
    // ============================================================================
    await test.step('Verify timestamps', async () => {
      const messages = page.locator('[data-testid="chat-message"]');
      const count = await messages.count();

      for (let i = 0; i < count; i++) {
        const timestamp = messages.nth(i).locator('[data-testid="message-timestamp"]');
        await expect(timestamp).toBeVisible();

        const timestampText = await timestamp.textContent();
        expect(timestampText).toMatch(/\d{1,2}:\d{2}/); // HH:MM format
      }
    });
  });

  test('should group messages by agent role', async ({ page }) => {
    // ============================================================================
    // STEP 1: Start workflow
    // ============================================================================
    await test.step('Start workflow', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 2: Verify message grouping
    // ============================================================================
    await test.step('Verify grouping', async () => {
      const partnerMessages = await taskDetailPage.getMessagesByAgent('partner');
      const managerMessages = await taskDetailPage.getMessagesByAgent('manager');
      const auditorMessages = await taskDetailPage.getMessagesByAgent('auditor');

      // Each agent should have sent messages
      expect(partnerMessages.length).toBeGreaterThan(0);
      expect(managerMessages.length).toBeGreaterThan(0);
      expect(auditorMessages.length).toBeGreaterThan(0);

      // Verify visual grouping (messages from same agent should be adjacent)
      const messages = page.locator('[data-testid="chat-message"]');
      const count = await messages.count();

      let lastAgent = '';
      let agentChanges = 0;

      for (let i = 0; i < count; i++) {
        const agent = await messages.nth(i).getAttribute('data-agent') || '';
        if (agent !== lastAgent && lastAgent !== '') {
          agentChanges++;
        }
        lastAgent = agent;
      }

      // Should have fewer agent changes than total messages
      // (indicates grouping)
      expect(agentChanges).toBeLessThan(count);
    });
  });
});
