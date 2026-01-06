import { Outlet, useLocation, useNavigate } from '@tanstack/react-router';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/app/components/ui/resizable';
import { NavigationRail } from './NavigationRail';
import { ChatInterface } from './ChatInterface';
import { ArtifactPanel } from './ArtifactPanel';
import { useArtifactStore } from '@/app/stores/useArtifactStore';

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { artifacts } = useArtifactStore();
  const hasArtifacts = artifacts.length > 0;

  // Determine current view based on route
  const getCurrentView = (): 'chat' | 'workspace' | 'settings' => {
    if (location.pathname.startsWith('/workspace')) {
      return 'workspace';
    }
    if (location.pathname.startsWith('/settings')) {
      return 'settings';
    }
    return 'chat';
  };

  const currentView = getCurrentView();

  const handleViewChange = (view: 'chat' | 'workspace' | 'settings') => {
    switch (view) {
      case 'chat':
        navigate({ to: '/' });
        break;
      case 'workspace':
        navigate({ to: '/workspace/dashboard' });
        break;
      case 'settings':
        navigate({ to: '/settings/agent-tools' });
        break;
    }
  };

  const renderView = () => {
    // If on chat view (root path)
    if (currentView === 'chat') {
      if (hasArtifacts) {
        return (
          <ResizablePanelGroup direction="horizontal">
            <ResizablePanel defaultSize={60} minSize={30}>
              <ChatInterface />
            </ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={40} minSize={20}>
              <ArtifactPanel />
            </ResizablePanel>
          </ResizablePanelGroup>
        );
      }
      return <ChatInterface />;
    }

    // For workspace and settings, render nested routes
    return <Outlet />;
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <NavigationRail currentView={currentView} onViewChange={handleViewChange} />
      <div className="flex-1 overflow-hidden">
        {renderView()}
      </div>
    </div>
  );
}
