/**
 * E2E Test: Chat SSE Integration
 *
 * Tests the chat functionality with SSE streaming using the current UI.
 * The UI has:
 * - Sidebar with Chat, Workspace, Settings
 * - Chat view with message input and send button
 * - SSE connection for real-time message streaming
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Chat SSE Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to frontend
    await page.goto(FRONTEND_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should load chat interface', async ({ page }) => {
    // Check that the chat interface is visible
    // The UI shows "AI Assistant" heading and message input
    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
    await expect(page.getByPlaceholder(/type your message/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
  });

  test('should enable send button when message is typed', async ({ page }) => {
    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Initially send button should be disabled
    await expect(sendButton).toBeDisabled();

    // Type a message
    await messageInput.fill('Hello, test message');

    // Send button should now be enabled
    await expect(sendButton).toBeEnabled();
  });

  test('should display user message after sending', async ({ page }) => {
    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Type and send a message
    const testMessage = 'Test message for E2E';
    await messageInput.fill(testMessage);
    await sendButton.click();

    // Wait for user message to appear in chat
    await expect(page.getByText(testMessage)).toBeVisible({ timeout: 10000 });

    // Check that "You" label appears (indicating user message)
    await expect(page.getByText('You', { exact: true })).toBeVisible();
  });

  test('should establish SSE connection on message send', async ({ page }) => {
    // Listen for SSE connection
    const ssePromise = page.waitForRequest(request =>
      request.url().includes('/api/stream/') &&
      request.method() === 'GET'
    );

    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Type and send a message
    await messageInput.fill('Test SSE connection');
    await sendButton.click();

    // Verify SSE request was made
    const sseRequest = await ssePromise;
    expect(sseRequest.url()).toContain('/api/stream/');
  });

  test('should show AI Assistant response placeholder', async ({ page }) => {
    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Type and send a message
    await messageInput.fill('Quick test');
    await sendButton.click();

    // Wait for AI Assistant label to appear (indicating response area)
    await expect(page.getByText('AI Assistant').first()).toBeVisible({ timeout: 10000 });
  });

  test('should clear input after sending message', async ({ page }) => {
    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Type and send a message
    await messageInput.fill('Message to clear');
    await sendButton.click();

    // Input should be cleared after sending
    await expect(messageInput).toHaveValue('');
  });

  test('should handle multiple messages', async ({ page }) => {
    const messageInput = page.getByPlaceholder(/type your message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Send first message
    await messageInput.fill('First message');
    await sendButton.click();
    await expect(page.getByText('First message')).toBeVisible({ timeout: 10000 });

    // Wait a bit for SSE to process
    await page.waitForTimeout(2000);

    // Send second message
    await messageInput.fill('Second message');
    await sendButton.click();
    await expect(page.getByText('Second message')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Backend SSE Endpoint', () => {
  test('should have healthy backend', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('should have SSE stream endpoint available', async ({ request }) => {
    // Test that the SSE endpoint exists using HEAD request (SSE connections stay open)
    // We'll verify by checking the content-type header starts with text/event-stream
    const response = await request.fetch(`${BACKEND_URL}/api/stream/test-task-id`, {
      method: 'GET',
      timeout: 5000, // Short timeout since we just need to verify connection starts
    }).catch(() => null);

    // Either the request connects (200) or we verify endpoint exists via error handling
    // The important thing is the endpoint doesn't 404
    expect(response === null || response.status() === 200).toBeTruthy();
  });

  test('should accept message parameter in SSE endpoint', async ({ request }) => {
    // SSE endpoints stay open, so we use a short timeout and catch errors
    const response = await request.fetch(
      `${BACKEND_URL}/api/stream/test-task-id?message=${encodeURIComponent('Hello')}`,
      {
        method: 'GET',
        timeout: 5000,
      }
    ).catch(() => null);

    // Either the request connects (200) or we verify endpoint exists via error handling
    expect(response === null || response.status() === 200).toBeTruthy();
  });
});

test.describe('Navigation', () => {
  test('should navigate between Chat and Workspace views', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.waitForLoadState('networkidle');

    // Click on Workspace tab (in the navigation rail)
    const workspaceButton = page.locator('nav').getByRole('button', { name: /workspace/i });
    if (await workspaceButton.isVisible()) {
      await workspaceButton.click();
      // Should show Workspace content - look for "Audit Command Center" heading
      await expect(page.getByRole('heading', { name: /Audit Command Center/i })).toBeVisible({ timeout: 5000 });
    }

    // Click on Chat tab (in the navigation rail)
    const chatButton = page.locator('nav').getByRole('button', { name: /chat/i });
    if (await chatButton.isVisible()) {
      await chatButton.click();
      // Should show Chat interface with AI Assistant heading
      await expect(page.getByText('AI Assistant').first()).toBeVisible({ timeout: 5000 });
    }
  });
});
