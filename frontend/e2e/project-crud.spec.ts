/**
 * E2E Integration Test: Project CRUD Flow
 *
 * Tests the complete project CRUD lifecycle:
 * - Create project via UI (frontend ↔ backend ↔ Supabase)
 * - Verify project appears in dropdown
 * - Select project
 * - Verify selection persists on refresh
 *
 * @module e2e/project-crud.spec
 */

import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';
import { ROUTES } from './config/routes';
import {
  mockClientInfo,
  mockClientInfo2,
} from './fixtures/mock-audit-data';

/**
 * Page Object for Project Selector interactions
 */
class ProjectSelectorPage {
  constructor(private page: import('@playwright/test').Page) {}

  // Locators
  get projectSelectorTrigger() {
    return this.page.getByRole('button', { name: /select a project|loading projects/i });
  }

  get projectDropdown() {
    return this.page.locator('[role="menu"]');
  }

  get newProjectButton() {
    return this.page.getByRole('menuitem', { name: /new project/i });
  }

  get projectItems() {
    return this.page.locator('[role="menuitem"]').filter({ hasNot: this.page.locator('text=New Project') });
  }

  get noProjectsMessage() {
    return this.page.locator('text=No projects found');
  }

  /**
   * Open the project selector dropdown
   */
  async openDropdown(): Promise<void> {
    await this.projectSelectorTrigger.click();
    await this.projectDropdown.waitFor({ state: 'visible' });
  }

  /**
   * Select a project by client name
   */
  async selectProject(clientName: string): Promise<void> {
    await this.openDropdown();
    const projectItem = this.page.getByRole('menuitem').filter({ hasText: clientName });
    await projectItem.click();
  }

  /**
   * Check if a project exists in the dropdown
   */
  async hasProject(clientName: string): Promise<boolean> {
    await this.openDropdown();
    const projectItem = this.page.getByRole('menuitem').filter({ hasText: clientName });
    const isVisible = await projectItem.isVisible();
    // Close dropdown by pressing Escape
    await this.page.keyboard.press('Escape');
    return isVisible;
  }

  /**
   * Get the currently selected project name from the trigger button
   */
  async getSelectedProjectName(): Promise<string | null> {
    const triggerText = await this.projectSelectorTrigger.textContent();
    if (triggerText?.includes('Select a project') || triggerText?.includes('Loading')) {
      return null;
    }
    // Extract client name from trigger (format: "ClientName FYYear")
    const match = triggerText?.match(/^(.+?)\s+FY\d+/);
    return match ? match[1].trim() : triggerText?.trim() || null;
  }

  /**
   * Wait for projects to load
   */
  async waitForProjectsLoaded(): Promise<void> {
    await this.page.waitForFunction(
      () => {
        const button = document.querySelector('[role="button"]');
        return button && !button.textContent?.includes('Loading');
      },
      { timeout: 10000 }
    );
  }

  /**
   * Get the count of projects in the dropdown
   */
  async getProjectCount(): Promise<number> {
    await this.openDropdown();
    // Count menu items that are not "New Project"
    const items = this.page.getByRole('menuitem');
    const count = await items.count();
    // Subtract 1 for "New Project" button if present
    const hasNewProjectButton = await this.newProjectButton.isVisible().catch(() => false);
    await this.page.keyboard.press('Escape');
    return hasNewProjectButton ? count - 1 : count;
  }
}

