# E2E Test Quick Reference Guide

**Quick commands for running and managing Playwright E2E tests**

---

## Essential Commands

### Run All Tests
```bash
npm run test:e2e
```
Runs all 91 tests in parallel with HTML reporting.

### Run Specific Test File
```bash
npm run test:e2e -- 01-health-check.spec.ts
npm run test:e2e -- artifact-workflow.spec.ts
```

### Run Tests Matching Pattern
```bash
npm run test:e2e -- -g "Health Check"
npm run test:e2e -- -g "realtime"
```

### Run Interactive UI Mode
```bash
npm run test:e2e:ui
```
Opens Playwright Test UI for interactive debugging and test selection.

### Run Single Test in Debug Mode
```bash
npm run test:e2e:debug
```
Launches with debugger - step through tests line by line.

### View HTML Report
```bash
npm run test:e2e:report
```
Opens latest HTML test report in default browser.

---

## Advanced Options

### Run Tests in a Specific Browser
```bash
npm run test:e2e -- --project=chromium
```

### Run with Headed Browser (see the browser)
```bash
npm run test:e2e -- --headed
```

### Run Single Test
```bash
npm run test:e2e -- 01-health-check.spec.ts:19
# or
npm run test:e2e -- --grep "should have backend server running"
```

### Disable Parallel Execution (run sequentially)
```bash
npm run test:e2e -- --workers=1
```

### Keep Browser Open on Failure
```bash
npm run test:e2e -- --headed --no-close-on-failure
```

### Update Test Snapshots
```bash
npm run test:e2e -- --update-snapshots
```

### Trace Only Failed Tests
```bash
npm run test:e2e -- --trace on
```

---

## Pre-Test Setup

### Check Backend Health
```bash
curl http://localhost:8000/api/health
```

### Start Backend (if not running)
```bash
cd backend
source venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m src.main
```

### Start Frontend Dev Server (manual)
```bash
# Playwright auto-starts this, but manual start:
npm run dev
```

### Check Both Servers Running
```bash
curl http://localhost:8000/api/health && curl http://localhost:5173
echo "Both servers healthy"
```

---

## Test Categories

### Health Check Tests (19 tests)
```bash
npm run test:e2e -- 01-health-check.spec.ts
```
Verifies backend/frontend connectivity, CORS, configuration.

### Project Creation Tests (5 tests)
```bash
npm run test:e2e -- 02-project-creation.spec.ts
```
Tests audit project creation and validation.

### Task Approval Tests (6 tests)
```bash
npm run test:e2e -- 03-task-approval.spec.ts
```
Tests task approval workflow and status changes.

### Realtime Sync Tests (7 tests)
```bash
npm run test:e2e -- 04-realtime-sync.spec.ts
```
Tests Supabase Realtime multi-tab synchronization.

### SSE Streaming Tests (8 tests)
```bash
npm run test:e2e -- 05-sse-streaming.spec.ts
```
Tests Server-Sent Events for agent message streaming.

### Complete Workflow Tests (11 tests)
```bash
npm run test:e2e -- 06-complete-workflow.spec.ts
```
Tests full end-to-end workflows.

### Supabase Realtime Tests (24 tests)
```bash
npm run test:e2e -- 07-supabase-realtime.spec.ts
```
Comprehensive Supabase Realtime testing.

### Artifact Workflow Tests (11 tests)
```bash
npm run test:e2e -- artifact-workflow.spec.ts
```
Tests artifact creation, tabs, resizing, persistence.

---

## Debugging Tips

### Show Browser During Test
```bash
npm run test:e2e -- --headed 01-health-check.spec.ts:19
```

### Slow Down Test Execution
```bash
npm run test:e2e -- --headed --headed 01-health-check.spec.ts --slow-mo=1000
# or in test file:
page.setDefaultTimeout(30000);
```

### Check Test Output
Tests automatically take:
- Screenshots on failure: `e2e/screenshots/`
- Traces on first retry: in report artifacts
- Full HTML report: `playwright-report/`

### View Console Logs in Test
```typescript
// In your test file:
page.on('console', msg => console.log(msg.text()));
```

### Check Network Requests
```typescript
// In test file:
page.on('response', response =>
  console.log(response.url(), response.status())
);
```

---

## Common Issues & Solutions

### Problem: "Port 5173 already in use"
```bash
# Find and kill the process
lsof -i :5173
kill -9 <PID>

# Or use different port in playwright.config.ts
```

### Problem: "Cannot find tests"
```bash
# Ensure tests are in e2e/ directory
ls frontend/e2e/*.spec.ts

# List all tests
npm run test:e2e -- --list
```

