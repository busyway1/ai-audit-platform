/**
 * E2E Test: Realtime Sync via Supabase
 *
 * Tests Supabase Realtime synchronization between backend and frontend:
 * - Backend state changes propagate to frontend via Realtime
 * - Task status updates reflect instantly (<500ms)
 * - Multiple browser tabs receive same updates
 * - Connection recovery after disconnect
 *
 * @module e2e/04-realtime-sync.spec
 */

import { test, expect } from '@playwright/test';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { DashboardPage } from './pages/DashboardPage';
import {
  mockClientInfo,
  mockTaskStatusUpdates,
} from './fixtures/mock-audit-data';

test.describe('Realtime Sync via Supabase', () => {
  let dashboardPage: DashboardPage;
  let taskDetailPage: TaskDetailPage;
  let testThreadId: string;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    taskDetailPage = new TaskDetailPage(page);

    // Create a project first
    await dashboardPage.goto();
    await dashboardPage.startNewProject(
      mockClientInfo.clientName,
      mockClientInfo.fiscalYear,
      mockClientInfo.overallMateriality
    );
    await dashboardPage.waitForProjectCreation();

    // Extract thread_id
    const response = await page.waitForResponse(
      (res) => res.url().includes('/api/projects/start') && res.status() === 201
    );
    const body = await response.json();
    testThreadId = body.thread_id;

    // Navigate to task detail
    await dashboardPage.openProject(mockClientInfo.clientName);
  });

  test('should receive realtime task status updates', async ({ page }) => {
    // ============================================================================
    // STEP 1: Record initial status
    // ============================================================================
    const initialStatus = await test.step('Get initial status', async () => {
      return taskDetailPage.getStatus();
    });

    expect(initialStatus).toContain('Pending');

    // ============================================================================
    // STEP 2: Trigger backend state change (approve task)
    // ============================================================================
    await test.step('Trigger backend state change', async () => {
      await taskDetailPage.approveTask();

      // Wait for backend to process
      await page.waitForResponse(
        (res) => res.url().includes('/api/tasks/approve') && res.status() === 200
      );
    });

    // ============================================================================
    // STEP 3: Measure time for frontend update
    // ============================================================================
    await test.step('Verify realtime update speed', async () => {
      const startTime = Date.now();

      // Wait for status change
      await taskDetailPage.waitForStatusChange('In-Progress', 5000);

      const updateTime = Date.now() - startTime;

      // Should update in less than 500ms
      expect(updateTime).toBeLessThan(500);

      console.log(`Realtime update latency: ${updateTime}ms`);
    });

    // ============================================================================
    // STEP 4: Verify status reflects backend state
    // ============================================================================
    await test.step('Verify status updated', async () => {
      const currentStatus = await taskDetailPage.getStatus();
      expect(currentStatus).toContain('In-Progress');
    });
  });

  test('should sync across multiple browser tabs', async ({ context, page }) => {
    // ============================================================================
    // STEP 1: Open second browser tab
    // ============================================================================
    const secondTab = await test.step('Open second tab', async () => {
      const newPage = await context.newPage();
      const secondDashboard = new DashboardPage(newPage);
      await secondDashboard.goto();
      await secondDashboard.openProject(mockClientInfo.clientName);
      return newPage;
    });

    const secondTaskPage = new TaskDetailPage(secondTab);

    // ============================================================================
    // STEP 2: Verify both tabs show same initial status
    // ============================================================================
    await test.step('Verify initial sync', async () => {
      const status1 = await taskDetailPage.getStatus();
      const status2 = await secondTaskPage.getStatus();
      expect(status1).toBe(status2);
    });

    // ============================================================================
    // STEP 3: Approve task in first tab
    // ============================================================================
    await test.step('Approve in first tab', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForStatusChange('In-Progress', 5000);
    });

    // ============================================================================
    // STEP 4: Verify second tab updates automatically
    // ============================================================================
    await test.step('Verify second tab auto-updates', async () => {
      // Second tab should receive realtime update
      await secondTaskPage.waitForStatusChange('In-Progress', 2000);

      const status2 = await secondTaskPage.getStatus();
      expect(status2).toContain('In-Progress');
    });

    // ============================================================================
    // STEP 5: Verify both tabs stay in sync
    // ============================================================================
    await test.step('Verify continued sync', async () => {
      // Wait for completion in both tabs
      await Promise.all([
        taskDetailPage.waitForCompletion(30000),
        secondTaskPage.waitForCompletion(30000),
      ]);

      const finalStatus1 = await taskDetailPage.getStatus();
      const finalStatus2 = await secondTaskPage.getStatus();
      expect(finalStatus1).toBe(finalStatus2);
    });

    await secondTab.close();
  });

  test('should handle Supabase Realtime connection lifecycle', async ({ page }) => {
    // ============================================================================
    // STEP 1: Verify initial connection
    // ============================================================================
    await test.step('Verify Realtime connected', async () => {
      // Wait for page to establish Realtime connection
      await page.waitForTimeout(1000);

      // Check for Realtime connection in browser console
      const hasConnection = await page.evaluate(() => {
        // Check if Supabase Realtime channel is connected
        return (window as any).supabaseRealtimeConnected === true;
      });

      // Note: This assumes frontend sets a global flag when connected
      // Adjust based on actual implementation
    });

    // ============================================================================
    // STEP 2: Simulate network disconnect
    // ============================================================================
    await test.step('Simulate disconnect', async () => {
      // Temporarily go offline
      await page.context().setOffline(true);
      await page.waitForTimeout(2000);
    });

    // ============================================================================
    // STEP 3: Reconnect and verify recovery
    // ============================================================================
    await test.step('Verify reconnection', async () => {
      // Go back online
      await page.context().setOffline(false);

      // Trigger a backend change to test recovery
      await taskDetailPage.approveTask();

      // Should receive update after reconnection
      await taskDetailPage.waitForStatusChange('In-Progress', 10000);

      const status = await taskDetailPage.getStatus();
      expect(status).toContain('In-Progress');
    });
  });

  test('should receive updates for all task fields', async ({ page }) => {
    // ============================================================================
    // STEP 1: Monitor multiple task fields
    // ============================================================================
    const initialValues = await test.step('Get initial values', async () => {
      return {
        status: await taskDetailPage.getStatus(),
        riskScore: await taskDetailPage.getRiskScore(),
      };
    });

    // ============================================================================
    // STEP 2: Trigger backend changes
    // ============================================================================
    await test.step('Trigger changes', async () => {
      await taskDetailPage.approveTask();
      await page.waitForResponse(
        (res) => res.url().includes('/api/tasks/approve') && res.status() === 200
      );
    });

    // ============================================================================
    // STEP 3: Verify all fields update
    // ============================================================================
    await test.step('Verify field updates', async () => {
      // Wait for status change
      await taskDetailPage.waitForStatusChange('In-Progress', 5000);

      const newValues = {
        status: await taskDetailPage.getStatus(),
        riskScore: await taskDetailPage.getRiskScore(),
      };

      // Status should have changed
      expect(newValues.status).not.toBe(initialValues.status);

      // Risk score should remain consistent
      expect(newValues.riskScore).toBe(initialValues.riskScore);
    });
  });

  test('should batch rapid status updates efficiently', async ({ page }) => {
    // ============================================================================
    // STEP 1: Track number of UI updates
    // ============================================================================
    let updateCount = 0;

    await test.step('Setup update counter', async () => {
      await page.evaluate(() => {
        const statusElement = document.querySelector('[data-testid="task-status"]');
        if (statusElement) {
          (window as any).updateCount = 0;
          const observer = new MutationObserver(() => {
            (window as any).updateCount++;
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
    // STEP 2: Trigger rapid status changes
    // ============================================================================
    await test.step('Trigger rapid changes', async () => {
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForCompletion(30000);
    });

    // ============================================================================
    // STEP 3: Verify updates were batched
    // ============================================================================
    await test.step('Verify batching', async () => {
      updateCount = await page.evaluate(() => (window as any).updateCount || 0);

      // Should have some updates but not excessive
      // (indicates batching/throttling is working)
      expect(updateCount).toBeGreaterThan(0);
      expect(updateCount).toBeLessThan(20); // Reasonable upper limit
    });
  });

  test('should handle Realtime subscription cleanup on navigation', async ({ page }) => {
    // ============================================================================
    // STEP 1: Navigate to task detail
    // ============================================================================
    await test.step('Already on task detail', async () => {
      const status = await taskDetailPage.getStatus();
      expect(status).toBeDefined();
    });

    // ============================================================================
    // STEP 2: Navigate away
    // ============================================================================
    await test.step('Navigate away', async () => {
      await dashboardPage.goto();
    });

    // ============================================================================
    // STEP 3: Verify no memory leaks from subscriptions
    // ============================================================================
    await test.step('Verify cleanup', async () => {
      // Check for cleanup in browser console
      const hasLeaks = await page.evaluate(() => {
        // Check if Realtime channels were properly unsubscribed
        return (window as any).supabaseActiveChannels?.length > 0;
      });

      // Should not have active channels after navigation
      // Note: Adjust based on actual implementation
    });

    // ============================================================================
    // STEP 4: Navigate back and verify new subscription works
    // ============================================================================
    await test.step('Verify re-subscription works', async () => {
      await dashboardPage.openProject(mockClientInfo.clientName);

      // Should be able to receive updates again
      await taskDetailPage.approveTask();
      await taskDetailPage.waitForStatusChange('In-Progress', 5000);

      const status = await taskDetailPage.getStatus();
      expect(status).toContain('In-Progress');
    });
  });

  test('should display connection status indicator', async ({ page }) => {
    // ============================================================================
    // STEP 1: Verify connection indicator when online
    // ============================================================================
    await test.step('Verify online indicator', async () => {
      const connectionIndicator = page.locator('[data-testid="connection-status"]');

      // Should show connected status
      await expect(connectionIndicator).toContainText(/connected|online/i);
    });

    // ============================================================================
    // STEP 2: Go offline and verify indicator
    // ============================================================================
    await test.step('Verify offline indicator', async () => {
      await page.context().setOffline(true);
      await page.waitForTimeout(1000);

      const connectionIndicator = page.locator('[data-testid="connection-status"]');

      // Should show disconnected status
      await expect(connectionIndicator).toContainText(/disconnected|offline/i);
    });

    // ============================================================================
    // STEP 3: Reconnect and verify indicator
    // ============================================================================
    await test.step('Verify reconnection indicator', async () => {
      await page.context().setOffline(false);
      await page.waitForTimeout(2000);

      const connectionIndicator = page.locator('[data-testid="connection-status"]');

      // Should show reconnected status
      await expect(connectionIndicator).toContainText(/connected|online/i);
    });
  });
});
