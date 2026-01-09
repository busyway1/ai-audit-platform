import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { supabase } from '../../lib/supabase'
import { getApiUrl } from '../../config/api'
import type { AuditProject, AuditProjectInsert, AuditProjectUpdate, AuditProjectStatus } from '../types/supabase'

/**
 * API Response types for backend endpoints
 */
interface ApiProjectResponse {
  id: string
  client_name: string
  fiscal_year: number
  overall_materiality: number | null
  status: string
  created_at: string
  updated_at: string | null
}

interface ProjectListApiResponse {
  status: string
  projects: ApiProjectResponse[]
  total: number
}

/**
 * Convert API response to AuditProject type
 */
function convertApiProjectToAuditProject(apiProject: ApiProjectResponse): AuditProject {
  return {
    id: apiProject.id,
    client_name: apiProject.client_name,
    fiscal_year: apiProject.fiscal_year,
    overall_materiality: apiProject.overall_materiality,
    status: apiProject.status as AuditProjectStatus,
    created_at: apiProject.created_at,
    updated_at: apiProject.updated_at || apiProject.created_at,
    metadata: {},
  }
}

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

// Type for the set function from Zustand
type SetState = {
  (partial: ProjectStore | Partial<ProjectStore> | ((state: ProjectStore) => ProjectStore | Partial<ProjectStore>), replace?: false): void
  (state: ProjectStore | ((state: ProjectStore) => ProjectStore), replace: true): void
}

// Separate the store definition to allow for persist middleware
const createProjectStore = (
  set: SetState,
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
      // Fetch projects from backend API
      const response = await fetch(getApiUrl('/api/projects'))

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error: ${response.status}`)
      }

      const data: ProjectListApiResponse = await response.json()

      // Convert API response to store format
      const projectMap = data.projects.reduce(
        (acc, apiProject) => ({
          ...acc,
          [apiProject.id]: convertApiProjectToAuditProject(apiProject),
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
      // Fetch single project from backend API
      const response = await fetch(getApiUrl(`/api/projects/${projectId}`))

      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error: ${response.status}`)
      }

      const data = await response.json()
      const project = convertApiProjectToAuditProject(data.project)

      set((state) => ({
        projects: {
          ...state.projects,
          [project.id]: project,
        },
      }))

      return project
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch project'
      set({ error: errorMessage })
      return null
    }
  },

  createProject: async (data: AuditProjectInsert) => {
    set({ error: null })

    try {
      // Create project via backend API
      const response = await fetch(getApiUrl('/api/projects'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_name: data.client_name,
          fiscal_year: data.fiscal_year,
          overall_materiality: data.overall_materiality,
          status: data.status?.toLowerCase() || 'planning',
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error: ${response.status}`)
      }

      const responseData = await response.json()
      const newProject = convertApiProjectToAuditProject(responseData.project)

      set((state) => ({
        projects: {
          ...state.projects,
          [newProject.id]: newProject,
        },
      }))

      return newProject
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create project'
      set({ error: errorMessage })
      return null
    }
  },

  updateProject: async (projectId: string, updateData: AuditProjectUpdate) => {
    set({ error: null })

    try {
      // Update project via backend API
      const response = await fetch(getApiUrl(`/api/projects/${projectId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_name: updateData.client_name,
          fiscal_year: updateData.fiscal_year,
          overall_materiality: updateData.overall_materiality,
          status: updateData.status?.toLowerCase(),
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error: ${response.status}`)
      }

      const responseData = await response.json()
      const updatedProject = convertApiProjectToAuditProject(responseData.project)

      set((state) => ({
        projects: {
          ...state.projects,
          [projectId]: updatedProject,
        },
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update project'
      set({ error: errorMessage })
      throw error
    }
  },

  deleteProject: async (projectId: string) => {
    set({ error: null })

    try {
      // Delete project via backend API
      const response = await fetch(getApiUrl(`/api/projects/${projectId}`), {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error: ${response.status}`)
      }

      // Update local state
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
