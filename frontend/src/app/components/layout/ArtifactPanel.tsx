import { useArtifactStore } from '@/app/stores/useArtifactStore';
import { ArtifactTabBar } from './ArtifactTabBar';
import { ArtifactRenderer } from '../artifacts/ArtifactRenderer';

export function ArtifactPanel() {
  const { artifacts, activeArtifactId } = useArtifactStore();
  const activeArtifact = artifacts.find(a => a.id === activeArtifactId);

  if (!activeArtifact) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <p className="text-gray-400">No artifact selected</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      <ArtifactTabBar />
      <div className="flex-1 overflow-auto p-6">
        <ArtifactRenderer artifact={activeArtifact.artifact} />
      </div>
    </div>
  );
}
