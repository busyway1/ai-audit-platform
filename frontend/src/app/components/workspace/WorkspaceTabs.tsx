import { Link, useRouterState } from '@tanstack/react-router';
import {
  LayoutDashboard,
  FileText,
  CheckSquare,
  AlertCircle,
  FolderOpen,
  Clipboard,
} from 'lucide-react';

interface Tab {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const tabs: Tab[] = [
  {
    name: 'Dashboard',
    path: '/workspace/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Financial Statements',
    path: '/workspace/financial-statements',
    icon: FileText,
  },
  {
    name: 'Tasks',
    path: '/workspace/tasks',
    icon: CheckSquare,
  },
  {
    name: 'Issues',
    path: '/workspace/issues',
    icon: AlertCircle,
  },
  {
    name: 'Documents',
    path: '/workspace/documents',
    icon: FolderOpen,
  },
  {
    name: 'Working Papers',
    path: '/workspace/working-papers',
    icon: Clipboard,
  },
];

export function WorkspaceTabs() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  const isActiveTab = (tabPath: string): boolean => {
    return currentPath === tabPath || currentPath.startsWith(`${tabPath}/`);
  };

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="px-6">
        <nav
          className="flex gap-2 overflow-x-auto scrollbar-hide"
          aria-label="Workspace navigation"
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = isActiveTab(tab.path);

            return (
              <Link
                key={tab.path}
                to={tab.path}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap
                  border-b-2 transition-colors duration-200
                  ${
                    isActive
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                  }
                `}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
                <span>{tab.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
