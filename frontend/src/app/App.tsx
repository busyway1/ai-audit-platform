import { Router, Route, RootRoute, RouterProvider, redirect } from '@tanstack/react-router';
import { AppShell } from './components/layout/AppShell';
import { WorkspaceLayout } from './components/workspace/WorkspaceLayout';
import { SettingsLayout } from './components/settings/SettingsLayout';
import { Dashboard } from './components/Dashboard';
import { FinancialStatements } from './components/FinancialStatements';
import { IssueTracker } from './components/IssueTracker';
import { Documents } from './components/Documents';
import { WorkingPaperViewer } from './components/WorkingPaperViewer';
import { EngagementPlan } from './components/EngagementPlan';
import { AgentToolsSettings } from './components/settings/AgentToolsSettings';
import { EGAList } from './components/ega/EGAList';
import { TaskHierarchyTree } from './components/tasks/TaskHierarchyTree';

// Placeholder component for User Preferences (Phase 3)
function UserPreferences() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">User Preferences</h1>
      <p className="text-gray-600">User preferences settings coming soon...</p>
    </div>
  );
}

// Create root route
const rootRoute = new RootRoute({
  component: AppShell,
});

// Create workspace routes
const workspaceRoute = new Route({
  getParentRoute: () => rootRoute,
  path: 'workspace',
  component: WorkspaceLayout,
});

const workspaceDashboardRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'dashboard',
  component: Dashboard,
});

const workspaceFinancialStatementsRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'financial-statements',
  component: FinancialStatements,
});

const workspaceTasksRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'tasks',
  component: TaskHierarchyTree,
});

const workspaceIssuesRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'issues',
  component: IssueTracker,
});

const workspaceDocumentsRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'documents',
  component: Documents,
});

const workspaceWorkingPapersRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'working-papers',
  component: WorkingPaperViewer,
});

const workspaceEGAsRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: 'egas',
  component: EGAList,
});

// Redirect /workspace to /workspace/dashboard
const workspaceIndexRoute = new Route({
  getParentRoute: () => workspaceRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/workspace/dashboard' });
  },
});

// Create settings routes
const settingsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: 'settings',
  component: SettingsLayout,
});

const settingsAgentToolsRoute = new Route({
  getParentRoute: () => settingsRoute,
  path: 'agent-tools',
  component: AgentToolsSettings,
});

const settingsPreferencesRoute = new Route({
  getParentRoute: () => settingsRoute,
  path: 'preferences',
  component: UserPreferences,
});

// Redirect /settings to /settings/agent-tools
const settingsIndexRoute = new Route({
  getParentRoute: () => settingsRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/settings/agent-tools' });
  },
});

// Root index route for chat (no component needed, handled by AppShell)
const rootIndexRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/',
});

// Create route tree
const routeTree = rootRoute.addChildren([
  rootIndexRoute,
  workspaceRoute.addChildren([
    workspaceIndexRoute,
    workspaceDashboardRoute,
    workspaceFinancialStatementsRoute,
    workspaceTasksRoute,
    workspaceIssuesRoute,
    workspaceDocumentsRoute,
    workspaceWorkingPapersRoute,
    workspaceEGAsRoute,
  ]),
  settingsRoute.addChildren([
    settingsIndexRoute,
    settingsAgentToolsRoute,
    settingsPreferencesRoute,
  ]),
]);

// Create router instance
const router = new Router({ routeTree });

// TypeScript: Register router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

export default function App() {
  return <RouterProvider router={router} />;
}