import { Outlet } from '@tanstack/react-router';
import { WorkspaceTabs } from './WorkspaceTabs';

export function WorkspaceLayout() {
  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Breadcrumb */}
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <p className="text-sm text-gray-500">
          Workspace <span className="text-gray-400">›</span>{' '}
          <span className="text-gray-900 font-medium">Dashboard</span>
        </p>
      </div>

      {/* Tabs Navigation */}
      <WorkspaceTabs />

      {/* Content Area */}
      <div className="flex-1 overflow-auto">
        <Outlet />
      </div>
    </div>
  );
}
