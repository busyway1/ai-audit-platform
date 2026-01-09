# Full Integration E2E Tests - Quick Start Guide

**File**: `08-full-integration.spec.ts`
**Duration**: ~15-20 minutes
**Status**: ✅ Ready to Execute

---

## 🚀 Quick Start

### 1. Prerequisites Check

```bash
# Check backend Python venv exists
ls backend/venv/bin/activate

# Check frontend node_modules
ls frontend/node_modules

# Check Playwright installed
npx playwright --version

# Check ports are free
lsof -ti:8080  # Should be empty (backend port)
lsof -ti:5173  # Should be empty (frontend port)
```

### 2. Environment Setup

**Backend `.env`**:
```bash
cd backend
cat .env  # Verify these exist:
# SUPABASE_URL=...
# SUPABASE_ANON_KEY=...
# DATABASE_URL=postgresql://...
```

**Frontend `.env`**:
```bash
cd frontend
cat .env  # Verify these exist:
# VITE_SUPABASE_URL=...
# VITE_SUPABASE_ANON_KEY=...
```

### 3. Run Tests

```bash
# From project root
cd frontend

# Run all 4 integration tests
npm run test:e2e e2e/08-full-integration.spec.ts

# Run in headed mode (watch tests execute)
npm run test:e2e e2e/08-full-integration.spec.ts --headed

# Run specific test only
npm run test:e2e e2e/08-full-integration.spec.ts -g "Project Creation"
```

---

## 📋 Test Scenarios

### Test 1: Project Creation (5-7 min)
```
✓ Navigate to frontend
✓ Send project creation message
✓ Wait for Partner agent response
✓ Verify audit plan created
✓ Check approval button appears
```

### Test 2: Approval Workflow (3-5 min)
```
✓ Click approve button
✓ Manager spawns Staff agents
✓ Verify SSE streaming works
✓ Check task status updates
✓ Monitor agent messages
```

### Test 3: Real-time Sync (2-3 min)
```
✓ Open 2 browser tabs
✓ Create project in Tab 1
✓ Verify Tab 2 updates (no refresh!)
✓ Approve in Tab 1
✓ Check Tab 2 syncs
```

### Test 4: Workpaper Download (1-2 min)
```
✓ Wait for workflow completion
✓ Find download button
✓ Click download
✓ Verify file downloaded
```

---

## 🎯 Expected Output

### Success Output

```
🚀 Starting test suite: Full Integration E2E
📋 Setting up servers...
⏳ Waiting for Backend to become healthy at http://localhost:8080...
✅ Backend is healthy (attempt 5/30)
⏳ Waiting for Frontend to become healthy at http://localhost:5173...
✅ Frontend is healthy (attempt 3/30)
✅ All servers healthy and ready for testing

🧪 TEST 1: Project Creation Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Step 1.1: Navigating to frontend...
✅ Frontend loaded successfully
📍 Step 1.2: Creating new audit project...
✅ Project creation message sent
📍 Step 1.3: Waiting for Partner agent response...
✅ Partner agent created audit plan
📍 Step 1.4: Verifying audit plan content...
✅ Audit plan contains key areas
📍 Step 1.5: Verifying approval UI...
✅ Approval button visible
✅ TEST 1 PASSED (Duration: 6234ms)

[... similar output for Tests 2, 3, 4 ...]

🛑 Cleaning up servers...
✅ Backend stopped
✅ Frontend stopped
✅ All servers stopped

  4 passed (18m)
```

---

## 🐛 Troubleshooting

### Issue: Backend health check fails

```bash
# Check if venv exists
ls backend/venv/bin/activate

# Activate venv manually
cd backend
source venv/bin/activate

# Test server manually
uvicorn src.main:app --reload

# Check logs
tail -f backend/backend.log
```

### Issue: Frontend health check fails

```bash
# Check if node_modules exists
ls frontend/node_modules

# Install dependencies
cd frontend
npm install

# Test server manually
npm run dev

# Check if port is in use
lsof -ti:5173
```

### Issue: Tests timeout

```bash
# Increase timeout in playwright.config.ts
timeout: 60000,  // 1 minute per test
```

### Issue: SSE not working

