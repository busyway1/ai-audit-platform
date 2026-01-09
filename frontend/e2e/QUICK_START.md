# E2E Workflow Test - Quick Start Guide

## Prerequisites

### 1. Start Backend Server

```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start server
python -m src.main
```

**Verify backend is running**:
```bash
curl http://localhost:8080/api/health
# Expected: {"status": "healthy", ...}
```

### 2. Start Frontend Server

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Start dev server
npm run dev
```

**Verify frontend is running**:
- Open browser to http://localhost:5173
- Should see AI Audit Platform interface

### 3. Install Playwright (if not already done)

```bash
cd frontend

# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

## Running the Complete Workflow Test

### Quick Run (All Tests)

```bash
cd frontend
npx playwright test e2e/06-complete-workflow.spec.ts
```

### Run with UI Mode (Recommended)

```bash
npx playwright test e2e/06-complete-workflow.spec.ts --ui
```

### View Results

```bash
npx playwright show-report
```

## Troubleshooting

See `06-complete-workflow-README.md` for detailed troubleshooting guide.