test.describe('Project CRUD Integration Flow', () => {
  let dashboardPage: DashboardPage;
  let projectSelector: ProjectSelectorPage;

  // Generate unique client name for each test run to avoid conflicts
  const testClientName = `Test Corp ${Date.now()}`;
  const testFiscalYear = 2024;
  const testMateriality = 750000;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    projectSelector = new ProjectSelectorPage(page);
    await dashboardPage.goto();
  });

  test('should complete full CRUD flow: create → verify → select → persist', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create project via UI
    // ============================================================================
    await test.step('Create project via UI', async () => {
      // Start the project creation flow
      await dashboardPage.startNewProject(
        testClientName,
        testFiscalYear,
        testMateriality
      );

      // Wait for the POST request to /api/projects/start
      const responsePromise = page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects/start') &&
          (response.status() === 200 || response.status() === 201)
      );

      const response = await responsePromise;
      const body = await response.json();

      // Verify response indicates success
      expect(body).toHaveProperty('status', 'success');

      // Wait for success message
      await dashboardPage.waitForProjectCreation();
      await expect(dashboardPage.successMessage).toBeVisible();
    });

    // ============================================================================
    // STEP 2: Verify project appears in dropdown
    // ============================================================================
    await test.step('Verify project appears in dropdown', async () => {
      // Wait for projects to reload
      await projectSelector.waitForProjectsLoaded();

      // Open dropdown and check for new project
      const hasProject = await projectSelector.hasProject(testClientName);
      expect(hasProject).toBe(true);
    });

    // ============================================================================
    // STEP 3: Select project
    // ============================================================================
    await test.step('Select project from dropdown', async () => {
      await projectSelector.selectProject(testClientName);

      // Verify selection is reflected in the trigger button
      const selectedName = await projectSelector.getSelectedProjectName();
      expect(selectedName).toBe(testClientName);
    });

    // ============================================================================
    // STEP 4: Verify selection persists on refresh
    // ============================================================================
    await test.step('Verify selection persists on refresh', async () => {
      // Refresh the page
      await page.reload();

      // Wait for page to fully load
      await projectSelector.waitForProjectsLoaded();

      // Verify the same project is still selected (from localStorage)
      const selectedName = await projectSelector.getSelectedProjectName();
      expect(selectedName).toBe(testClientName);
    });
  });

  test('should verify project appears in project card list after creation', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create a new project
    // ============================================================================
    await test.step('Create new project', async () => {
      await dashboardPage.startNewProject(
        mockClientInfo.clientName,
        mockClientInfo.fiscalYear,
        mockClientInfo.overallMateriality
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 2: Verify project card exists on dashboard
    // ============================================================================
    await test.step('Verify project card on dashboard', async () => {
      // Navigate back to dashboard to see project cards
      await dashboardPage.goto();

      // Verify project card is visible
      const projectCard = dashboardPage.getProjectCard(mockClientInfo.clientName);
      await expect(projectCard).toBeVisible();

      // Verify card contains expected data
      await expect(projectCard).toContainText(mockClientInfo.clientName);
      await expect(projectCard).toContainText(`FY${mockClientInfo.fiscalYear}`);
    });
  });

  test('should handle project selection state correctly across navigation', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create and select a project
    // ============================================================================
    await test.step('Create and select project', async () => {
      await dashboardPage.startNewProject(
        mockClientInfo2.clientName,
        mockClientInfo2.fiscalYear,
        mockClientInfo2.overallMateriality
      );
      await dashboardPage.waitForProjectCreation();
      await projectSelector.waitForProjectsLoaded();
      await projectSelector.selectProject(mockClientInfo2.clientName);
    });

    // ============================================================================
    // STEP 2: Navigate to different page
    // ============================================================================
    await test.step('Navigate to tasks page', async () => {
      await page.goto(ROUTES.workspace.tasks);
      await page.waitForLoadState('networkidle');
    });

    // ============================================================================
    // STEP 3: Verify selection persists after navigation
    // ============================================================================
    await test.step('Verify selection persists', async () => {
      await projectSelector.waitForProjectsLoaded();
      const selectedName = await projectSelector.getSelectedProjectName();
      expect(selectedName).toBe(mockClientInfo2.clientName);
    });

    // ============================================================================
    // STEP 4: Navigate back to dashboard
    // ============================================================================
    await test.step('Navigate back to dashboard', async () => {
      await dashboardPage.goto();
      await projectSelector.waitForProjectsLoaded();

      // Selection should still persist
      const selectedName = await projectSelector.getSelectedProjectName();
      expect(selectedName).toBe(mockClientInfo2.clientName);
    });
  });

  test('should show empty state when no projects exist', async ({ page, context }) => {
    // ============================================================================
    // STEP 1: Clear localStorage to simulate fresh state
    // ============================================================================
    await test.step('Clear project state', async () => {
      await context.clearCookies();
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
    });

    // ============================================================================
    // STEP 2: Mock empty projects response
    // ============================================================================
    await test.step('Mock empty projects API', async () => {
      await page.route('**/audit_projects*', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], error: null }),
        });
      });
    });

    // ============================================================================
    // STEP 3: Navigate to dashboard
    // ============================================================================
    await test.step('Navigate to dashboard', async () => {
      await page.goto(ROUTES.workspace.dashboard);
      await projectSelector.waitForProjectsLoaded();
    });

    // ============================================================================
    // STEP 4: Verify empty state in dropdown
    // ============================================================================
    await test.step('Verify empty state', async () => {
      await projectSelector.openDropdown();
      await expect(projectSelector.noProjectsMessage).toBeVisible();
    });
  });

  test('should update project list via Supabase realtime subscription', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create initial project
    // ============================================================================
    await test.step('Create initial project', async () => {
      await dashboardPage.startNewProject(
        testClientName,
        testFiscalYear,
        testMateriality
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 2: Get initial project count
    // ============================================================================
    let initialCount: number;
    await test.step('Get initial count', async () => {
      await projectSelector.waitForProjectsLoaded();
      initialCount = await projectSelector.getProjectCount();
      expect(initialCount).toBeGreaterThanOrEqual(1);
    });

    // ============================================================================
    // STEP 3: Create another project
    // ============================================================================
    await test.step('Create second project', async () => {
      const secondClientName = `Second Corp ${Date.now()}`;
      await dashboardPage.startNewProject(
        secondClientName,
        2025,
        500000
      );
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 4: Verify project count increased
    // ============================================================================
    await test.step('Verify realtime update', async () => {
      // Wait for realtime subscription to update
      await page.waitForTimeout(1000);
      await projectSelector.waitForProjectsLoaded();

      const newCount = await projectSelector.getProjectCount();
      expect(newCount).toBeGreaterThan(initialCount!);
    });
  });

  test('should validate required fields in project creation form', async ({ page }) => {
    // ============================================================================
    // STEP 1: Click new project button
    // ============================================================================
    await test.step('Open project creation form', async () => {
      await dashboardPage.newProjectButton.click();
    });

    // ============================================================================
    // STEP 2: Try to submit without filling required fields
    // ============================================================================
    await test.step('Submit empty form', async () => {
      await dashboardPage.startAuditButton.click();
    });

    // ============================================================================
    // STEP 3: Verify validation errors shown
    // ============================================================================
    await test.step('Verify validation errors', async () => {
      // Check for validation messages - exact selectors depend on UI implementation
      const validationError = page.locator('[data-testid="validation-error"]').or(
        page.locator('.text-destructive')
      ).or(
        page.locator('[role="alert"]')
      );

      // At least one validation error should be visible
      await expect(validationError.first()).toBeVisible({ timeout: 5000 });
    });
  });

  test('should handle API error gracefully when creating project', async ({ page }) => {
    // ============================================================================
    // STEP 1: Mock API failure
    // ============================================================================
    await test.step('Mock API error', async () => {
      await page.route('**/api/projects/start', (route) => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });
    });

    // ============================================================================
    // STEP 2: Attempt project creation
    // ============================================================================
    await test.step('Attempt project creation', async () => {
      await dashboardPage.startNewProject(
        'Error Test Corp',
        2024,
        500000
      );
    });

    // ============================================================================
    // STEP 3: Verify error message displayed
    // ============================================================================
    await test.step('Verify error handling', async () => {
      await expect(dashboardPage.errorMessage).toBeVisible();
    });
  });

  test('should switch between multiple projects correctly', async ({ page }) => {
    // ============================================================================
    // STEP 1: Create two projects
    // ============================================================================
    const firstClient = `First Corp ${Date.now()}`;
    const secondClient = `Second Corp ${Date.now()}`;

    await test.step('Create first project', async () => {
      await dashboardPage.startNewProject(firstClient, 2024, 1000000);
      await dashboardPage.waitForProjectCreation();
    });

    await test.step('Create second project', async () => {
      await dashboardPage.startNewProject(secondClient, 2024, 2000000);
      await dashboardPage.waitForProjectCreation();
    });

    // ============================================================================
    // STEP 2: Select first project
    // ============================================================================
    await test.step('Select first project', async () => {
      await projectSelector.waitForProjectsLoaded();
      await projectSelector.selectProject(firstClient);

      const selected = await projectSelector.getSelectedProjectName();
      expect(selected).toBe(firstClient);
    });

    // ============================================================================
    // STEP 3: Switch to second project
    // ============================================================================
    await test.step('Switch to second project', async () => {
      await projectSelector.selectProject(secondClient);

      const selected = await projectSelector.getSelectedProjectName();
      expect(selected).toBe(secondClient);
    });

    // ============================================================================
    // STEP 4: Verify switch persists on refresh
    // ============================================================================
    await test.step('Verify switch persists', async () => {
      await page.reload();
      await projectSelector.waitForProjectsLoaded();

      const selected = await projectSelector.getSelectedProjectName();
      expect(selected).toBe(secondClient);
    });
  });
});
