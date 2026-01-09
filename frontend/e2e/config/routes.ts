/**
 * E2E Test Route Configuration
 *
 * Centralized route definitions matching TanStack Router structure.
 * This ensures all E2E tests use consistent, correct routes.
 */

const BASE_URL = process.env.VITE_FRONTEND_URL || 'http://localhost:5173';
const BACKEND_URL = process.env.VITE_API_URL || 'http://localhost:8080';

/**
 * Application routes matching TanStack Router configuration
 */
export const ROUTES = {
  // Root route - Chat interface with AppShell
  root: '/',

  // Workspace routes
  workspace: {
    base: '/workspace',
    dashboard: '/workspace/dashboard',
    financialStatements: '/workspace/financial-statements',
    tasks: '/workspace/tasks',
    issues: '/workspace/issues',
    documents: '/workspace/documents',
    workingPapers: '/workspace/working-papers',
  },

  // Settings routes
  settings: {
    base: '/settings',
    agentTools: '/settings/agent-tools',
    preferences: '/settings/preferences',
  },
} as const;

/**
 * Full URLs for E2E navigation
 */
export const URLS = {
  // Frontend URLs
  frontend: {
    root: `${BASE_URL}${ROUTES.root}`,
    workspace: {
      dashboard: `${BASE_URL}${ROUTES.workspace.dashboard}`,
      financialStatements: `${BASE_URL}${ROUTES.workspace.financialStatements}`,
      tasks: `${BASE_URL}${ROUTES.workspace.tasks}`,
      issues: `${BASE_URL}${ROUTES.workspace.issues}`,
      documents: `${BASE_URL}${ROUTES.workspace.documents}`,
      workingPapers: `${BASE_URL}${ROUTES.workspace.workingPapers}`,
    },
    settings: {
      agentTools: `${BASE_URL}${ROUTES.settings.agentTools}`,
      preferences: `${BASE_URL}${ROUTES.settings.preferences}`,
    },
  },

  // Backend URLs
  backend: {
    health: `${BACKEND_URL}/api/health`,
    docs: `${BACKEND_URL}/docs`,
    redoc: `${BACKEND_URL}/redoc`,
  },
} as const;

/**
 * Helper to build full URL from route
 */
export function buildUrl(route: string): string {
  return `${BASE_URL}${route}`;
}

/**
 * Helper to build backend URL
 */
export function buildBackendUrl(path: string): string {
  return `${BACKEND_URL}${path}`;
}

/**
 * Export base URLs for backward compatibility
 */
export const FRONTEND_URL = BASE_URL;
export const BACKEND_API_URL = BACKEND_URL;