### Problem: "Backend connection refused"
```bash
# Start backend:
cd backend && source venv/bin/activate && python -m src.main

# Verify:
curl http://localhost:8000/api/health
```

### Problem: "Tests timeout frequently"
```bash
# Increase timeouts in playwright.config.ts:
timeout: 120000,  // 2 minutes
actionTimeout: 60000,  // 1 minute
```

### Problem: "Screenshot/Trace directories missing"
```bash
# Create directories
mkdir -p frontend/e2e/screenshots
mkdir -p frontend/playwright-report
```

---

## Test Configuration

### Key Settings in `playwright.config.ts`

| Setting | Value | Purpose |
|---------|-------|---------|
| testDir | ./e2e | Where test files are located |
| fullyParallel | true | Run tests in parallel |
| baseURL | http://localhost:5173 | Frontend URL |
| timeout | 60000 | Max time per test (60s) |
| actionTimeout | 30000 | Max time per action (30s) |
| reporter | html | Generate HTML report |
| screenshot | only-on-failure | Only capture on failure |
| trace | on-first-retry | Record trace on retry |
| webServer | npm run dev | Auto-start frontend |

### Modify Config
Edit `frontend/playwright.config.ts` to:
- Change timeout values
- Add/remove browsers
- Adjust parallel workers
- Change base URL
- Update reporter settings

---

## Writing New Tests

### Basic Test Template
```typescript
import { test, expect } from '@playwright/test';

test('should describe what it does', async ({ page }) => {
  await page.goto('/');

  // Interact with page
  await page.click('button');

  // Assert expected behavior
  await expect(page.locator('text=Success')).toBeVisible();
});
```

### Using Page Objects
```typescript
import { DashboardPage } from '../pages/DashboardPage';

test('should create project', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();
  await dashboard.startNewProject('Test Co', 2024, 100000);
  await dashboard.waitForProjectCreation();
});
```

### Using Fixtures
```typescript
import { mockClientInfo, mockAuditProject } from '../fixtures/mock-audit-data';

test('should use mock data', async ({ page }) => {
  const clientName = mockClientInfo.clientName;
  // Use mock data in test
});
```

### Using Helpers
```typescript
import { sendChatMessage, waitForChatMessage } from '../helpers';

test('should send message', async ({ page }) => {
  await sendChatMessage(page, 'Hello');
  await waitForChatMessage(page, 'Response');
});
```

---

## Performance & Optimization

### Run Only Failing Tests
```bash
# After a test run fails:
npm run test:e2e -- --last-failed
```

### Run in Sequence (Slower but Less Flaky)
```bash
npm run test:e2e -- --workers=1
```

### Skip Slow Tests
Add `@skip` tag to test:
```typescript
test.skip('slow test', async ({ page }) => {
  // This test is skipped
});
```

### Focus on Specific Tests
```typescript
test.only('important test', async ({ page }) => {
  // Only this test runs
});
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Tests
  run: |
    npm ci
    npm run test:e2e
```

### In CI Environment
Tests automatically:
- Run in single-worker mode (CI=true)
- Retry failed tests 2 times
- Generate HTML report
- Upload screenshots on failure

### Check CI Status
```bash
# Locally simulate CI environment
CI=true npm run test:e2e
```

---

## Useful Files

| File | Purpose |
|------|---------|
| `playwright.config.ts` | Main configuration |
| `tsconfig.e2e.json` | TypeScript config for tests |
| `e2e/helpers.ts` | General test helpers |
| `e2e/realtime-helpers.ts` | Realtime/SSE helpers |
| `e2e/pages/DashboardPage.ts` | Dashboard page object |
| `e2e/pages/TaskDetailPage.ts` | Task detail page object |
| `e2e/fixtures/mock-audit-data.ts` | Mock audit data |
| `e2e/fixtures/testData.ts` | General test data |
| `e2e/utils/setup.ts` | Server setup utilities |
| `e2e/utils/api.ts` | API client helper |
| `playwright-report/` | HTML test report |
| `e2e/screenshots/` | Failed test screenshots |

---

## Next Steps

1. **Run Health Check**: `npm run test:e2e -- 01-health-check.spec.ts`
2. **Review Report**: `npm run test:e2e:report`
3. **Run All Tests**: `npm run test:e2e`
4. **Debug Failures**: `npm run test:e2e:debug`
5. **Add New Tests**: Follow test template above

---

## Support

For issues or questions:
1. Check test output in `playwright-report/`
2. Review test file documentation
3. Check helper function comments
4. Consult `TEST_STRUCTURE.md` for architecture
5. Review `TEST_COVERAGE.md` for test details
