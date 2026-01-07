/**
 * E2E Test: Project Creation Flow
 *
 * Tests the complete project creation flow including:
 * - Frontend form submission
 * - Backend POST /api/projects/start
 * - Partner agent invocation
 * - Audit plan generation
 * - UI updates with project data
 *
 * @module e2e/02-project-creation.spec
 */

import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import {
  mockClientInfo,
  mockThreadId,
  mockStartAuditResponse,
  expectedPartnerBehavior,
} from './fixtures/mock-audit-data';

test.describe('Project Creation Flow', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
  });

  test('should create new audit project via frontend', async ({ page }) => {
    // ============================================================================
    // STEP 1: Fill out project creation form
    // ============================================================================
    await test.step('Fill project creation form', async () => {
      await dashboardPage.startNewProject(
        mockClientInfo.clientName,
        mockClientInfo.fiscalYear,
        mockClientInfo.overallMateriality
      );
    });

    // ============================================================================
    // STEP 2: Verify POST /api/projects/start request
    // ============================================================================
    await test.step('Verify API request to backend', async () => {
      // Wait for network request to /api/projects/start
      const requestPromise = page.waitForRequest(
        (request) =>
          request.url().includes('/api/projects/start') && request.method() === 'POST'
      );

      const request = await requestPromise;

      // Verify request payload
      const postData = request.postDataJSON();
      expect(postData).toMatchObject({
        client_name: mockClientInfo.clientName,
        fiscal_year: mockClientInfo.fiscalYear,
        overall_materiality: mockClientInfo.overallMateriality,
      });
    });

    // ============================================================================
    // STEP 3: Verify backend response
    // ============================================================================
    await test.step('Verify backend response', async () => {
      // Wait for response from /api/projects/start
      const responsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects/start') && response.status() === 201
      );

      const response = await responsePromise;
      const body = await response.json();

      // Verify response structure
      expect(body).toMatchObject({
        status: 'success',
        next_action: 'await_approval',
      });

      // Verify thread_id format
      expect(body.thread_id).toMatch(/^project-/);
    });

    // ============================================================================
    // STEP 4: Wait for project creation success
    // ============================================================================
    await test.step('Wait for success message', async () => {
      await dashboardPage.waitForProjectCreation();

      // Verify success message is visible
      await expect(dashboardPage.successMessage).toBeVisible();
      await expect(dashboardPage.successMessage).toContainText('Audit project created');
    });

    // ============================================================================
    // STEP 5: Verify Partner agent created audit plan
    // ============================================================================
    await test.step('Verify audit plan created', async () => {
      // Open the newly created project
      await dashboardPage.openProject(mockClientInfo.clientName);

      const taskDetailPage = new TaskDetailPage(page);

      // Verify at least 3 tasks were created (as per expectedPartnerBehavior)
      const taskCount = await taskDetailPage.taskList.count();
      expect(taskCount).toBeGreaterThanOrEqual(expectedPartnerBehavior.tasksCreated);

      // Verify all tasks have status "Pending" initially
      for (let i = 0; i < taskCount; i++) {
        const taskItem = taskDetailPage.taskList.nth(i);
        const status = await taskItem.getAttribute('data-status');
        expect(status).toBe('Pending');
      }
    });

    // ============================================================================
    // STEP 6: Verify UI reflects project data
    // ============================================================================
    await test.step('Verify UI displays project data', async () => {
      // Navigate back to dashboard
      await dashboardPage.goto();

      // Verify project card exists
      const projectCard = dashboardPage.getProjectCard(mockClientInfo.clientName);
      await expect(projectCard).toBeVisible();

      // Verify project details on card
      await expect(projectCard).toContainText(mockClientInfo.clientName);
      await expect(projectCard).toContainText(`FY${mockClientInfo.fiscalYear}`);
      await expect(projectCard).toContainText('Planning'); // Initial status
    });
  });

  test('should handle invalid project data gracefully', async ({ page }) => {
    // ============================================================================
    // STEP 1: Submit invalid data (negative materiality)
    // ============================================================================
    await test.step('Submit invalid materiality', async () => {
      await dashboardPage.startNewProject(
        'Invalid Corp',
        2024,
        -1000 // Invalid: negative materiality
      );
    });

    // ============================================================================
    // STEP 2: Verify error response from backend
    // ============================================================================
    await test.step('Verify 400 error response', async () => {
      const responsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects/start') && response.status() === 400
      );

      const response = await responsePromise;
      const body = await response.json();

      // Verify error structure (FastAPI validation error)
      expect(body).toHaveProperty('detail');
    });

    // ============================================================================
    // STEP 3: Verify UI shows error message
    // ============================================================================
    await test.step('Verify error message displayed', async () => {
      await expect(dashboardPage.errorMessage).toBeVisible();
      await expect(dashboardPage.errorMessage).toContainText('Invalid');
    });
  });

  test('should handle backend unavailable scenario', async ({ page, context }) => {
    // ============================================================================
    // STEP 1: Intercept and fail backend request
    // ============================================================================
    await test.step('Mock backend failure', async () => {
      await page.route('**/api/projects/start', (route) => {
        route.abort('failed'); // Simulate network failure
      });
    });

    // ============================================================================
    // STEP 2: Attempt project creation
    // ============================================================================
    await test.step('Attempt project creation', async () => {
      await dashboardPage.startNewProject(
        mockClientInfo.clientName,
        mockClientInfo.fiscalYear,
        mockClientInfo.overallMateriality
      );
    });

    // ============================================================================
    // STEP 3: Verify error handling
    // ============================================================================
    await test.step('Verify error message', async () => {
      // Should show network error
      await expect(dashboardPage.errorMessage).toBeVisible();
      await expect(dashboardPage.errorMessage).toContainText(/network|connection|failed/i);
    });

    // ============================================================================
    // STEP 4: Verify retry functionality
    // ============================================================================
    await test.step('Verify retry button appears', async () => {
      const retryButton = page.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible();
    });
  });

  test('should create multiple projects sequentially', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create first project
    // ============================================================================
    await test.step('Create first project', async () => {
      await dashboardPage.startNewProject(
        'First Corp',
        2024,
        1000000
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 2: Create second project
    // ============================================================================
    await test.step('Create second project', async () => {
      await dashboardPage.startNewProject(
        'Second Corp',
        2024,
        2000000
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 3: Verify both projects exist
    // ============================================================================
    await test.step('Verify both projects visible', async () => {
      await dashboardPage.goto();

      const projectCount = await dashboardPage.getProjectCount();
      expect(projectCount).toBeGreaterThanOrEqual(2);

      // Verify both project cards exist
      await expect(dashboardPage.getProjectCard('First Corp')).toBeVisible();
      await expect(dashboardPage.getProjectCard('Second Corp')).toBeVisible();
    });
  });

  test('should validate Partner agent response structure', async ({ page }) => {
    // ============================================================================
    // STEP 1: Intercept backend response
    // ============================================================================
    let partnerResponse: any;

    await page.route('**/api/projects/start', async (route) => {
      const response = await route.fetch();
      partnerResponse = await response.json();
      await route.fulfill({ response });
    });

    // ============================================================================
    // STEP 2: Create project
    // ============================================================================
    await test.step('Create project', async () => {
      await dashboardPage.startNewProject(
        mockClientInfo.clientName,
        mockClientInfo.fiscalYear,
        mockClientInfo.overallMateriality
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 3: Verify Partner agent response
    // ============================================================================
    await test.step('Verify Partner agent response structure', async () => {
      expect(partnerResponse).toBeDefined();
      expect(partnerResponse).toHaveProperty('status', 'success');
      expect(partnerResponse).toHaveProperty('thread_id');
      expect(partnerResponse).toHaveProperty('next_action', 'await_approval');

      // Verify thread_id format matches expected pattern
      expect(partnerResponse.thread_id).toMatch(/^project-[a-z0-9-]+-\d{4}$/);
    });
  });
});
