import { create } from 'zustand';

interface SessionState {
  currentEngagement: string;
  lastSyncTime: string;

  saveSession: () => void;
  restoreSession: () => void;
  setCurrentEngagement: (id: string) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  currentEngagement: 'ABC Corporation - FY 2025',
  lastSyncTime: new Date().toISOString(),

  saveSession: () => {
    // Will be implemented with chat/artifact stores in integration
    const sessionData = {
      currentEngagement: get().currentEngagement,
      timestamp: Date.now(),
    };
    localStorage.setItem('audit-session', JSON.stringify(sessionData));
  },

  restoreSession: () => {
    const saved = localStorage.getItem('audit-session');
    if (saved) {
      const data = JSON.parse(saved);
      set({
        currentEngagement: data.currentEngagement,
        lastSyncTime: new Date(data.timestamp).toISOString(),
      });
    }
  },

  setCurrentEngagement: (id) => set({ currentEngagement: id }),
}));
