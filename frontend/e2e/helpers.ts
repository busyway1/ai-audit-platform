import { Page } from '@playwright/test';

/**
 * Helper function to create an artifact from a chat query
 */
export async function createArtifact(page: Page, query: string, waitTime = 2000): Promise<void> {
  await page.fill('textarea[placeholder*="Type your message"]', query);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(waitTime);
}

/**
 * Helper function to wait for artifact panel to be visible
 */
export async function waitForArtifactPanel(page: Page, timeout = 5000): Promise<void> {
  await page.waitForSelector('[data-testid="artifact-panel"]', {
    state: 'visible',
    timeout
  });
}

/**
 * Helper function to wait for pending badge to appear and disappear
 */
export async function waitForPendingBadgeLifecycle(page: Page): Promise<void> {
  // Wait for pending badge to appear
  await page.waitForSelector('text=/Pending/i', { state: 'visible', timeout: 5000 });

  // Wait for pending badge to disappear
  await page.waitForSelector('text=/Pending/i', { state: 'hidden', timeout: 5000 });
}

/**
 * Helper function to get artifact tab count
 */
export async function getArtifactTabCount(page: Page): Promise<number> {
  const tabs = page.locator('[data-testid="artifact-tab"]');
  return await tabs.count();
}

/**
 * Helper function to pin an artifact tab by index
 */
export async function pinArtifactTab(page: Page, tabIndex = 0): Promise<void> {
  const tabs = page.locator('[data-testid="artifact-tab"]');
  const pinButton = tabs.nth(tabIndex).locator('[aria-label*="Pin"]');
  await pinButton.click();
}

/**
 * Helper function to close an artifact tab by index
 */
export async function closeArtifactTab(page: Page, tabIndex = 0): Promise<void> {
  const tabs = page.locator('[data-testid="artifact-tab"]');
  const closeButton = tabs.nth(tabIndex).locator('[aria-label*="Close"]');
  await closeButton.click();
  await page.waitForTimeout(500);
}

/**
 * Helper function to get resize handle count (indicates panel layout)
 */
export async function getResizeHandleCount(page: Page): Promise<number> {
  const handles = page.locator('[data-panel-resize-handle-id]');
  return await handles.count();
}

/**
 * Helper function to drag resize handle
 */
export async function dragResizeHandle(
  page: Page,
  handleIndex = 0,
  deltaX = -100
): Promise<void> {
  const resizeHandle = page.locator('[data-panel-resize-handle-id]').nth(handleIndex);
  const handleBox = await resizeHandle.boundingBox();

  if (!handleBox) {
    throw new Error('Resize handle not found or not visible');
  }

  const centerX = handleBox.x + handleBox.width / 2;
  const centerY = handleBox.y + handleBox.height / 2;

  await page.mouse.move(centerX, centerY);
  await page.mouse.down();
  await page.mouse.move(centerX + deltaX, centerY);
  await page.mouse.up();
  await page.waitForTimeout(500);
}

/**
 * Helper function to double-click resize handle (snap to 50/50)
 */
export async function snapResizeHandleTo5050(page: Page, handleIndex = 0): Promise<void> {
  const resizeHandle = page.locator('[data-panel-resize-handle-id]').nth(handleIndex);
  await resizeHandle.dblclick();
  await page.waitForTimeout(500);
}

/**
 * Helper function to get panel width by panel ID
 */
export async function getPanelWidth(page: Page, panelId: string): Promise<number> {
  const panel = page.locator(`[data-panel-id="${panelId}"]`);
  const box = await panel.boundingBox();
  return box?.width ?? 0;
}

/**
 * Helper function to verify panel ratio (for 50/50 checks)
 */
export function verifyPanelRatio(
  width1: number,
  width2: number,
  expectedRatio = 1.0,
  tolerance = 0.05
): boolean {
  const ratio = width1 / width2;
  const minRatio = expectedRatio - tolerance;
  const maxRatio = expectedRatio + tolerance;
  return ratio >= minRatio && ratio <= maxRatio;
}

/**
 * Helper function to setup console log listener
 */
export function setupConsoleListener(page: Page): string[] {
  const consoleLogs: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'log') {
      consoleLogs.push(msg.text());
    }
  });

  return consoleLogs;
}

