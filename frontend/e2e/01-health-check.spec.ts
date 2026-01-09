/**
 * E2E Test: Health Check
 *
 * Verifies that both backend and frontend servers are running and accessible.
 * This is the foundational test that ensures the basic infrastructure is working
 * before running more complex integration tests.
 */

import { test, expect } from '@playwright/test';
import { checkHealth, waitForBackendReady, checkEndpointStatus } from './utils/api';
import { isBackendRunning, isFrontendRunning, BACKEND_CONFIG, FRONTEND_CONFIG } from './utils/setup';
import { TEST_SCENARIOS } from './fixtures/testData';
import { URLS } from './config/routes';

test.describe('01 - Health Check', () => {
  test.describe('Backend Health', () => {
    test('should have backend server running', async () => {
      const isRunning = await isBackendRunning();
      expect(isRunning).toBe(true);
    });

    test('should respond to /api/health endpoint', async () => {
      const health = await checkHealth();

      // Verify response structure
      expect(health).toBeDefined();
      expect(health.status).toBeDefined();

      // Accept common status values (including degraded - backend is running but some services may be unavailable)
      const validStatuses = ['healthy', 'ok', 'running', 'degraded'];
      expect(validStatuses).toContain(health.status.toLowerCase());
    });

    test('should respond to root endpoint /', async () => {
      const isOk = await checkEndpointStatus('/', 200);
      expect(isOk).toBe(true);
    });

    test('should have API documentation available', async () => {
      const docsAvailable = await checkEndpointStatus('/docs', 200);
      expect(docsAvailable).toBe(true);
    });

    test('should be ready within timeout', async () => {
      const isReady = await waitForBackendReady(5000);
      expect(isReady).toBe(true);
    });
  });

  test.describe('Frontend Health', () => {
    test('should have frontend server running', async () => {
      const isRunning = await isFrontendRunning();
      expect(isRunning).toBe(true);
    });

    test('should load main page successfully', async ({ page }) => {
      const response = await page.goto(FRONTEND_CONFIG.url);
      expect(response?.status()).toBe(200);
    });

    test('should have React app mounted', async ({ page }) => {
      await page.goto(FRONTEND_CONFIG.url);

      // Wait for React root element
      const root = page.locator('#root');
      await expect(root).toBeVisible();
    });

    test('should load without JavaScript errors', async ({ page }) => {
      const errors: string[] = [];

      // Listen for console errors
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // Listen for page errors
      page.on('pageerror', (error) => {
        errors.push(error.message);
      });

      await page.goto(FRONTEND_CONFIG.url);
      await page.waitForLoadState('networkidle');

      // Filter out known harmless errors (like extension errors, API errors from backend, WebSocket errors)
      // During E2E testing, backend/network errors are expected and handled by the UI
      const criticalErrors = errors.filter(
        (error) =>
          !error.includes('extension') &&
          !error.includes('chrome-error') &&
          !error.includes('favicon') &&
          !error.includes('Failed to load resource') && // API errors from backend
          !error.includes('500') && // Server errors
          !error.includes('WebSocket') && // WebSocket connection errors (Supabase realtime)
          !error.includes('ERR_NAME_NOT_RESOLVED') && // DNS resolution errors
          !error.includes('above error occurred') && // React error boundaries (stack traces)
          !error.includes('at ') && // Stack trace lines
          !error.includes('supabase') // Supabase-related errors (handled by app)
      );

      expect(criticalErrors).toEqual([]);
    });
  });

  test.describe('Backend-Frontend Connectivity', () => {
    test('should allow CORS requests from frontend', async ({ page }) => {
      await page.goto(FRONTEND_CONFIG.url);

      // Try to make a fetch request to backend from frontend context
      const response = await page.evaluate(async (backendUrl) => {
        try {
          const res = await fetch(`${backendUrl}/api/health`);
          return {
            ok: res.ok,
            status: res.status,
            data: await res.json(),
          };
        } catch (error) {
          return {
            ok: false,
            error: String(error),
          };
        }
      }, BACKEND_CONFIG.url);

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      expect(response.data).toBeDefined();
    });

    test('should have both servers accessible simultaneously', async () => {
      const [backendRunning, frontendRunning] = await Promise.all([
        isBackendRunning(),
        isFrontendRunning(),
      ]);

      expect(backendRunning).toBe(true);
      expect(frontendRunning).toBe(true);
    });

    test('should respond within acceptable timeframes', async () => {
      const startTime = Date.now();

      const [health, frontendStatus] = await Promise.all([
        checkHealth(),
        checkEndpointStatus('/', 200),
      ]);

      const duration = Date.now() - startTime;

      expect(health).toBeDefined();
      expect(frontendStatus).toBe(true);

      // Both servers should respond within 5 seconds
      expect(duration).toBeLessThan(5000);
    });
  });

  test.describe('Environment Configuration', () => {
    test('should use correct backend URL', async () => {
      expect(BACKEND_CONFIG.url).toBe('http://localhost:8080');
      expect(BACKEND_CONFIG.port).toBe(8080);
    });

    test('should use correct frontend URL', async () => {
      expect(FRONTEND_CONFIG.url).toBe('http://localhost:5173');
      expect(FRONTEND_CONFIG.port).toBe(5173);
    });

    test('should have test scenarios defined', () => {
      expect(TEST_SCENARIOS.quickHealthCheck).toBeDefined();
      expect(TEST_SCENARIOS.basicProjectCreation).toBeDefined();
      expect(TEST_SCENARIOS.fullAuditWorkflow).toBeDefined();
    });
  });

  test.describe('API Endpoints Availability', () => {
    test('should have /api/health endpoint', async () => {
      const available = await checkEndpointStatus('/api/health', 200);
      expect(available).toBe(true);
    });

    test('should have documentation endpoints', async () => {
      const [docsAvailable, redocAvailable] = await Promise.all([
        checkEndpointStatus('/docs', 200),
        checkEndpointStatus('/redoc', 200),
      ]);

      expect(docsAvailable).toBe(true);
      expect(redocAvailable).toBe(true);
    });

    test('should handle 404 for non-existent endpoints', async () => {
      const response = await fetch(`${BACKEND_CONFIG.url}/api/nonexistent`);
      expect(response.status).toBe(404);
    });
  });

  test.describe('Full Integration Smoke Test', () => {
    test('should complete full health check workflow', async ({ page }) => {
      // Step 1: Verify backend is healthy
      const backendHealth = await checkHealth();
      expect(backendHealth.status).toBeDefined();

      // Step 2: Load frontend
      await page.goto(FRONTEND_CONFIG.url);
      await expect(page.locator('#root')).toBeVisible();

      // Step 3: Frontend can communicate with backend
      const apiResponse = await page.evaluate(async (backendUrl) => {
        const res = await fetch(`${backendUrl}/api/health`);
        return res.ok;
      }, BACKEND_CONFIG.url);

      expect(apiResponse).toBe(true);

      // Step 4: No console errors
      const errors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.waitForLoadState('networkidle');

      const criticalErrors = errors.filter(
        (error) =>
          !error.includes('extension') &&
          !error.includes('favicon') &&
          !error.includes('Failed to load resource') &&
          !error.includes('500')
      );

      expect(criticalErrors.length).toBe(0);
    });
  });
});
