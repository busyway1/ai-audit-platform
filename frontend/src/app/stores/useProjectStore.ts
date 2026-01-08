import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { supabase } from '../../lib/supabase'
import type { AuditProject, AuditProjectInsert, AuditProjectUpdate } from '../types/supabase'

interface ProjectStoreState {
  projects: Record<string, AuditProject>
  selectedProjectId: string | null
  loading: boolean
  error: string | null
  subscriptions: Map<string, () => void>
}

interface ProjectStoreActions {
  fetchProjects: () => Promise<void>
  fetchProjectById: (projectId: string) => Promise<AuditProject | null>
  createProject: (data: AuditProjectInsert) => Promise<AuditProject | null>
  updateProject: (projectId: string, data: AuditProjectUpdate) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  selectProject: (projectId: string | null) => void
  subscribeToUpdates: () => () => void
  unsubscribeFromUpdates: () => void
  clearProjects: () => void
  setError: (error: string | null) => void
}

type ProjectStore = ProjectStoreState & ProjectStoreActions

// Separate the store definition to allow for persist middleware
const createProjectStore = (
  set: (
    partial: ProjectStoreState | Partial<ProjectStoreState> | ((state: ProjectStoreState) => ProjectStoreState | Partial<ProjectStoreState>),
    replace?: boolean
  ) => void,
  get: () => ProjectStore
): ProjectStore => ({
  // State
  projects: {},
  selectedProjectId: null,
  loading: false,
  error: null,
  subscriptions: new Map(),

  // Actions
  fetchProjects: async () => {
    set({ loading: true, error: null })

    try {
      const { data, error } = await supabase
        .from('audit_projects')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) {
        throw new Error(error.message)
      }

      const projectMap = (data || []).reduce(
        (acc, project) => ({
          ...acc,
          [project.id]: project,
        }),
        {} as Record<string, AuditProject>
      )

      set({ projects: projectMap, loading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch projects'
      set({ error: errorMessage, loading: false })
    }
  },

  fetchProjectById: async (projectId: string) => {
    try {
      const { data, error } = await supabase
        .from('audit_projects')
        .select('*')
        .eq('id', projectId)
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (data) {
        set((state) => ({
          projects: {
            ...state.projects,
            [data.id]: data,
          },
        }))
      }

      return data || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch project'
      set({ error: errorMessage })
      return null
    }
  },

  createProject: async (data: AuditProjectInsert) => {
    set({ error: null })

    try {
      const { data: newProject, error } = await supabase
        .from('audit_projects')
        .insert([data])
        .select()
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (newProject) {
        set((state) => ({
          projects: {
            ...state.projects,
            [newProject.id]: newProject,
          },
        }))
      }

      return newProject || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create project'
      set({ error: errorMessage })
      return null
    }
  },

  updateProject: async (projectId: string, updateData: AuditProjectUpdate) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_projects')
        .update(updateData)
        .eq('id', projectId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      const currentProject = get().projects[projectId]
      if (currentProject) {
        set((state) => ({
          projects: {
            ...state.projects,
            [projectId]: {
              ...currentProject,
              ...updateData,
            },
          },
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update project'
      set({ error: errorMessage })
      throw error
    }
  },

  deleteProject: async (projectId: string) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_projects')
        .delete()
        .eq('id', projectId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      set((state) => {
        const newProjects = { ...state.projects }
        delete newProjects[projectId]

        // Clear selected project if it was deleted
        const newSelectedProjectId = state.selectedProjectId === projectId
          ? null
          : state.selectedProjectId

        return {
          projects: newProjects,
          selectedProjectId: newSelectedProjectId,
        }
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete project'
      set({ error: errorMessage })
      throw error
    }
  },

  selectProject: (projectId: string | null) => {
    set({ selectedProjectId: projectId, error: null })
  },

  subscribeToUpdates: () => {
    set({ error: null })

    // Avoid duplicate subscriptions
    const existingCleanup = get().subscriptions.get('projects')
    if (existingCleanup) {
      existingCleanup()
    }

    const channel = supabase
      .channel('audit-projects')
      .on(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'audit_projects',
        },
        (payload) => {
          const eventType = payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE'
          const newRecord = payload.new as AuditProject | undefined
          const oldRecord = payload.old as AuditProject | undefined

          set((state) => {
            const updatedProjects = { ...state.projects }

            if (eventType === 'INSERT' && newRecord) {
              updatedProjects[newRecord.id] = newRecord
            } else if (eventType === 'UPDATE' && newRecord) {
              updatedProjects[newRecord.id] = newRecord
            } else if (eventType === 'DELETE' && oldRecord) {
              delete updatedProjects[oldRecord.id]
            }

            // Clear selected project if it was deleted
            const newSelectedProjectId =
              eventType === 'DELETE' && oldRecord && state.selectedProjectId === oldRecord.id
                ? null
                : state.selectedProjectId

            return {
              projects: updatedProjects,
              selectedProjectId: newSelectedProjectId,
            }
          })
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          // Subscription established
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          set({
            error: 'Subscription error for projects',
          })
        }
      })

    // Store cleanup function
    const cleanup = () => {
      channel.unsubscribe()
    }

    set((state) => ({
      subscriptions: new Map(state.subscriptions).set('projects', cleanup),
    }))

    return cleanup
  },

  unsubscribeFromUpdates: () => {
    const cleanup = get().subscriptions.get('projects')
    if (cleanup) {
      cleanup()
      set((state) => {
        const newSubscriptions = new Map(state.subscriptions)
        newSubscriptions.delete('projects')
        return { subscriptions: newSubscriptions }
      })
    }
  },

  clearProjects: () => {
    set({ projects: {}, selectedProjectId: null, error: null })
  },

  setError: (error: string | null) => {
    set({ error })
  },
})

// Helper to get the selected project from the store
export const getSelectedProject = (state: ProjectStore): AuditProject | null => {
  if (!state.selectedProjectId) return null
  return state.projects[state.selectedProjectId] || null
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set, get) => createProjectStore(set, get),
    {
      name: 'project-store',
      // Only persist selectedProjectId, not the full projects data
      partialize: (state) => ({
        selectedProjectId: state.selectedProjectId,
      }),
    }
  )
)
