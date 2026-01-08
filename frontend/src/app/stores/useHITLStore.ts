import { create } from 'zustand'
import { supabase } from '../../lib/supabase'
import type {
  HITLRequest,
  HITLRequestInsert,
  HITLRequestUpdate,
  HITLRequestStatus,
} from '../types/supabase'

interface HITLStoreState {
  requests: Record<string, HITLRequest>
  loading: boolean
  error: string | null
  subscriptions: Map<string, () => void>
}

interface HITLResponse {
  status: 'approved' | 'rejected'
  response: string
  respondedBy?: string
}

interface HITLStoreActions {
  fetchRequests: (projectId: string) => Promise<void>
  fetchPendingRequests: (projectId?: string) => Promise<void>
  fetchRequestById: (requestId: string) => Promise<HITLRequest | null>
  createRequest: (data: HITLRequestInsert) => Promise<HITLRequest | null>
  updateRequest: (requestId: string, data: HITLRequestUpdate) => Promise<void>
  submitResponse: (requestId: string, response: HITLResponse) => Promise<void>
  deleteRequest: (requestId: string) => Promise<void>
  subscribeToUpdates: (projectId: string) => () => void
  unsubscribeFromUpdates: (projectId: string) => void
  clearRequests: () => void
  setError: (error: string | null) => void
  getRequestsByStatus: (status: HITLRequestStatus) => HITLRequest[]
  getRequestsByUrgency: (minScore: number) => HITLRequest[]
  getPendingRequests: () => HITLRequest[]
  getRequestsSortedByUrgency: () => HITLRequest[]
}

type HITLStore = HITLStoreState & HITLStoreActions

export const useHITLStore = create<HITLStore>((set, get) => ({
  // State
  requests: {},
  loading: false,
  error: null,
  subscriptions: new Map(),

  // Actions
  fetchRequests: async (projectId: string) => {
    set({ loading: true, error: null })

    try {
      const { data, error } = await supabase
        .from('hitl_requests')
        .select('*')
        .eq('project_id', projectId)
        .order('urgency_score', { ascending: false })

      if (error) {
        throw new Error(error.message)
      }

      const requestMap = (data || []).reduce(
        (acc, request) => ({
          ...acc,
          [request.id]: request,
        }),
        {} as Record<string, HITLRequest>
      )

      set({ requests: requestMap, loading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch HITL requests'
      set({ error: errorMessage, loading: false })
    }
  },

  fetchPendingRequests: async (projectId?: string) => {
    set({ loading: true, error: null })

    try {
      let query = supabase
        .from('hitl_requests')
        .select('*')
        .eq('status', 'pending')
        .order('urgency_score', { ascending: false })

      if (projectId) {
        query = query.eq('project_id', projectId)
      }

      const { data, error } = await query

      if (error) {
        throw new Error(error.message)
      }

      const requestMap = (data || []).reduce(
        (acc, request) => ({
          ...acc,
          [request.id]: request,
        }),
        {} as Record<string, HITLRequest>
      )

      set({ requests: requestMap, loading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch pending requests'
      set({ error: errorMessage, loading: false })
    }
  },

  fetchRequestById: async (requestId: string) => {
    try {
      const { data, error } = await supabase
        .from('hitl_requests')
        .select('*')
        .eq('id', requestId)
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (data) {
        set((state) => ({
          requests: {
            ...state.requests,
            [data.id]: data,
          },
        }))
      }

      return data || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch HITL request'
      set({ error: errorMessage })
      return null
    }
  },

  createRequest: async (data: HITLRequestInsert) => {
    set({ error: null })

    try {
      const { data: newRequest, error } = await supabase
        .from('hitl_requests')
        .insert([data])
        .select()
        .single()

      if (error) {
        throw new Error(error.message)
      }

      if (newRequest) {
        set((state) => ({
          requests: {
            ...state.requests,
            [newRequest.id]: newRequest,
          },
        }))
      }

      return newRequest || null
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create HITL request'
      set({ error: errorMessage })
      return null
    }
  },

  updateRequest: async (requestId: string, updateData: HITLRequestUpdate) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('hitl_requests')
        .update(updateData)
        .eq('id', requestId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      const currentRequest = get().requests[requestId]
      if (currentRequest) {
        set((state) => ({
          requests: {
            ...state.requests,
            [requestId]: {
              ...currentRequest,
              ...updateData,
            },
          },
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update HITL request'
      set({ error: errorMessage })
      throw error
    }
  },

  submitResponse: async (requestId: string, responseData: HITLResponse) => {
    set({ error: null })

    try {
      const updateData: HITLRequestUpdate = {
        status: responseData.status,
        response: responseData.response,
        responded_by: responseData.respondedBy || null,
        responded_at: new Date().toISOString(),
      }

      const { error } = await supabase
        .from('hitl_requests')
        .update(updateData)
        .eq('id', requestId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      const currentRequest = get().requests[requestId]
      if (currentRequest) {
        set((state) => ({
          requests: {
            ...state.requests,
            [requestId]: {
              ...currentRequest,
              ...updateData,
            },
          },
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit response'
      set({ error: errorMessage })
      throw error
    }
  },

  deleteRequest: async (requestId: string) => {
    set({ error: null })

    try {
      const { error } = await supabase
        .from('hitl_requests')
        .delete()
        .eq('id', requestId)

      if (error) {
        throw new Error(error.message)
      }

      // Optimistically update local state
      set((state) => {
        const newRequests = { ...state.requests }
        delete newRequests[requestId]
        return { requests: newRequests }
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete HITL request'
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
      .channel(`hitl-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'hitl_requests',
          filter: `project_id=eq.${projectId}`,
        },
        (payload) => {
          const eventType = payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE'
          const newRecord = payload.new as HITLRequest | undefined
          const oldRecord = payload.old as HITLRequest | undefined

          set((state) => {
            const updatedRequests = { ...state.requests }

            if (eventType === 'INSERT' && newRecord) {
              updatedRequests[newRecord.id] = newRecord
            } else if (eventType === 'UPDATE' && newRecord) {
              updatedRequests[newRecord.id] = newRecord
            } else if (eventType === 'DELETE' && oldRecord) {
              delete updatedRequests[oldRecord.id]
            }

            return { requests: updatedRequests }
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

  clearRequests: () => {
    set({ requests: {}, error: null })
  },

  setError: (error: string | null) => {
    set({ error })
  },

  // Helper selectors
  getRequestsByStatus: (status: HITLRequestStatus) => {
    const requests = get().requests
    return Object.values(requests).filter((request) => request.status === status)
  },

  getRequestsByUrgency: (minScore: number) => {
    const requests = get().requests
    return Object.values(requests).filter((request) => request.urgency_score >= minScore)
  },

  getPendingRequests: () => {
    const requests = get().requests
    return Object.values(requests).filter((request) => request.status === 'pending')
  },

  getRequestsSortedByUrgency: () => {
    const requests = get().requests
    return Object.values(requests).sort((a, b) => b.urgency_score - a.urgency_score)
  },
}))
