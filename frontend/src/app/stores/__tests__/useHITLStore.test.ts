import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useHITLStore } from '../useHITLStore'
import type { HITLRequest, HITLRequestInsert } from '../../types/supabase'

// Mock Supabase
vi.mock('../../lib/supabase', () => ({
  supabase: {
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          order: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
          single: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
        }),
        order: vi.fn().mockReturnValue({
          eq: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
        }),
      }),
      insert: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: null,
            error: null,
          }),
        }),
      }),
      update: vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({
          data: null,
          error: null,
        }),
      }),
      delete: vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({
          data: null,
          error: null,
        }),
      }),
    }),
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnValue({
        subscribe: vi.fn().mockResolvedValue(null),
      }),
      unsubscribe: vi.fn().mockResolvedValue(null),
    }),
  },
}))

describe('useHITLStore', () => {
  beforeEach(() => {
    act(() => {
      useHITLStore.getState().clearRequests()
      useHITLStore.getState().setError(null)
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Helper function to create mock HITL requests
  const createMockRequest = (id: string, overrides?: Partial<HITLRequest>): HITLRequest => ({
    id,
    task_id: 'task-1',
    project_id: 'project-1',
    request_type: 'approval',
    urgency_score: 75,
    title: 'Approve high-value transaction',
    context: 'Transaction exceeds materiality threshold',
    options: ['approve', 'reject', 'escalate'],
    status: 'pending',
    response: null,
    responded_by: null,
    responded_at: null,
    metadata: {},
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  })

  describe('State Management', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useHITLStore())

      expect(result.current.requests).toEqual({})
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe(null)
      expect(result.current.subscriptions.size).toBe(0)
    })

    it('should clear requests', () => {
      const { result } = renderHook(() => useHITLStore())

      act(() => {
        const request = createMockRequest('request-1')
        useHITLStore.setState({ requests: { [request.id]: request } })
      })

      expect(result.current.requests).not.toEqual({})

      act(() => {
        result.current.clearRequests()
      })

      expect(result.current.requests).toEqual({})
      expect(result.current.error).toBeNull()
    })

    it('should set error', () => {
      const { result } = renderHook(() => useHITLStore())

      act(() => {
        result.current.setError('Test error')
      })

      expect(result.current.error).toBe('Test error')

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('Request Management', () => {
    it('should add request to state', () => {
      const { result } = renderHook(() => useHITLStore())
      const request = createMockRequest('request-1')

      act(() => {
        useHITLStore.setState((state) => ({
          requests: { ...state.requests, [request.id]: request },
        }))
      })

      expect(result.current.requests['request-1']).toEqual(request)
      expect(Object.keys(result.current.requests)).toHaveLength(1)
    })

    it('should update request in state', () => {
      const { result } = renderHook(() => useHITLStore())
      const request = createMockRequest('request-1')

      act(() => {
        useHITLStore.setState({ requests: { [request.id]: request } })
      })

      const updatedRequest = {
        ...request,
        status: 'approved' as const,
        response: 'Approved by auditor',
      }

      act(() => {
        useHITLStore.setState((state) => ({
          requests: { ...state.requests, [request.id]: updatedRequest },
        }))
      })

      expect(result.current.requests['request-1'].status).toBe('approved')
      expect(result.current.requests['request-1'].response).toBe('Approved by auditor')
    })

    it('should delete request from state', () => {
      const { result } = renderHook(() => useHITLStore())
      const request = createMockRequest('request-1')

      act(() => {
        useHITLStore.setState({ requests: { [request.id]: request } })
      })

      expect(result.current.requests['request-1']).toBeDefined()

      act(() => {
        useHITLStore.setState((state) => {
          const newRequests = { ...state.requests }
          delete newRequests['request-1']
          return { requests: newRequests }
        })
      })

      expect(result.current.requests['request-1']).toBeUndefined()
    })

    it('should handle multiple requests', () => {
      const { result } = renderHook(() => useHITLStore())
      const request1 = createMockRequest('request-1', { urgency_score: 90 })
      const request2 = createMockRequest('request-2', { urgency_score: 60 })
      const request3 = createMockRequest('request-3', { urgency_score: 30 })

      act(() => {
        useHITLStore.setState({
          requests: {
            [request1.id]: request1,
            [request2.id]: request2,
            [request3.id]: request3,
          },
        })
      })

      expect(Object.keys(result.current.requests)).toHaveLength(3)
      expect(result.current.requests['request-1']).toEqual(request1)
      expect(result.current.requests['request-2']).toEqual(request2)
      expect(result.current.requests['request-3']).toEqual(request3)
    })
  })

  describe('Subscription Management', () => {
    it('should store subscription cleanup function', () => {
      const { result } = renderHook(() => useHITLStore())
      const mockCleanup = vi.fn()

      act(() => {
        useHITLStore.setState({ subscriptions: new Map() })
        useHITLStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', mockCleanup),
        }))
      })

      expect(result.current.subscriptions.get('project-1')).toBe(mockCleanup)
    })

    it('should handle multiple subscriptions', () => {
      const { result } = renderHook(() => useHITLStore())
      const cleanup1 = vi.fn()
      const cleanup2 = vi.fn()

      act(() => {
        useHITLStore.setState({ subscriptions: new Map() })
        useHITLStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions)
            .set('project-1', cleanup1)
            .set('project-2', cleanup2),
        }))
      })

      expect(result.current.subscriptions.size).toBe(2)
      expect(result.current.subscriptions.get('project-1')).toBe(cleanup1)
      expect(result.current.subscriptions.get('project-2')).toBe(cleanup2)
    })

    it('should remove subscription', () => {
      const { result } = renderHook(() => useHITLStore())
      const cleanup = vi.fn()

      act(() => {
        useHITLStore.setState({ subscriptions: new Map() })
        useHITLStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', cleanup),
        }))
      })

      expect(result.current.subscriptions.size).toBe(1)

      act(() => {
        const newSubscriptions = new Map()
        useHITLStore.setState({ subscriptions: newSubscriptions })
      })

      expect(result.current.subscriptions.size).toBe(0)
    })
  })

  describe('Loading State', () => {
    it('should set loading state', () => {
      const { result } = renderHook(() => useHITLStore())

      act(() => {
        useHITLStore.setState({ loading: true })
      })

      expect(result.current.loading).toBe(true)

      act(() => {
        useHITLStore.setState({ loading: false })
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('Request Creation', () => {
    it('should handle request insert data structure', () => {
      const insertData: HITLRequestInsert = {
        task_id: 'task-1',
        project_id: 'project-1',
        title: 'Approve transaction',
        context: 'High value transaction detected',
      }

      expect(insertData.task_id).toBe('task-1')
      expect(insertData.project_id).toBe('project-1')
      expect(insertData.title).toBe('Approve transaction')
    })
  })

  describe('Record Organization', () => {
    it('should organize requests by ID in record structure', () => {
      const { result } = renderHook(() => useHITLStore())
      const request1 = createMockRequest('request-1')
      const request2 = createMockRequest('request-2')

      act(() => {
        useHITLStore.setState({
          requests: {
            [request1.id]: request1,
            [request2.id]: request2,
          },
        })
      })

      const requests = result.current.requests
      expect(requests['request-1']).toBe(request1)
      expect(requests['request-2']).toBe(request2)
      expect(Object.keys(requests)).toEqual(expect.arrayContaining(['request-1', 'request-2']))
    })
  })

  describe('Error Handling', () => {
    it('should handle error state', () => {
      const { result } = renderHook(() => useHITLStore())

      act(() => {
        result.current.setError('Database connection failed')
      })

      expect(result.current.error).toBe('Database connection failed')
    })

    it('should clear error state', () => {
      const { result } = renderHook(() => useHITLStore())

      act(() => {
        result.current.setError('Test error')
      })

      expect(result.current.error).not.toBeNull()

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('Request Status Updates', () => {
    it('should handle request status changes', () => {
      const { result } = renderHook(() => useHITLStore())
      const request = createMockRequest('request-1', { status: 'pending' })

      act(() => {
        useHITLStore.setState({ requests: { [request.id]: request } })
      })

      expect(result.current.requests['request-1'].status).toBe('pending')

      const statusSequence: Array<'pending' | 'approved' | 'rejected' | 'expired'> = [
        'pending',
        'approved',
      ]

      statusSequence.forEach((status) => {
        act(() => {
          const currentRequest = result.current.requests['request-1']
          useHITLStore.setState({
            requests: {
              ...result.current.requests,
              [request.id]: { ...currentRequest, status },
            },
          })
        })

        expect(result.current.requests['request-1'].status).toBe(status)
      })
    })
  })

  describe('Helper Selectors', () => {
    it('should get requests by status', () => {
      const { result } = renderHook(() => useHITLStore())
      const pendingRequest = createMockRequest('request-1', { status: 'pending' })
      const approvedRequest = createMockRequest('request-2', { status: 'approved' })
      const rejectedRequest = createMockRequest('request-3', { status: 'rejected' })

      act(() => {
        useHITLStore.setState({
          requests: {
            [pendingRequest.id]: pendingRequest,
            [approvedRequest.id]: approvedRequest,
            [rejectedRequest.id]: rejectedRequest,
          },
        })
      })

      const pendingRequests = result.current.getRequestsByStatus('pending')
      expect(pendingRequests).toHaveLength(1)
      expect(pendingRequests[0].id).toBe('request-1')

      const approvedRequests = result.current.getRequestsByStatus('approved')
      expect(approvedRequests).toHaveLength(1)
      expect(approvedRequests[0].id).toBe('request-2')
    })

    it('should get requests by urgency score', () => {
      const { result } = renderHook(() => useHITLStore())
      const highUrgency = createMockRequest('request-1', { urgency_score: 90 })
      const mediumUrgency = createMockRequest('request-2', { urgency_score: 60 })
      const lowUrgency = createMockRequest('request-3', { urgency_score: 30 })

      act(() => {
        useHITLStore.setState({
          requests: {
            [highUrgency.id]: highUrgency,
            [mediumUrgency.id]: mediumUrgency,
            [lowUrgency.id]: lowUrgency,
          },
        })
      })

      const urgentRequests = result.current.getRequestsByUrgency(70)
      expect(urgentRequests).toHaveLength(1)
      expect(urgentRequests[0].id).toBe('request-1')

      const moderateRequests = result.current.getRequestsByUrgency(50)
      expect(moderateRequests).toHaveLength(2)
    })

    it('should get pending requests', () => {
      const { result } = renderHook(() => useHITLStore())
      const pendingRequest1 = createMockRequest('request-1', { status: 'pending' })
      const pendingRequest2 = createMockRequest('request-2', { status: 'pending' })
      const approvedRequest = createMockRequest('request-3', { status: 'approved' })

      act(() => {
        useHITLStore.setState({
          requests: {
            [pendingRequest1.id]: pendingRequest1,
            [pendingRequest2.id]: pendingRequest2,
            [approvedRequest.id]: approvedRequest,
          },
        })
      })

      const pendingRequests = result.current.getPendingRequests()
      expect(pendingRequests).toHaveLength(2)
      expect(pendingRequests.every((r) => r.status === 'pending')).toBe(true)
    })

    it('should get requests sorted by urgency', () => {
      const { result } = renderHook(() => useHITLStore())
      const highUrgency = createMockRequest('request-1', { urgency_score: 90 })
      const mediumUrgency = createMockRequest('request-2', { urgency_score: 60 })
      const lowUrgency = createMockRequest('request-3', { urgency_score: 30 })

      act(() => {
        useHITLStore.setState({
          requests: {
            [lowUrgency.id]: lowUrgency,
            [highUrgency.id]: highUrgency,
            [mediumUrgency.id]: mediumUrgency,
          },
        })
      })

      const sortedRequests = result.current.getRequestsSortedByUrgency()
      expect(sortedRequests).toHaveLength(3)
      expect(sortedRequests[0].urgency_score).toBe(90)
      expect(sortedRequests[1].urgency_score).toBe(60)
      expect(sortedRequests[2].urgency_score).toBe(30)
    })
  })

  describe('Response Submission', () => {
    it('should handle approve response data structure', () => {
      const responseData = {
        status: 'approved' as const,
        response: 'Approved after review',
        respondedBy: 'user-123',
      }

      expect(responseData.status).toBe('approved')
      expect(responseData.response).toBe('Approved after review')
      expect(responseData.respondedBy).toBe('user-123')
    })

    it('should handle reject response data structure', () => {
      const responseData = {
        status: 'rejected' as const,
        response: 'Rejected due to insufficient documentation',
        respondedBy: 'user-456',
      }

      expect(responseData.status).toBe('rejected')
      expect(responseData.response).toBe('Rejected due to insufficient documentation')
    })
  })

  describe('Request Types', () => {
    it('should handle different request types', () => {
      const { result } = renderHook(() => useHITLStore())
      const approvalRequest = createMockRequest('request-1', { request_type: 'approval' })
      const clarificationRequest = createMockRequest('request-2', { request_type: 'clarification' })
      const escalationRequest = createMockRequest('request-3', { request_type: 'escalation' })
      const reviewRequest = createMockRequest('request-4', { request_type: 'review' })

      act(() => {
        useHITLStore.setState({
          requests: {
            [approvalRequest.id]: approvalRequest,
            [clarificationRequest.id]: clarificationRequest,
            [escalationRequest.id]: escalationRequest,
            [reviewRequest.id]: reviewRequest,
          },
        })
      })

      expect(result.current.requests['request-1'].request_type).toBe('approval')
      expect(result.current.requests['request-2'].request_type).toBe('clarification')
      expect(result.current.requests['request-3'].request_type).toBe('escalation')
      expect(result.current.requests['request-4'].request_type).toBe('review')
    })
  })

  describe('Urgency Score Handling', () => {
    it('should correctly compare urgency scores', () => {
      const { result } = renderHook(() => useHITLStore())
      const critical = createMockRequest('request-1', { urgency_score: 95 })
      const high = createMockRequest('request-2', { urgency_score: 80 })
      const medium = createMockRequest('request-3', { urgency_score: 50 })
      const low = createMockRequest('request-4', { urgency_score: 20 })

      act(() => {
        useHITLStore.setState({
          requests: {
            [critical.id]: critical,
            [high.id]: high,
            [medium.id]: medium,
            [low.id]: low,
          },
        })
      })

      // Critical threshold (>=90)
      const criticalRequests = result.current.getRequestsByUrgency(90)
      expect(criticalRequests).toHaveLength(1)

      // High threshold (>=70)
      const highRequests = result.current.getRequestsByUrgency(70)
      expect(highRequests).toHaveLength(2)

      // Medium threshold (>=40)
      const mediumRequests = result.current.getRequestsByUrgency(40)
      expect(mediumRequests).toHaveLength(3)

      // Low threshold (>=10)
      const lowRequests = result.current.getRequestsByUrgency(10)
      expect(lowRequests).toHaveLength(4)
    })
  })
})
