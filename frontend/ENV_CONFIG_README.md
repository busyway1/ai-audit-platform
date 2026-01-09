# Environment Variable Configuration

This document explains how environment variables are used for API configuration across different deployment environments.

## 📁 Files

### Environment Files

| File | Purpose | Git Tracked? |
|------|---------|--------------|
| `.env.example` | Template with all variables | ✅ Yes (committed) |
| `.env.development` | Development configuration | ✅ Yes (committed) |
| `.env.production.example` | Production template | ✅ Yes (committed) |
| `.env.production` | **Actual production config** | ❌ No (gitignored) |
| `.env` | Local overrides (optional) | ❌ No (gitignored) |

### Code Files

| File | Purpose |
|------|---------|
| `src/config/api.ts` | API configuration utility |
| `src/vite-env.d.ts` | TypeScript environment types |

---

## 🚀 Quick Start

### 1. Development Setup (First Time)

```bash
# Copy example file (optional - .env.development is auto-loaded)
cp .env.example .env

# Install dependencies
npm install

# Start development server (uses .env.development automatically)
npm run dev
```

The development server will automatically use:
- `VITE_API_URL=http://localhost:8080` (from `.env.development`)
- `VITE_API_TIMEOUT=30000` (from `.env.development`)

### 2. Production Setup

```bash
# Create production environment file
cp .env.production.example .env.production

# Edit with your production values
nano .env.production

# Build for production
npm run build

# Preview production build locally
npm run preview
```

---

## 🔧 Environment Variables

### Required Variables

| Variable | Description | Development | Production |
|----------|-------------|-------------|------------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8080` | `https://api.your-domain.com` |
| `VITE_API_TIMEOUT` | Request timeout (ms) | `30000` | `30000` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_SUPABASE_URL` | Supabase project URL | *(none)* |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key | *(none)* |
| `VITE_FRONTEND_URL` | Frontend URL (E2E tests) | `http://localhost:5173` |
| `VITE_DEBUG` | Enable debug mode | `false` |

---

## 💻 Usage in Code

### Import the Configuration

```typescript
import { getApiUrl, API_CONFIG, API_ENDPOINTS } from '@/config/api';
```

### Construct API URLs

```typescript
// Method 1: Use getApiUrl() helper
const url = getApiUrl('/api/projects/start');
// Returns: 'http://localhost:8080/api/projects/start' (dev)
// Returns: 'https://api.your-domain.com/api/projects/start' (prod)

// Method 2: Use predefined endpoints
import { API_ENDPOINTS } from '@/config/api';
const url = getApiUrl(API_ENDPOINTS.health);
// Returns: 'http://localhost:8080/api/health'
```

### Access Configuration

```typescript
import { API_CONFIG } from '@/config/api';

const timeout = API_CONFIG.timeout; // 30000
const baseUrl = API_CONFIG.baseUrl; // 'http://localhost:8080'
```

### Full Example (Fetch Request)

```typescript
import { getApiUrl, API_CONFIG } from '@/config/api';

async function createProject(data: ProjectData) {
  const response = await fetch(getApiUrl('/api/projects/start'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(API_CONFIG.timeout),
  });

  if (!response.ok) {
    throw new Error(`Project creation failed: ${response.statusText}`);
  }

  return response.json();
}
```

---

## 🧪 E2E Testing

E2E tests automatically use environment variables for server URLs:

```typescript
// frontend/e2e/utils/server-manager.ts
const BACKEND_URL = process.env.VITE_API_URL || 'http://localhost:8080';
const FRONTEND_URL = process.env.VITE_FRONTEND_URL || 'http://localhost:5173';
```

Run tests with custom URLs:

```bash
# Use default localhost URLs
npm run test:e2e

# Override for staging environment
VITE_API_URL=https://staging-api.example.com npm run test:e2e

# Override both backend and frontend
VITE_API_URL=https://api.example.com \
VITE_FRONTEND_URL=https://app.example.com \
npm run test:e2e
```

---

## 🔐 Security Best Practices

### DO ✅

- ✅ Commit `.env.example` and `.env.development` (no secrets)
- ✅ Add `.env.production` to `.gitignore`
- ✅ Use environment variables for API URLs
- ✅ Document all required variables
- ✅ Provide safe defaults for development

### DON'T ❌

- ❌ Commit `.env.production` with real credentials
- ❌ Hardcode API URLs in components
- ❌ Store secrets in `.env.example`
- ❌ Use production URLs in development
- ❌ Expose sensitive keys in frontend code

---

## 🌍 Deployment Environments

### Local Development

```env
VITE_API_URL=http://localhost:8080
VITE_API_TIMEOUT=30000
```

Files used: `.env.development` (auto-loaded)

### Staging

```env
VITE_API_URL=https://staging-api.your-domain.com
VITE_API_TIMEOUT=30000
VITE_SUPABASE_URL=https://staging-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-staging-key
```

Files used: `.env.production` or CI/CD environment variables

### Production

```env
VITE_API_URL=https://api.your-domain.com
VITE_API_TIMEOUT=30000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-production-key
```

Files used: `.env.production` or CI/CD environment variables

---

## 🐛 Troubleshooting

### Issue: Environment variables not loading

**Solution**: Ensure variables start with `VITE_` prefix (Vite requirement)

```env
# ❌ Wrong - won't be exposed to client
API_URL=http://localhost:8080

# ✅ Correct - exposed to client
VITE_API_URL=http://localhost:8080
```

### Issue: Changes not reflecting

**Solution**: Restart the dev server after changing `.env` files

```bash
# Stop server (Ctrl+C)
# Restart
npm run dev
```

### Issue: TypeScript errors with `import.meta.env`

**Solution**: Ensure `src/vite-env.d.ts` exists and is included in `tsconfig.json`

```typescript
// src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_API_TIMEOUT: string;
  // ... other variables
}
```

### Issue: Build fails with "import.meta not found"

**Solution**: Check `tsconfig.json` has correct module settings

```json
{
  "compilerOptions": {
    "module": "ESNext",
    "target": "ES2020"
  }
}
```

---

## 📚 Additional Resources

- [Vite Environment Variables](https://vite.dev/guide/env-and-mode.html)
- [TypeScript Environment Types](https://vite.dev/guide/env-and-mode.html#intellisense-for-typescript)
- [Deployment Best Practices](https://vite.dev/guide/static-deploy.html)

---

## ✅ Checklist

Before deploying:

- [ ] `.env.production` created with correct values
- [ ] All required variables set (`VITE_API_URL`, `VITE_API_TIMEOUT`)
- [ ] No secrets in `.env.example` or committed files
- [ ] Build succeeds: `npm run build`
- [ ] Preview works: `npm run preview`
- [ ] E2E tests pass: `npm run test:e2e`
- [ ] Environment-specific URLs verified
