import { defineConfig, devices } from '@playwright/test';

// Use environment variables for flexibility when ports are already in use
const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const BACKEND_PORT = process.env.BACKEND_PORT || '8080';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: process.env.FRONTEND_URL || `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',

    // Extended timeout for backend interactions
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  // Global timeout per test
  timeout: 60000,

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Start both backend and frontend servers automatically
  webServer: [
    {
      command: `cd ../backend && source venv/bin/activate && uvicorn src.main:app --port ${BACKEND_PORT}`,
      url: `http://localhost:${BACKEND_PORT}/api/health`,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: `http://localhost:${FRONTEND_PORT}`,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
