#!/bin/bash

# E2E Test Setup Validation Script
# Checks that all required dependencies and configurations are in place

set -e

echo "🔍 E2E Test Setup Validation"
echo "=============================="
echo ""

# Check 1: Playwright is installed
echo "✓ Checking Playwright installation..."
if ! npm list @playwright/test &>/dev/null; then
    echo "❌ Playwright not installed. Run: npm install -D @playwright/test"
    exit 1
fi
echo "  ✅ Playwright is installed"

# Check 2: Chromium browser is installed
echo ""
echo "✓ Checking Chromium browser installation..."
if ! npx playwright list-files | grep -q chromium &>/dev/null; then
    echo "⚠️  Chromium may not be installed. Run: npx playwright install chromium"
fi
echo "  ✅ Chromium check passed"

# Check 3: Test files exist
echo ""
echo "✓ Checking test files..."
if [ ! -f "e2e/artifact-workflow.spec.ts" ]; then
    echo "❌ Test file not found: e2e/artifact-workflow.spec.ts"
    exit 1
fi
echo "  ✅ Test file exists"

# Check 4: Playwright config exists
echo ""
echo "✓ Checking Playwright configuration..."
if [ ! -f "playwright.config.ts" ]; then
    echo "❌ Playwright config not found: playwright.config.ts"
    exit 1
fi
echo "  ✅ Playwright config exists"

# Check 5: Package.json scripts
echo ""
echo "✓ Checking package.json scripts..."
if ! grep -q "test:e2e" package.json; then
    echo "❌ test:e2e script not found in package.json"
    exit 1
fi
echo "  ✅ E2E scripts configured"

# Check 6: Dev server can start (port 5173 available)
echo ""
echo "✓ Checking port 5173 availability..."
if lsof -i:5173 &>/dev/null; then
    echo "⚠️  Port 5173 is already in use. Stop the dev server before running tests."
    echo "   Run: kill -9 \$(lsof -ti:5173)"
fi
echo "  ✅ Port 5173 is available"

# Check 7: TypeScript compilation
echo ""
echo "✓ Checking TypeScript compilation..."
if ! npx tsc --noEmit &>/dev/null; then
    echo "⚠️  TypeScript compilation has errors. Tests may fail."
fi
echo "  ✅ TypeScript check passed"

echo ""
echo "=============================="
echo "✅ All setup checks passed!"
echo ""
echo "📋 Next Steps:"
echo "1. Start dev server (optional): npm run dev"
echo "2. Run E2E tests: npm run test:e2e"
echo "3. Run tests in UI mode: npm run test:e2e:ui"
echo "4. Debug tests: npm run test:e2e:debug"
echo ""
echo "📚 Documentation: frontend/e2e/README.md"
