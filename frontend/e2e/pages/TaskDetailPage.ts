/**
 * Task Detail Page Object
 *
 * Encapsulates interactions with task detail view including approval flow,
 * agent messages, and task status updates.
 *
 * @module e2e/pages/TaskDetailPage
 */

import { Page, Locator } from '@playwright/test';
import { ROUTES } from '../config/routes';

export class TaskDetailPage {
  readonly page: Page;

  // Locators
  readonly taskTitle: Locator;
  readonly taskStatus: Locator;
  readonly riskScore: Locator;
  readonly approveButton: Locator;
  readonly rejectButton: Locator;
  readonly chatMessages: Locator;
  readonly chatInput: Locator;
  readonly sendMessageButton: Locator;
  readonly agentIndicator: Locator;
  readonly taskList: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;

    // Initialize locators
    this.taskTitle = page.locator('[data-testid="task-title"]');
    this.taskStatus = page.locator('[data-testid="task-status"]');
    this.riskScore = page.locator('[data-testid="risk-score"]');
    this.approveButton = page.getByRole('button', { name: /approve/i });
    this.rejectButton = page.getByRole('button', { name: /reject/i });
    this.chatMessages = page.locator('[data-testid="chat-message"]');
    this.chatInput = page.getByPlaceholder(/type a message/i);
    this.sendMessageButton = page.getByRole('button', { name: /send/i });
    this.agentIndicator = page.locator('[data-testid="agent-typing-indicator"]');
    this.taskList = page.locator('[data-testid="task-list-item"]');
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]');
  }

  /**
   * Navigate to task detail page
   * Note: Tasks are at /workspace/tasks in TanStack Router
   */
  async goto(taskId?: string): Promise<void> {
    const route = taskId ? `${ROUTES.workspace.tasks}/${taskId}` : ROUTES.workspace.tasks;
    await this.page.goto(route);
  }

  /**
   * Approve the current task
   */
  async approveTask(): Promise<void> {
    await this.approveButton.click();
  }

  /**
   * Reject the current task
   */
  async rejectTask(): Promise<void> {
    await this.rejectButton.click();
  }

  /**
   * Wait for task status to change
   */
  async waitForStatusChange(expectedStatus: string, timeout: number = 10000): Promise<void> {
    await this.page.waitForFunction(
      (status) => {
        const statusElement = document.querySelector('[data-testid="task-status"]');
        return statusElement?.textContent?.includes(status);
      },
      expectedStatus,
      { timeout }
    );
  }

  /**
   * Get current task status
   */
  async getStatus(): Promise<string> {
    return this.taskStatus.textContent() || '';
  }

  /**
   * Get current risk score
   */
  async getRiskScore(): Promise<number> {
    const text = await this.riskScore.textContent();
    return parseFloat(text || '0');
  }

  /**
   * Wait for new agent message
   */
  async waitForNewMessage(timeout: number = 5000): Promise<void> {
    const initialCount = await this.chatMessages.count();
    await this.page.waitForFunction(
      (expectedCount) => {
        const messages = document.querySelectorAll('[data-testid="chat-message"]');
        return messages.length > expectedCount;
      },
      initialCount,
      { timeout }
    );
  }

  /**
   * Get all chat messages
   */
  async getMessages(): Promise<string[]> {
    const count = await this.chatMessages.count();
    const messages: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await this.chatMessages.nth(i).textContent();
      if (text) messages.push(text);
    }
    return messages;
  }

  /**
   * Get message by agent role
   */
  async getMessagesByAgent(agentRole: string): Promise<string[]> {
    const messages = this.page.locator(`[data-testid="chat-message"][data-agent="${agentRole}"]`);
    const count = await messages.count();
    const result: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await messages.nth(i).textContent();
      if (text) result.push(text);
    }
    return result;
  }

  /**
   * Check if agent is typing
   */
  async isAgentTyping(): Promise<boolean> {
    return this.agentIndicator.isVisible();
  }

  /**
   * Send a message in chat
   */
  async sendMessage(message: string): Promise<void> {
    await this.chatInput.fill(message);
    await this.sendMessageButton.click();
  }

  /**
   * Get task list item by category
   */
  getTaskItem(category: string): Locator {
    return this.page.locator(`[data-testid="task-list-item"][data-category="${category}"]`);
  }

  /**
   * Wait for approval button to appear
   */
  async waitForApprovalButton(timeout: number = 5000): Promise<void> {
    await this.approveButton.waitFor({ state: 'visible', timeout });
  }

  /**
   * Wait for task completion
   */
  async waitForCompletion(timeout: number = 30000): Promise<void> {
    await this.waitForStatusChange('Completed', timeout);
  }
}
