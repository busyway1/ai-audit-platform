import { create } from 'zustand';
import type { Task, Issue, Document } from '../types/audit';

interface EntityState {
  tasks: Record<string, Task>;
  issues: Record<string, Issue>;
  documents: Record<string, Document>;

  updateTask: (id: string, data: Partial<Task>) => void;
  updateIssue: (id: string, data: Partial<Issue>) => void;
  updateDocument: (id: string, data: Partial<Document>) => void;

  addTask: (task: Task) => void;
  addIssue: (issue: Issue) => void;
  addDocument: (document: Document) => void;

  removeTask: (id: string) => void;
  removeIssue: (id: string) => void;
  removeDocument: (id: string) => void;

  getTasks: () => Task[];
  getIssues: () => Issue[];
  getDocuments: () => Document[];

  getTask: (id: string) => Task | undefined;
  getIssue: (id: string) => Issue | undefined;
  getDocument: (id: string) => Document | undefined;

  bulkUpdateTasks: (updates: Record<string, Partial<Task>>) => void;
  bulkUpdateIssues: (updates: Record<string, Partial<Issue>>) => void;
  bulkUpdateDocuments: (updates: Record<string, Partial<Document>>) => void;

  setTasks: (tasks: Task[]) => void;
  setIssues: (issues: Issue[]) => void;
  setDocuments: (documents: Document[]) => void;

  clearAll: () => void;
}

export const useEntityStore = create<EntityState>((set, get) => ({
  tasks: {},
  issues: {},
  documents: {},

  updateTask: (id, data) =>
    set((state) => ({
      tasks: {
        ...state.tasks,
        [id]: state.tasks[id] ? { ...state.tasks[id], ...data } : state.tasks[id],
      },
    })),

  updateIssue: (id, data) =>
    set((state) => ({
      issues: {
        ...state.issues,
        [id]: state.issues[id] ? { ...state.issues[id], ...data } : state.issues[id],
      },
    })),

  updateDocument: (id, data) =>
    set((state) => ({
      documents: {
        ...state.documents,
        [id]: state.documents[id]
          ? { ...state.documents[id], ...data }
          : state.documents[id],
      },
    })),

  addTask: (task) =>
    set((state) => ({
      tasks: { ...state.tasks, [task.id]: task },
    })),

  addIssue: (issue) =>
    set((state) => ({
      issues: { ...state.issues, [issue.id]: issue },
    })),

  addDocument: (document) =>
    set((state) => ({
      documents: { ...state.documents, [document.id]: document },
    })),

  removeTask: (id) =>
    set((state) => {
      const newTasks = { ...state.tasks };
      delete newTasks[id];
      return { tasks: newTasks };
    }),

  removeIssue: (id) =>
    set((state) => {
      const newIssues = { ...state.issues };
      delete newIssues[id];
      return { issues: newIssues };
    }),

  removeDocument: (id) =>
    set((state) => {
      const newDocuments = { ...state.documents };
      delete newDocuments[id];
      return { documents: newDocuments };
    }),

  getTasks: () => Object.values(get().tasks),

  getIssues: () => Object.values(get().issues),

  getDocuments: () => Object.values(get().documents),

  getTask: (id) => get().tasks[id],

  getIssue: (id) => get().issues[id],

  getDocument: (id) => get().documents[id],

  bulkUpdateTasks: (updates) =>
    set((state) => ({
      tasks: Object.entries(updates).reduce(
        (acc, [id, data]) => ({
          ...acc,
          [id]: state.tasks[id] ? { ...state.tasks[id], ...data } : state.tasks[id],
        }),
        state.tasks
      ),
    })),

  bulkUpdateIssues: (updates) =>
    set((state) => ({
      issues: Object.entries(updates).reduce(
        (acc, [id, data]) => ({
          ...acc,
          [id]: state.issues[id] ? { ...state.issues[id], ...data } : state.issues[id],
        }),
        state.issues
      ),
    })),

  bulkUpdateDocuments: (updates) =>
    set((state) => ({
      documents: Object.entries(updates).reduce(
        (acc, [id, data]) => ({
          ...acc,
          [id]: state.documents[id]
            ? { ...state.documents[id], ...data }
            : state.documents[id],
        }),
        state.documents
      ),
    })),

  setTasks: (tasks) =>
    set({
      tasks: tasks.reduce(
        (acc, task) => ({ ...acc, [task.id]: task }),
        {} as Record<string, Task>
      ),
    }),

  setIssues: (issues) =>
    set({
      issues: issues.reduce(
        (acc, issue) => ({ ...acc, [issue.id]: issue }),
        {} as Record<string, Issue>
      ),
    }),

  setDocuments: (documents) =>
    set({
      documents: documents.reduce(
        (acc, doc) => ({ ...acc, [doc.id]: doc }),
        {} as Record<string, Document>
      ),
    }),

  clearAll: () =>
    set({
      tasks: {},
      issues: {},
      documents: {},
    }),
}));
