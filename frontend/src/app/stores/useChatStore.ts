import { create } from 'zustand';
import type { ChatMessage } from '../types/audit';

interface ChatState {
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  getMessageById: (id: string) => ChatMessage | undefined;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map((msg) =>
      msg.id === id ? { ...msg, ...updates } : msg
    )
  })),

  clearMessages: () => set({ messages: [] }),

  getMessageById: (id) => get().messages.find((msg) => msg.id === id),
}));
