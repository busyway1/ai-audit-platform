import { create } from 'zustand'
import { supabase } from '../../lib/supabase'
import type { AuditTask, AuditTaskInsert, AuditTaskUpdate } from '../types/supabase'

interface TaskStoreState {
  tasks: Record<string, AuditTask>
  loading: boolean
  error: string | null
  subscriptions: Map<string, () => void>
}

interface TaskStoreActions {
  fetchTasks: (projectId: string) => Promise<void>
  fetchTaskById: (taskId: string) => Promise<AuditTask | null>
  updateTask: (taskId: string, data: AuditTaskUpdate) => Promise<void>
  deleteTask: (taskId: string) => Promise<void>
  createTask: (data: AuditTaskInsert) => Promise<AuditTask | null>
  subscribeToUpdates: (projectId: string) => () => void
  unsubscribeFromUpdates: (projectId: string) => void
  clearTasks: () => void
  setError: (error: string | null) => void
}

type TaskStore = TaskStoreState & TaskStoreActions

export const useTaskStore = create<TaskStore>((set, get) => ({
  // State
  tasks: {},
  loading: false,
  error: null,
  subscriptions: new Map(),

  // Actions
  fetchTasks: async (projectId: string) => {
    set({ loading: true, error: null })

    try {
      const { data, error } = await supabase
        .from('audit_tasks')
        .select('*')
        .eq('project_id', projectId)
        .order('created_at', { ascending: false })

      if (error) {
        throw new Error(error.message)
      }

      const taskMap = (data || []).reduce(
        (acc, task) => ({
          ...acc,
          [task.id]: task,
        }),
        {} as Record<string, AuditTask>
      )

      set({ tasks: taskMap, loading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch tasks'
      set({ error: errorMessage, loading: false })
    }
  },

  fetchTaskById: async (taskId: string) => {
    try {
      const { data, error } = await supabase
        .from('audit_tasks')
        .select('*')
        .eq('id', taskId)
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (data) {
        set((state) => ({
          tasks: {
            ...state.tasks,
            [data.id]: data,
          },
        }))
      }

      return data || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch task'
      set({ error: errorMessage })
      return null
    }
  },

  updateTask: async (taskId: string, updateData: AuditTaskUpdate) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_tasks')
        .update(updateData)
        .eq('id', taskId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      const currentTask = get().tasks[taskId]
      if (currentTask) {
        set((state) => ({
          tasks: {
            ...state.tasks,
            [taskId]: {
              ...currentTask,
              ...updateData,
            },
          },
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update task'
      set({ error: errorMessage })
      throw error
    }
  },

  deleteTask: async (taskId: string) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_tasks')
        .delete()
        .eq('id', taskId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      set((state) => {
        const newTasks = { ...state.tasks }
        delete newTasks[taskId]
        return { tasks: newTasks }
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete task'
      set({ error: errorMessage })
      throw error
    }
  },

  createTask: async (data) => {
    set({ error: null })

    try {
      const { data: newTask, error } = await supabase
        .from('audit_tasks')
        .insert([data])
        .select()
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (newTask) {
        set((state) => ({
          tasks: {
            ...state.tasks,
            [newTask.id]: newTask,
          },
        }))
      }

      return newTask || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create task'
      set({ error: errorMessage })
      return null
    }
  },

  subscribeToUpdates: (projectId: string) => {
    set({ error: null })

    // Avoid duplicate subscriptions
    const existingCleanup = get().subscriptions.get(projectId)
    if (existingCleanup) {
      existingCleanup()
    }

    const channel = supabase
      .channel(`project-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'audit_tasks',
          filter: `project_id=eq.${projectId}`,
        },
        (payload) => {
          const eventType = payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE'
          const newRecord = payload.new as AuditTask | undefined
          const oldRecord = payload.old as AuditTask | undefined

          set((state) => {
            const updatedTasks = { ...state.tasks }

            if (eventType === 'INSERT' && newRecord) {
              updatedTasks[newRecord.id] = newRecord
            } else if (eventType === 'UPDATE' && newRecord) {
              updatedTasks[newRecord.id] = newRecord
            } else if (eventType === 'DELETE' && oldRecord) {
              delete updatedTasks[oldRecord.id]
            }

            return { tasks: updatedTasks }
          })
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          // Subscription established
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          set({
            error: `Subscription error for project ${projectId}`,
          })
        }
      })

    // Store cleanup function
    const cleanup = () => {
      channel.unsubscribe()
    }

    set((state) => ({
      subscriptions: new Map(state.subscriptions).set(projectId, cleanup),
    }))

    return cleanup
  },

  unsubscribeFromUpdates: (projectId: string) => {
    const cleanup = get().subscriptions.get(projectId)
    if (cleanup) {
      cleanup()
      set((state) => {
        const newSubscriptions = new Map(state.subscriptions)
        newSubscriptions.delete(projectId)
        return { subscriptions: newSubscriptions }
      })
    }
  },

  clearTasks: () => {
    set({ tasks: {}, error: null })
  },

  setError: (error: string | null) => {
    set({ error })
  },
}))