```bash
# Check backend logs for SSE endpoint
grep "SSE" backend/backend.log

# Verify EventSource in browser console
# Open DevTools → Console → Look for EventSource connection
```

### Issue: Realtime sync fails

```bash
# Check Supabase credentials
cd frontend && cat .env | grep SUPABASE

# Verify Realtime enabled in Supabase dashboard
# → Settings → API → Realtime → Enabled

# Check browser console for subscription errors
```

---

## 📸 Screenshots

All screenshots saved to: `frontend/e2e/screenshots/`

**Naming pattern**: `full-integration-{test}-{step}-{timestamp}.png`

**Example**:
```
full-integration-test1-step1-frontend-loaded-2026-01-07T15-30-00.png
full-integration-test2-step3-manager-response-2026-01-07T15-35-00.png
full-integration-test3-step2-tab1-project-created-2026-01-07T15-40-00.png
```

---

## ⏱️ Timing Benchmarks

| Metric | Target | Typical | Max |
|--------|--------|---------|-----|
| Server startup | <1 min | 30 sec | 1 min |
| Test 1 (Creation) | 5-7 min | 6 min | 7 min |
| Test 2 (Approval) | 3-5 min | 4 min | 5 min |
| Test 3 (Realtime) | 2-3 min | 2.5 min | 3 min |
| Test 4 (Download) | 1-2 min | 1.5 min | 2 min |
| **Total** | **12-18 min** | **15 min** | **20 min** |

---

## 🎓 Key Concepts

### Server Lifecycle

```typescript
test.beforeAll(async () => {
  await startBackend();   // Starts FastAPI + LangGraph
  await startFrontend();  // Starts Vite dev server
});

test.afterAll(async () => {
  await stopServers();    // Graceful cleanup
});
```

### Health Checks

```typescript
// Backend: GET http://localhost:8080/api/health
// Frontend: GET http://localhost:5173/

// 30 retries, 1 second apart
// Total timeout: 30 seconds
```

### SSE Monitoring

```typescript
// Intercept EventSource to capture SSE events
await monitorSSEEvents(page);

// Retrieve captured events
const events = await getSSEMessages(page);
```

### Dual-Tab Testing

```typescript
const tab1 = await context.newPage();
const tab2 = await context.newPage();

// Update in tab1
await sendChatMessage(tab1, "...");

// Verify tab2 updates via Supabase Realtime
await waitForArtifactPanel(tab2);
```

---

## ✅ Success Checklist

Before running tests:
- [ ] Backend venv exists
- [ ] Frontend node_modules exist
- [ ] Playwright browsers installed
- [ ] Backend .env configured
- [ ] Frontend .env configured
- [ ] Supabase project created
- [ ] Supabase Realtime enabled
- [ ] Ports 8000 and 5173 are free

After tests complete:
- [ ] All 4 tests passed
- [ ] 20+ screenshots captured
- [ ] No critical console errors
- [ ] Servers cleaned up properly
- [ ] Total duration <20 minutes

---

## 📚 Related Files

- **Test File**: `frontend/e2e/08-full-integration.spec.ts`
- **Server Manager**: `frontend/e2e/utils/server-manager.ts`
- **Helpers**: `frontend/e2e/helpers.ts`
- **Execution Report**: `frontend/e2e/FULL_INTEGRATION_E2E_REPORT.md`
- **Backend Routes**: `backend/src/api/routes.py`
- **LangGraph**: `backend/src/graph/graph.py`

---

## 🚦 Run Commands

```bash
# Standard execution
npm run test:e2e e2e/08-full-integration.spec.ts

# Headed mode (watch tests)
npm run test:e2e e2e/08-full-integration.spec.ts --headed

# Debug mode
DEBUG=pw:api npm run test:e2e e2e/08-full-integration.spec.ts

# Single test
npm run test:e2e e2e/08-full-integration.spec.ts -g "Project Creation"

# Update snapshots (if using visual regression)
npm run test:e2e e2e/08-full-integration.spec.ts --update-snapshots

# Generate HTML report
npm run test:e2e e2e/08-full-integration.spec.ts --reporter=html
```

---

**Created**: 2026-01-07
**Status**: ✅ Ready for Execution
**Next Steps**: Run tests and verify all workflows pass
