import { create } from 'zustand'
import { supabase } from '../../lib/supabase'
import type { AuditEGA, AuditEGAInsert, AuditEGAUpdate } from '../types/supabase'

interface EGAStoreState {
  egas: Record<string, AuditEGA>
  loading: boolean
  error: string | null
  subscriptions: Map<string, () => void>
}

interface EGAStoreActions {
  fetchEGAs: (projectId: string) => Promise<void>
  fetchEGAById: (egaId: string) => Promise<AuditEGA | null>
  createEGA: (data: AuditEGAInsert) => Promise<AuditEGA | null>
  updateEGA: (egaId: string, data: AuditEGAUpdate) => Promise<void>
  deleteEGA: (egaId: string) => Promise<void>
  subscribeToUpdates: (projectId: string) => () => void
  unsubscribeFromUpdates: (projectId: string) => void
  clearEGAs: () => void
  setError: (error: string | null) => void
  getEGAsByProject: (projectId: string) => AuditEGA[]
}

type EGAStore = EGAStoreState & EGAStoreActions

export const useEGAStore = create<EGAStore>((set, get) => ({
  // State
  egas: {},
  loading: false,
  error: null,
  subscriptions: new Map(),

  // Actions
  fetchEGAs: async (projectId: string) => {
    set({ loading: true, error: null })

    try {
      const { data, error } = await supabase
        .from('audit_egas')
        .select('*')
        .eq('project_id', projectId)
        .order('created_at', { ascending: false })

      if (error) {
        throw new Error(error.message)
      }

      const egaMap = (data || []).reduce(
        (acc, ega) => ({
          ...acc,
          [ega.id]: ega,
        }),
        {} as Record<string, AuditEGA>
      )

      set({ egas: egaMap, loading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch EGAs'
      set({ error: errorMessage, loading: false })
    }
  },

  fetchEGAById: async (egaId: string) => {
    try {
      const { data, error } = await supabase
        .from('audit_egas')
        .select('*')
        .eq('id', egaId)
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (data) {
        set((state) => ({
          egas: {
            ...state.egas,
            [data.id]: data,
          },
        }))
      }

      return data || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch EGA'
      set({ error: errorMessage })
      return null
    }
  },

  createEGA: async (data: AuditEGAInsert) => {
    set({ error: null })

    try {
      const { data: newEGA, error } = await supabase
        .from('audit_egas')
        .insert([data])
        .select()
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (newEGA) {
        set((state) => ({
          egas: {
            ...state.egas,
            [newEGA.id]: newEGA,
          },
        }))
      }

      return newEGA || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create EGA'
      set({ error: errorMessage })
      return null
    }
  },

  updateEGA: async (egaId: string, updateData: AuditEGAUpdate) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_egas')
        .update(updateData)
        .eq('id', egaId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      const currentEGA = get().egas[egaId]
      if (currentEGA) {
        set((state) => ({
          egas: {
            ...state.egas,
            [egaId]: {
              ...currentEGA,
              ...updateData,
            },
          },
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update EGA'
      set({ error: errorMessage })
      throw error
    }
  },

  deleteEGA: async (egaId: string) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('audit_egas')
        .delete()
        .eq('id', egaId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      set((state) => {
        const newEGAs = { ...state.egas }
        delete newEGAs[egaId]
        return { egas: newEGAs }
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete EGA'
      set({ error: errorMessage })
      throw error
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
      .channel(`ega-project-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'audit_egas',
          filter: `project_id=eq.${projectId}`,
        },
        (payload) => {
          const eventType = payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE'
          const newRecord = payload.new as AuditEGA | undefined
          const oldRecord = payload.old as AuditEGA | undefined

          set((state) => {
            const updatedEGAs = { ...state.egas }

            if (eventType === 'INSERT' && newRecord) {
              updatedEGAs[newRecord.id] = newRecord
            } else if (eventType === 'UPDATE' && newRecord) {
              updatedEGAs[newRecord.id] = newRecord
            } else if (eventType === 'DELETE' && oldRecord) {
              delete updatedEGAs[oldRecord.id]
            }

            return { egas: updatedEGAs }
          })
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          // Subscription established
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          set({
            error: `Subscription error for EGAs in project ${projectId}`,
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

  clearEGAs: () => {
    set({ egas: {}, error: null })
  },

  setError: (error: string | null) => {
    set({ error })
  },

  getEGAsByProject: (projectId: string) => {
    const allEGAs = get().egas
    return Object.values(allEGAs).filter((ega) => ega.project_id === projectId)
  },
}))
