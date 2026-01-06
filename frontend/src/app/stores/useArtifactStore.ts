import { create } from 'zustand';
import type { Artifact, ArtifactTab, SplitLayout } from '../types/audit';

interface ArtifactState {
  artifacts: ArtifactTab[];
  activeArtifactId: string | null;
  pinnedArtifactId: string | null;
  splitLayout: SplitLayout;
  splitRatio: number;

  addArtifact: (artifact: Artifact) => void;
  removeArtifact: (id: string) => void;
  setActiveArtifact: (id: string | null) => void;
  pinArtifact: (id: string | null) => void;
  setSplitLayout: (layout: SplitLayout, ratio?: number) => void;
  updateArtifact: (id: string, updates: Partial<Artifact>) => void;
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  artifacts: [],
  activeArtifactId: null,
  pinnedArtifactId: null,
  splitLayout: 'none',
  splitRatio: 0.4, // 40% for artifact panel by default

  addArtifact: (artifact) => set((state) => {
    const newTab: ArtifactTab = { id: artifact.id, artifact, isPinned: false };
    return {
      artifacts: [...state.artifacts, newTab],
      activeArtifactId: artifact.id
    };
  }),

  removeArtifact: (id) => set((state) => ({
    artifacts: state.artifacts.filter((tab) => tab.id !== id),
    activeArtifactId: state.activeArtifactId === id ? null : state.activeArtifactId,
    pinnedArtifactId: state.pinnedArtifactId === id ? null : state.pinnedArtifactId,
  })),

  setActiveArtifact: (id) => set({ activeArtifactId: id }),

  pinArtifact: (id) => set((state) => ({
    pinnedArtifactId: id,
    artifacts: state.artifacts.map((tab) => ({
      ...tab,
      isPinned: tab.id === id
    })),
    splitLayout: id ? 'horizontal' : 'none'
  })),

  setSplitLayout: (layout, ratio) => set((state) => ({
    splitLayout: layout,
    splitRatio: ratio !== undefined ? ratio : state.splitRatio
  })),

  updateArtifact: (id, updates) => set((state) => ({
    artifacts: state.artifacts.map((tab) =>
      tab.artifact.id === id
        ? { ...tab, artifact: { ...tab.artifact, ...updates } }
        : tab
    )
  })),
}));
