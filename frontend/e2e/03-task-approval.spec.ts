/**
 * E2E Test: Task Approval Flow
 *
 * Tests the complete task approval flow including:
 * - Loading project with pending approval
 * - User approval action
 * - Backend POST /api/tasks/approve
 * - Manager agent spawning Staff agents
 * - Task status transitions (Pending → In-Progress → Completed)
 *
 * @module e2e/03-task-approval.spec
 */

import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import {
  mockClientInfo,
  mockThreadId,
  mockApprovalResponse,
  expectedManagerBehavior,
} from './fixtures/mock-audit-data';

test.describe('Task Approval Flow', () => {
  let dashboardPage: DashboardPage;
  let taskDetailPage: TaskDetailPage;
  let testThreadId: string;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    taskDetailPage = new TaskDetailPage(page);

    // Create a project first (setup for approval tests)
    await dashboardPage.goto();
    await dashboardPage.startNewProject(
      mockClientInfo.clientName,
      mockClientInfo.fiscalYear,
      mockClientInfo.overallMateriality
    );
    await dashboardPage.waitForProjectCreation();

    // Extract thread_id from response
    const response = await page.waitForResponse(
      (res) => res.url().includes('/api/projects/start') && res.status() === 201
    );
    const body = await response.json();
    testThreadId = body.thread_id;

    // Navigate to task detail page
    await dashboardPage.openProject(mockClientInfo.clientName);
  });

  test('should approve task and trigger Manager agent', async ({ page }) => {
    // ============================================================================
    // STEP 1: Verify approval button is visible
    // ============================================================================
    await test.step('Verify approval button visible', async () => {
      await taskDetailPage.waitForApprovalButton();
      await expect(taskDetailPage.approveButton).toBeVisible();
      await expect(taskDetailPage.approveButton).toBeEnabled();
    });

    // ============================================================================
    // STEP 2: Click approve button
    // ============================================================================
    await test.step('Click approve button', async () => {
      await taskDetailPage.approveTask();
    });

    // ============================================================================
    // STEP 3: Verify POST /api/tasks/approve request
    // ============================================================================
    await test.step('Verify API request', async () => {
      const requestPromise = page.waitForRequest(
        (request) =>
          request.url().includes('/api/tasks/approve') && request.method() === 'POST'
      );

      const request = await requestPromise;
      const postData = request.postDataJSON();

      // Verify request payload
      expect(postData).toMatchObject({
        thread_id: testThreadId,
        approved: true,
      });
    });

    // ============================================================================
    // STEP 4: Verify backend response
    // ============================================================================
    await test.step('Verify backend response', async () => {
      const responsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/tasks/approve') && response.status() === 200
      );

      const response = await responsePromise;
      const body = await response.json();

      // Verify response structure
      expect(body).toMatchObject({
        status: 'resumed',
        thread_id: testThreadId,
        task_status: 'In-Progress',
      });
    });

    // ============================================================================
    // STEP 5: Verify Manager spawns Staff agents
    // ============================================================================
    await test.step('Verify Manager agent spawns Staff agents', async () => {
      // Wait for status change to In-Progress (indicates Manager has assigned tasks)
      await taskDetailPage.waitForStatusChange('In-Progress', 10000);

      // Verify task status updated
      const status = await taskDetailPage.getStatus();
      expect(status).toContain('In-Progress');

      // Verify agent messages indicate staff assignment
      await taskDetailPage.waitForNewMessage(5000);
      const messages = await taskDetailPage.getMessages();

      // Should contain Manager's assignment message
      const hasManagerMessage = messages.some((msg) =>
        msg.includes('Assigning') || msg.includes('Task assigned')
      );
      expect(hasManagerMessage).toBe(true);
    });

    // ============================================================================
    // STEP 6: Verify task status transitions
    // ============================================================================
    await test.step('Verify status transitions', async () => {
      // Wait for completion
      await taskDetailPage.waitForCompletion(30000);

      // Verify final status
      const finalStatus = await taskDetailPage.getStatus();
      expect(finalStatus).toContain('Completed');
    });
  });

  test('should reject task and stop workflow', async ({ page }) => {
    // ============================================================================
    // STEP 1: Click reject button
    // ============================================================================
    await test.step('Click reject button', async () => {
      await taskDetailPage.waitForApprovalButton();
      await taskDetailPage.rejectTask();
    });

    // ============================================================================
    // STEP 2: Verify POST /api/tasks/approve with approved=false
    // ============================================================================
    await test.step('Verify rejection request', async () => {
      const requestPromise = page.waitForRequest(
        (request) =>
          request.url().includes('/api/tasks/approve') && request.method() === 'POST'
      );

      const request = await requestPromise;
      const postData = request.postDataJSON();

      // Verify rejection payload
      expect(postData).toMatchObject({
        thread_id: testThreadId,
        approved: false,
      });
    });

    // ============================================================================
    // STEP 3: Verify workflow stops
    // ============================================================================
    await test.step('Verify workflow stopped', async () => {
      // Wait a bit to ensure no status change happens
      await page.waitForTimeout(3000);

      // Status should remain Pending
      const status = await taskDetailPage.getStatus();
      expect(status).toContain('Pending');

      // No new messages should appear
      const messageCount = await taskDetailPage.chatMessages.count();
      await page.waitForTimeout(2000);
      const newMessageCount = await taskDetailPage.chatMessages.count();
      expect(newMessageCount).toBe(messageCount);
    });
  });

  test('should handle approval of multiple tasks', async ({ page }) => {
    // ============================================================================
    // STEP 1: Get all pending tasks
    // ============================================================================
    const taskCount = await taskDetailPage.taskList.count();
    expect(taskCount).toBeGreaterThanOrEqual(3);

    // ============================================================================
    // STEP 2: Approve first task
    // ============================================================================
    await test.step('Approve first task', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForStatusChange('In-Progress', 10000);
    });

    // ============================================================================
    // STEP 3: Wait for first task to complete
    // ============================================================================
    await test.step('Wait for first task completion', async () => {
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 4: Move to next pending task
    // ============================================================================
    await test.step('Move to second task', async () => {
      // Find next pending task
      const tasks = await taskDetailPage.taskList.all();
      for (const task of tasks) {
        const status = await task.getAttribute('data-status');
        if (status === 'Pending') {
          await task.click();
          break;
        }
      }
    });

    // ============================================================================
    // STEP 5: Approve second task
    // ============================================================================
    await test.step('Approve second task', async () => {
      await taskDetailPage.waitForApprovalButton();
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForStatusChange('In-Progress', 10000);
    });
  });

  test('should track task status changes over time', async ({ page }) => {
    const statusChanges: { status: string; timestamp: number }[] = [];

    // ============================================================================
    // STEP 1: Monitor task status changes
    // ============================================================================
    await test.step('Setup status monitoring', async () => {
      // Record initial status
      const initialStatus = await taskDetailPage.getStatus();
      statusChanges.push({
        status: initialStatus,
        timestamp: Date.now(),
      });

      // Monitor status changes via DOM mutation observer
      await page.evaluate(() => {
        const statusElement = document.querySelector('[data-testid="task-status"]');
        if (statusElement) {
          const observer = new MutationObserver(() => {
            const status = statusElement.textContent || '';
            (window as any).statusChanges = (window as any).statusChanges || [];
            (window as any).statusChanges.push({
              status,
              timestamp: Date.now(),
            });
          });
          observer.observe(statusElement, {
            childList: true,
            characterData: true,
            subtree: true,
          });
        }
      });
    });

    // ============================================================================
    // STEP 2: Approve task and track changes
    // ============================================================================
    await test.step('Approve and track', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 3: Verify status transition sequence
    // ============================================================================
    await test.step('Verify status transitions', async () => {
      const changes = await page.evaluate(() => (window as any).statusChanges || []);

      // Should have transitions: Pending → In-Progress → Completed
      expect(changes.length).toBeGreaterThanOrEqual(2);

      // Verify sequence
      const statuses = changes.map((c: any) => c.status);
      expect(statuses).toContain('In-Progress');
      expect(statuses[statuses.length - 1]).toContain('Completed');
    });
  });

  test('should handle approval timeout gracefully', async ({ page }) => {
    // ============================================================================
    // STEP 1: Mock slow backend response
    // ============================================================================
    await test.step('Mock slow response', async () => {
      await page.route('**/api/tasks/approve', async (route) => {
        // Delay response by 10 seconds
        await new Promise((resolve) => setTimeout(resolve, 10000));
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockApprovalResponse),
        });
      });
    });

    // ============================================================================
    // STEP 2: Attempt approval
    // ============================================================================
    await test.step('Click approve', async () => {
      await taskDetailPage.approveTask();
    });

    // ============================================================================
    // STEP 3: Verify loading indicator
    // ============================================================================
    await test.step('Verify loading state', async () => {
      // Should show loading indicator
      await expect(taskDetailPage.loadingSpinner).toBeVisible();

      // Approve button should be disabled
      await expect(taskDetailPage.approveButton).toBeDisabled();
    });

    // ============================================================================
    // STEP 4: Wait for eventual success
    // ============================================================================
    await test.step('Wait for eventual success', async () => {
      await taskDetailPage.waitForStatusChange('In-Progress', 15000);
      await expect(taskDetailPage.loadingSpinner).toBeHidden();
    });
  });

  test('should display Manager agent messages during approval', async ({ page }) => {
    // ============================================================================
    // STEP 1: Approve task
    // ============================================================================
    await test.step('Approve task', async () => {
      await taskDetailPage.approveTask();
    });

    // ============================================================================
    // STEP 2: Wait for Manager messages
    // ============================================================================
    await test.step('Wait for Manager messages', async () => {
      // Should receive Manager agent messages
      await taskDetailPage.waitForNewMessage(5000);

      const managerMessages = await taskDetailPage.getMessagesByAgent('manager');
      expect(managerMessages.length).toBeGreaterThan(0);

      // Verify Manager message content
      const hasAssignmentMessage = managerMessages.some((msg) =>
        msg.includes('Assigning') || msg.includes('Manager')
      );
      expect(hasAssignmentMessage).toBe(true);
    });

    // ============================================================================
    // STEP 3: Verify Staff agent messages appear
    // ============================================================================
    await test.step('Verify Staff messages', async () => {
      // Wait for Staff agent messages
      await page.waitForTimeout(2000);

      const auditorMessages = await taskDetailPage.getMessagesByAgent('auditor');
      expect(auditorMessages.length).toBeGreaterThan(0);
    });
  });
});
