import { useState } from 'react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/app/components/ui/resizable';
import { NavigationRail } from './NavigationRail';
import { ChatInterface } from './ChatInterface';
import { ArtifactPanel } from './ArtifactPanel';
import { useArtifactStore } from '@/app/stores/useArtifactStore';

export function AppShell() {
  const [currentView, setCurrentView] = useState<'chat' | 'workspace' | 'settings'>('chat');
  const { artifacts } = useArtifactStore();
  const hasArtifacts = artifacts.length > 0;

  const renderView = () => {
    switch (currentView) {
      case 'chat':
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

      case 'workspace':
        return (
          <div className="p-6">
            <h1 className="text-3xl mb-2">Audit Workspace</h1>
            <p className="text-gray-600">Phase 2: Workspace implementation coming soon</p>
          </div>
        );

      case 'settings':
        return (
          <div className="p-6">
            <h1 className="text-3xl mb-2">Settings</h1>
            <p className="text-gray-600">Phase 3: Settings implementation coming soon</p>
          </div>
        );

      default:
        return <ChatInterface />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <NavigationRail currentView={currentView} onViewChange={setCurrentView} />
      <div className="flex-1 overflow-hidden">
        {renderView()}
      </div>
    </div>
  );
}
