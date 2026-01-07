import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
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
      command: 'cd ../backend && source venv/bin/activate && uvicorn src.main:app --port 8000',
      url: 'http://localhost:8000/api/health',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
