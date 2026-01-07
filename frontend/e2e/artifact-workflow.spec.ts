import { test, expect, Page } from '@playwright/test';
import { URLS } from './config/routes';

test.describe('Artifact Workflow E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to root (chat interface)
    await page.goto(URLS.frontend.root);
    // Wait for app to load
    await page.waitForLoadState('networkidle');
  });

  test.describe('Multi-type Artifact Creation', () => {
    test('should create dashboard artifact from chat query', async ({ page }) => {
      // Type message
      await page.fill('textarea[placeholder*="Type your message"]', 'Show me the dashboard');
      await page.click('button[type="submit"]');

      // Wait for artifact panel to appear
      await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible({ timeout: 5000 });

      // Verify pending badge appears
      await expect(page.locator('text=/Pending/i')).toBeVisible();

      // Wait for completion (pending badge disappears)
      await expect(page.locator('text=/Pending/i')).not.toBeVisible({ timeout: 5000 });

      // Verify artifact content (dashboard specific elements)
      await expect(page.locator('text=/Dashboard/i')).toBeVisible();
    });

    test('should create engagement plan artifact from chat query', async ({ page }) => {
      await page.fill('textarea[placeholder*="Type your message"]', 'Show engagement plan');
      await page.click('button[type="submit"]');

      await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible({ timeout: 5000 });

      // Verify pending badge lifecycle
      await expect(page.locator('text=/Pending/i')).toBeVisible();
      await expect(page.locator('text=/Pending/i')).not.toBeVisible({ timeout: 5000 });

      // Verify engagement plan specific content
      await expect(page.locator('text=/Engagement/i')).toBeVisible();
    });

    test('should create task artifact from chat query', async ({ page }) => {
      await page.fill('textarea[placeholder*="Type your message"]', 'Show task status');
      await page.click('button[type="submit"]');

      await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible({ timeout: 5000 });

      // Verify pending badge lifecycle
      await expect(page.locator('text=/Pending/i')).toBeVisible();
      await expect(page.locator('text=/Pending/i')).not.toBeVisible({ timeout: 5000 });

      // Verify task artifact content
      await expect(page.locator('text=/Task/i')).toBeVisible();
    });

    test('should create financial statements artifact from chat query', async ({ page }) => {
      await page.fill('textarea[placeholder*="Type your message"]', 'Show financial statements');
      await page.click('button[type="submit"]');

      await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible({ timeout: 5000 });

      // Verify pending badge lifecycle
      await expect(page.locator('text=/Pending/i')).toBeVisible();
      await expect(page.locator('text=/Pending/i')).not.toBeVisible({ timeout: 5000 });

      // Verify financial statements content
      await expect(page.locator('text=/Financial/i')).toBeVisible();
    });

    test('should create issue details artifact from chat query', async ({ page }) => {
      await page.fill('textarea[placeholder*="Type your message"]', 'Show issue details');
      await page.click('button[type="submit"]');

      await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible({ timeout: 5000 });

      // Verify pending badge lifecycle
      await expect(page.locator('text=/Pending/i')).toBeVisible();
      await expect(page.locator('text=/Pending/i')).not.toBeVisible({ timeout: 5000 });

      // Verify issue details content
      await expect(page.locator('text=/Issue/i')).toBeVisible();
    });
  });

  test.describe('Tab Management', () => {
    const createArtifact = async (page: Page, query: string) => {
      await page.fill('textarea[placeholder*="Type your message"]', query);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000); // Wait for artifact creation
    };

    test('should display all artifact tabs in tab bar', async ({ page }) => {
      // Create 3 artifacts
      await createArtifact(page, 'Show me the dashboard');
      await createArtifact(page, 'Show engagement plan');
      await createArtifact(page, 'Show task status');

      // Wait for tab bar to be visible
      await expect(page.locator('[data-testid="artifact-tab-bar"]')).toBeVisible();

      // Count tabs (should be 3)
      const tabs = page.locator('[data-testid="artifact-tab"]');
      await expect(tabs).toHaveCount(3);
    });

    test('should switch between artifact tabs correctly', async ({ page }) => {
      // Create 2 artifacts
      await createArtifact(page, 'Show me the dashboard');
      await createArtifact(page, 'Show task status');

      // Get tabs
      const tabs = page.locator('[data-testid="artifact-tab"]');

      // Click first tab
      await tabs.nth(0).click();
      await expect(page.locator('text=/Dashboard/i')).toBeVisible();

      // Click second tab
      await tabs.nth(1).click();
      await expect(page.locator('text=/Task/i')).toBeVisible();
    });

    test('should close artifact tab when X button clicked', async ({ page }) => {
      // Create 2 artifacts
      await createArtifact(page, 'Show me the dashboard');
      await createArtifact(page, 'Show task status');

      // Verify 2 tabs exist
      const tabs = page.locator('[data-testid="artifact-tab"]');
      await expect(tabs).toHaveCount(2);

      // Click close button on first tab
      const closeButton = page.locator('[data-testid="artifact-tab"]').first().locator('[aria-label*="Close"]');
      await closeButton.click();

      // Verify only 1 tab remains
      await expect(tabs).toHaveCount(1);
    });

    test('should handle closing all tabs', async ({ page }) => {
      // Create 3 artifacts
      await createArtifact(page, 'Show me the dashboard');
      await createArtifact(page, 'Show engagement plan');
      await createArtifact(page, 'Show task status');

      const tabs = page.locator('[data-testid="artifact-tab"]');
      await expect(tabs).toHaveCount(3);

      // Close all tabs
      for (let i = 0; i < 3; i++) {
        const closeButton = tabs.first().locator('[aria-label*="Close"]');
        await closeButton.click();
        await page.waitForTimeout(500);
      }

      // Verify no tabs remain
      await expect(tabs).toHaveCount(0);

      // Verify artifact panel is hidden or empty
      const artifactPanel = page.locator('[data-testid="artifact-panel"]');
      await expect(artifactPanel).not.toBeVisible();
    });
  });

  test.describe('Pin and Split View', () => {
    const createArtifact = async (page: Page, query: string) => {
      await page.fill('textarea[placeholder*="Type your message"]', query);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    };

    test('should enable split view when artifact is pinned', async ({ page }) => {
      // Create 2 artifacts
      await createArtifact(page, 'Show me the dashboard');
      await createArtifact(page, 'Show task status');

      // Pin first artifact
      const pinButton = page.locator('[data-testid="artifact-tab"]').first().locator('[aria-label*="Pin"]');
      await pinButton.click();

      // Verify 3-panel layout (2 resize handles)
      const resizeHandles = page.locator('[data-panel-resize-handle-id]');
      await expect(resizeHandles).toHaveCount(2);

      // Verify both artifacts visible
      await expect(page.locator('text=/Dashboard/i')).toBeVisible();
      await expect(page.locator('text=/Task/i')).toBeVisible();
    });

    test('should keep pinned artifact visible when creating new artifact', async ({ page }) => {
      // Create artifact and pin it
      await createArtifact(page, 'Show me the dashboard');

      const pinButton = page.locator('[data-testid="artifact-tab"]').first().locator('[aria-label*="Pin"]');
      await pinButton.click();

      // Create new artifact
      await createArtifact(page, 'Show task status');

      // Verify both artifacts still visible (pinned + new)
      await expect(page.locator('text=/Dashboard/i')).toBeVisible();
      await expect(page.locator('text=/Task/i')).toBeVisible();
    });

    test('should unpin artifact when pin button clicked again', async ({ page }) => {
      // Create artifact and pin it
      await createArtifact(page, 'Show me the dashboard');

      const pinButton = page.locator('[data-testid="artifact-tab"]').first().locator('[aria-label*="Pin"]');
      await pinButton.click();

      // Verify split view (2 handles)
      let resizeHandles = page.locator('[data-panel-resize-handle-id]');
      await expect(resizeHandles).toHaveCount(2);

      // Unpin
      await pinButton.click();

      // Verify back to 2-panel layout (1 handle)
      resizeHandles = page.locator('[data-panel-resize-handle-id]');
      await expect(resizeHandles).toHaveCount(1);
    });
  });

  test.describe('Panel Resizing', () => {
    const createArtifact = async (page: Page, query: string) => {
      await page.fill('textarea[placeholder*="Type your message"]', query);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    };

    test('should resize panels when dragging resize handle', async ({ page }) => {
      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Get resize handle
      const resizeHandle = page.locator('[data-panel-resize-handle-id]').first();
      await expect(resizeHandle).toBeVisible();

      // Get initial panel sizes
      const chatPanel = page.locator('[data-panel-id="chat-panel"]');
      const artifactPanel = page.locator('[data-panel-id="artifact-panel"]');

      const initialChatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const initialArtifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      // Drag resize handle to the left (increase artifact panel size)
      const handleBox = await resizeHandle.boundingBox();
      if (handleBox) {
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 100, handleBox.y + handleBox.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
      }

      // Verify panel sizes changed
      const newChatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const newArtifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      expect(newChatWidth).toBeLessThan(initialChatWidth);
      expect(newArtifactWidth).toBeGreaterThan(initialArtifactWidth);
    });

    test('should snap panels to 50/50 when double-clicking resize handle', async ({ page }) => {
      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Get resize handle
      const resizeHandle = page.locator('[data-panel-resize-handle-id]').first();

      // Resize panels to non-50/50 ratio first
      const handleBox = await resizeHandle.boundingBox();
      if (handleBox) {
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 150, handleBox.y + handleBox.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
      }

      // Double-click resize handle
      await resizeHandle.dblclick();
      await page.waitForTimeout(500);

      // Get panel sizes
      const chatPanel = page.locator('[data-panel-id="chat-panel"]');
      const artifactPanel = page.locator('[data-panel-id="artifact-panel"]');

      const chatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const artifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      // Verify roughly equal (within 5% tolerance)
      const ratio = chatWidth / artifactWidth;
      expect(ratio).toBeGreaterThan(0.95);
      expect(ratio).toBeLessThan(1.05);
    });

    test('should resize smoothly without lag', async ({ page }) => {
      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Get resize handle
      const resizeHandle = page.locator('[data-panel-resize-handle-id]').first();

      // Perform multiple drag operations
      const handleBox = await resizeHandle.boundingBox();
      if (handleBox) {
        const startTime = Date.now();

        // Drag left
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 100, handleBox.y + handleBox.height / 2);
        await page.mouse.up();

        // Drag right
        await page.mouse.down();
        await page.mouse.move(handleBox.x + 100, handleBox.y + handleBox.height / 2);
        await page.mouse.up();

        const endTime = Date.now();
        const duration = endTime - startTime;

        // Verify operations complete quickly (< 2 seconds for smooth UX)
        expect(duration).toBeLessThan(2000);
      }
    });
  });

  test.describe('localStorage Persistence', () => {
    const createArtifact = async (page: Page, query: string) => {
      await page.fill('textarea[placeholder*="Type your message"]', query);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    };

    test('should persist panel sizes across page refresh', async ({ page }) => {
      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Resize panels
      const resizeHandle = page.locator('[data-panel-resize-handle-id]').first();
      const handleBox = await resizeHandle.boundingBox();

      if (handleBox) {
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 100, handleBox.y + handleBox.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
      }

      // Get panel sizes before refresh
      const chatPanel = page.locator('[data-panel-id="chat-panel"]');
      const artifactPanel = page.locator('[data-panel-id="artifact-panel"]');

      const beforeChatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const beforeArtifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      // Refresh page
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Recreate artifact (since chat history may not persist)
      await createArtifact(page, 'Show me the dashboard');

      // Get panel sizes after refresh
      const afterChatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const afterArtifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      // Verify sizes roughly match (within 5% tolerance)
      expect(Math.abs(afterChatWidth - beforeChatWidth) / beforeChatWidth).toBeLessThan(0.05);
      expect(Math.abs(afterArtifactWidth - beforeArtifactWidth) / beforeArtifactWidth).toBeLessThan(0.05);
    });
  });

  test.describe('Approval Buttons', () => {
    const createArtifact = async (page: Page, query: string) => {
      await page.fill('textarea[placeholder*="Type your message"]', query);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    };

    test('should log to console when Approve button clicked', async ({ page }) => {
      // Setup console listener
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'log') {
          consoleLogs.push(msg.text());
        }
      });

      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Click Approve button
      const approveButton = page.locator('button:has-text("Approve"), button[aria-label*="Approve"]');
      await approveButton.first().click();

      // Verify console log
      expect(consoleLogs.some(log => log.includes('Approve'))).toBeTruthy();
    });

    test('should log to console when Edit button clicked', async ({ page }) => {
      // Setup console listener
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'log') {
          consoleLogs.push(msg.text());
        }
      });

      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Click Edit button
      const editButton = page.locator('button:has-text("Edit"), button[aria-label*="Edit"]');
      await editButton.first().click();

      // Verify console log
      expect(consoleLogs.some(log => log.includes('Edit'))).toBeTruthy();
    });

    test('should log to console when Comment button clicked', async ({ page }) => {
      // Setup console listener
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'log') {
          consoleLogs.push(msg.text());
        }
      });

      // Create artifact
      await createArtifact(page, 'Show me the dashboard');

      // Click Comment button
      const commentButton = page.locator('button:has-text("Comment"), button[aria-label*="Comment"]');
      await commentButton.first().click();

      // Verify console log
      expect(consoleLogs.some(log => log.includes('Comment'))).toBeTruthy();
    });
  });

  test.describe('Complete User Journey', () => {
    test('should handle full workflow from empty to complex multi-artifact state', async ({ page }) => {
      // STEP 1: Verify empty state
      await expect(page.locator('[data-testid="artifact-panel"]')).not.toBeVisible();

      // STEP 2: Create 5 different artifact types
      const artifactQueries = [
        'Show me the dashboard',
        'Show engagement plan',
        'Show task status',
        'Show financial statements',
        'Show issue details'
      ];

      for (const query of artifactQueries) {
        await page.fill('textarea[placeholder*="Type your message"]', query);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(2500); // Wait for artifact creation
      }

      // Verify 5 tabs exist
      const tabs = page.locator('[data-testid="artifact-tab"]');
      await expect(tabs).toHaveCount(5);

      // STEP 3: Pin one artifact (first one)
      const pinButton = tabs.first().locator('[aria-label*="Pin"]');
      await pinButton.click();

      // Verify split view (2 resize handles for 3 panels)
      const resizeHandles = page.locator('[data-panel-resize-handle-id]');
      await expect(resizeHandles).toHaveCount(2);

      // STEP 4: Resize panels
      const resizeHandle = resizeHandles.first();
      const handleBox = await resizeHandle.boundingBox();

      if (handleBox) {
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 80, handleBox.y + handleBox.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
      }

      // STEP 5: Approve one artifact (second tab)
      await tabs.nth(1).click(); // Switch to second tab
      await page.waitForTimeout(500);

      // Setup console listener
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'log') {
          consoleLogs.push(msg.text());
        }
      });

      const approveButton = page.locator('button:has-text("Approve"), button[aria-label*="Approve"]');
      await approveButton.first().click();

      // Verify approval logged
      expect(consoleLogs.some(log => log.includes('Approve'))).toBeTruthy();

      // STEP 6: Close some tabs (close 2 tabs)
      for (let i = 0; i < 2; i++) {
        const closeButton = tabs.first().locator('[aria-label*="Close"]');
        await closeButton.click();
        await page.waitForTimeout(500);
      }

      // Verify 3 tabs remain
      await expect(tabs).toHaveCount(3);

      // STEP 7: Refresh page
      await page.reload();
      await page.waitForLoadState('networkidle');

      // STEP 8: Verify state persisted (panel sizes)
      // Note: Tab state may not persist depending on implementation
      // But panel size ratios should persist via localStorage

      // Recreate one artifact to verify panel persistence
      await page.fill('textarea[placeholder*="Type your message"]', 'Show me the dashboard');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      // Verify panel resizing was persisted (panels should not be at default 50/50)
      const chatPanel = page.locator('[data-panel-id="chat-panel"]');
      const artifactPanel = page.locator('[data-panel-id="artifact-panel"]');

      const chatWidth = await chatPanel.boundingBox().then(box => box?.width ?? 0);
      const artifactWidth = await artifactPanel.boundingBox().then(box => box?.width ?? 0);

      // Verify panels are NOT at 50/50 (should be resized from step 4)
      const ratio = chatWidth / artifactWidth;

      // Allow some tolerance, but verify it's not default 50/50
      const isNot5050 = ratio < 0.9 || ratio > 1.1;
      expect(isNot5050).toBeTruthy();
    });

    test('should handle rapid artifact creation without errors', async ({ page }) => {
      // Create 10 artifacts rapidly (stress test)
      const queries = [
        'Show me the dashboard',
        'Show engagement plan',
        'Show task status',
        'Show financial statements',
        'Show issue details',
        'Show me the dashboard',
        'Show engagement plan',
        'Show task status',
        'Show financial statements',
        'Show issue details'
      ];

      for (const query of queries) {
        await page.fill('textarea[placeholder*="Type your message"]', query);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(1000); // Shorter wait for stress test
      }

      // Verify no errors in console
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.waitForTimeout(5000); // Wait for all artifacts to settle

      // Verify no errors occurred
      expect(errors.length).toBe(0);

      // Verify all tabs created
      const tabs = page.locator('[data-testid="artifact-tab"]');
      await expect(tabs.count()).resolves.toBeGreaterThan(0);
    });

    test('should handle complex interactions without state corruption', async ({ page }) => {
      // Complex sequence: create, pin, resize, close, create, unpin, resize

      // Create 3 artifacts
      await page.fill('textarea[placeholder*="Type your message"]', 'Show me the dashboard');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      await page.fill('textarea[placeholder*="Type your message"]', 'Show task status');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      await page.fill('textarea[placeholder*="Type your message"]', 'Show engagement plan');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      // Pin first
      const tabs = page.locator('[data-testid="artifact-tab"]');
      await tabs.first().locator('[aria-label*="Pin"]').click();
      await page.waitForTimeout(500);

      // Resize
      const resizeHandle = page.locator('[data-panel-resize-handle-id]').first();
      const handleBox = await resizeHandle.boundingBox();
      if (handleBox) {
        await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox.x - 50, handleBox.y + handleBox.height / 2);
        await page.mouse.up();
      }
      await page.waitForTimeout(500);

      // Close second tab
      await tabs.nth(1).locator('[aria-label*="Close"]').click();
      await page.waitForTimeout(500);

      // Create new artifact
      await page.fill('textarea[placeholder*="Type your message"]', 'Show financial statements');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      // Unpin
      await tabs.first().locator('[aria-label*="Pin"]').click();
      await page.waitForTimeout(500);

      // Resize again
      const newHandleBox = await resizeHandle.boundingBox();
      if (newHandleBox) {
        await page.mouse.move(newHandleBox.x + newHandleBox.width / 2, newHandleBox.y + newHandleBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(newHandleBox.x + 50, newHandleBox.y + newHandleBox.height / 2);
        await page.mouse.up();
      }

      // Verify no errors and state is consistent
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.waitForTimeout(2000);

      expect(errors.length).toBe(0);

      // Verify final state has 3 tabs (created 4, closed 1)
      await expect(tabs).toHaveCount(3);
    });
  });
});
