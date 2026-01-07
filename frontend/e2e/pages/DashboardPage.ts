/**
 * Dashboard Page Object
 *
 * Encapsulates interactions with the dashboard UI for audit projects.
 * Follows Page Object Model pattern for maintainable E2E tests.
 *
 * @module e2e/pages/DashboardPage
 */

import { Page, Locator } from '@playwright/test';
import { ROUTES } from '../config/routes';

export class DashboardPage {
  readonly page: Page;

  // Locators
  readonly newProjectButton: Locator;
  readonly clientNameInput: Locator;
  readonly fiscalYearInput: Locator;
  readonly materialityInput: Locator;
  readonly startAuditButton: Locator;
  readonly projectCards: Locator;
  readonly loadingSpinner: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;

  constructor(page: Page) {
    this.page = page;

    // Initialize locators
    this.newProjectButton = page.getByRole('button', { name: /new project/i });
    this.clientNameInput = page.getByLabel(/client name/i);
    this.fiscalYearInput = page.getByLabel(/fiscal year/i);
    this.materialityInput = page.getByLabel(/materiality/i);
    this.startAuditButton = page.getByRole('button', { name: /start audit/i });
    this.projectCards = page.locator('[data-testid="project-card"]');
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
  }

  /**
   * Navigate to dashboard page
   * Note: Dashboard is at /workspace/dashboard in TanStack Router
   */
  async goto(): Promise<void> {
    await this.page.goto(ROUTES.workspace.dashboard);
  }

  /**
   * Start a new audit project with given details
   */
  async startNewProject(
    clientName: string,
    fiscalYear: number,
    materiality: number
  ): Promise<void> {
    await this.newProjectButton.click();
    await this.clientNameInput.fill(clientName);
    await this.fiscalYearInput.fill(fiscalYear.toString());
    await this.materialityInput.fill(materiality.toString());
    await this.startAuditButton.click();
  }

  /**
   * Wait for project creation success
   */
  async waitForProjectCreation(): Promise<void> {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 10000 });
    await this.successMessage.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Get project card by client name
   */
  getProjectCard(clientName: string): Locator {
    return this.page.locator(`[data-testid="project-card"][data-client="${clientName}"]`);
  }

  /**
   * Navigate to project detail page
   */
  async openProject(clientName: string): Promise<void> {
    const card = this.getProjectCard(clientName);
    await card.click();
  }

  /**
   * Check if project exists in list
   */
  async hasProject(clientName: string): Promise<boolean> {
    const card = this.getProjectCard(clientName);
    return card.isVisible();
  }

  /**
   * Get total number of projects
   */
  async getProjectCount(): Promise<number> {
    return this.projectCards.count();
  }
}
