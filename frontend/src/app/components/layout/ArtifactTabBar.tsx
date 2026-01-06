import { X, Pin } from 'lucide-react';
import { useArtifactStore } from '@/app/stores/useArtifactStore';

export function ArtifactTabBar() {
  const {
    artifacts,
    activeArtifactId,
    setActiveArtifact,
    removeArtifact,
    pinArtifact
  } = useArtifactStore();

  if (artifacts.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 overflow-x-auto bg-gray-50">
      {artifacts.map((tab) => (
        <div
          key={tab.id}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${
            tab.id === activeArtifactId
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
          }`}
        >
          <button
            onClick={() => setActiveArtifact(tab.id)}
            className="flex-1 text-left"
            aria-label={`Activate ${tab.artifact.title} artifact`}
          >
            {tab.artifact.title}
          </button>

          <button
            onClick={() => pinArtifact(tab.isPinned ? null : tab.id)}
            className={`p-1 rounded hover:bg-white/20 transition-colors ${
              tab.isPinned ? 'text-yellow-400' : ''
            }`}
            aria-label={tab.isPinned ? `Unpin ${tab.artifact.title}` : `Pin ${tab.artifact.title}`}
          >
            <Pin className="size-3" fill={tab.isPinned ? 'currentColor' : 'none'} />
          </button>

          <button
            onClick={() => removeArtifact(tab.id)}
            className="p-1 rounded hover:bg-white/20 transition-colors"
            aria-label={`Close ${tab.artifact.title}`}
          >
            <X className="size-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