/**
 * Helper function to setup error listener
 */
export function setupErrorListener(page: Page): string[] {
  const errors: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', error => {
    errors.push(error.message);
  });

  return errors;
}

/**
 * Helper to create multiple artifacts quickly
 */
export async function createMultipleArtifacts(
  page: Page,
  queries: string[],
  waitTimeBetween = 2000
): Promise<void> {
  for (const query of queries) {
    await createArtifact(page, query, waitTimeBetween);
  }
}

/**
 * Common artifact queries for testing
 */
export const ARTIFACT_QUERIES = {
  dashboard: 'Show me the dashboard',
  engagement: 'Show engagement plan',
  task: 'Show task status',
  financial: 'Show financial statements',
  issue: 'Show issue details',
};

/**
 * Helper to verify no console errors occurred
 */
export function verifyNoErrors(errors: string[]): void {
  if (errors.length > 0) {
    throw new Error(`Console errors detected: ${errors.join(', ')}`);
  }
}

/**
 * Helper to send chat message
 */
export async function sendChatMessage(page: Page, message: string): Promise<void> {
  const textarea = page.locator('textarea[placeholder*="Type your message"]');
  await textarea.fill(message);

  const submitButton = page.locator('button[type="submit"]');
  await submitButton.click();
}

/**
 * Helper to wait for chat message containing specific text
 */
export async function waitForChatMessage(
  page: Page,
  messagePattern: string | RegExp,
  timeout = 30000
): Promise<void> {
  const selector = messagePattern instanceof RegExp
    ? `text=${messagePattern.source}`
    : `text=${messagePattern}`;

  await page.waitForSelector(selector, { timeout });
}

/**
 * Helper to get latest chat message text
 */
export async function getLatestChatMessage(page: Page): Promise<string> {
  const messages = page.locator('[data-testid="chat-message"]');
  const count = await messages.count();

  if (count === 0) {
    return '';
  }

  const lastMessage = messages.nth(count - 1);
  return (await lastMessage.textContent()) || '';
}

/**
 * Helper to get all chat messages
 */
export async function getAllChatMessages(page: Page): Promise<string[]> {
  const messages = page.locator('[data-testid="chat-message"]');
  const count = await messages.count();
  const messageTexts: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await messages.nth(i).textContent();
    if (text) {
      messageTexts.push(text);
    }
  }

  return messageTexts;
}

/**
 * Helper to click approve button in artifact
 */
export async function clickApproveButton(page: Page): Promise<void> {
  const approveButton = page.locator(
    'button:has-text("Approve"), button[aria-label*="Approve"]'
  );
  await approveButton.first().click();
}

/**
 * Helper to click edit button in artifact
 */
export async function clickEditButton(page: Page): Promise<void> {
  const editButton = page.locator(
    'button:has-text("Edit"), button[aria-label*="Edit"]'
  );
  await editButton.first().click();
}

/**
 * Helper to check if backend is available
 */
export async function checkBackendHealth(
  backendUrl = process.env.VITE_API_URL || 'http://localhost:8080'
): Promise<boolean> {
  try {
    const response = await fetch(`${backendUrl}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Helper to take screenshot with timestamp
 */
export async function takeTimestampedScreenshot(
  page: Page,
  name: string,
  options?: { fullPage?: boolean }
): Promise<void> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `e2e/screenshots/${name}-${timestamp}.png`;

  await page.screenshot({
    path: filename,
    fullPage: options?.fullPage ?? true,
  });
}

/**
 * Helper to wait for loading state to complete
 */
export async function waitForLoadingComplete(page: Page, timeout = 10000): Promise<void> {
  // Wait for any loading spinners to disappear
  const loadingIndicators = page.locator('[data-testid*="loading"], [aria-busy="true"]');

  try {
    await loadingIndicators.first().waitFor({ state: 'hidden', timeout });
  } catch {
    // No loading indicators found or they disappeared quickly - that's fine
  }
}

/**
 * Helper to measure operation duration
 */
export async function measureDuration<T>(
  operation: () => Promise<T>
): Promise<{ result: T; duration: number }> {
  const start = Date.now();
  const result = await operation();
  const duration = Date.now() - start;

  return { result, duration };
}
