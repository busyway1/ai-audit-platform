import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEGAStore } from '../useEGAStore'
import type { AuditEGA, AuditEGAInsert } from '../../types/supabase'

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

describe('useEGAStore', () => {
  beforeEach(() => {
    act(() => {
      useEGAStore.getState().clearEGAs()
      useEGAStore.getState().setError(null)
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Helper function to create mock EGAs
  const createMockEGA = (id: string, overrides?: Partial<AuditEGA>): AuditEGA => ({
    id,
    project_id: 'project-1',
    name: 'Revenue Recognition',
    description: 'EGA for revenue recognition testing',
    risk_level: 'Medium',
    status: 'Not-Started',
    progress: 0,
    total_tasks: 10,
    completed_tasks: 0,
    metadata: {},
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  })

  describe('State Management', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useEGAStore())

      expect(result.current.egas).toEqual({})
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe(null)
      expect(result.current.subscriptions.size).toBe(0)
    })

    it('should clear EGAs', () => {
      const { result } = renderHook(() => useEGAStore())

      act(() => {
        const ega = createMockEGA('ega-1')
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      expect(result.current.egas).not.toEqual({})

      act(() => {
        result.current.clearEGAs()
      })

      expect(result.current.egas).toEqual({})
      expect(result.current.error).toBeNull()
    })

    it('should set error', () => {
      const { result } = renderHook(() => useEGAStore())

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

  describe('EGA Management', () => {
    it('should add EGA to state', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1')

      act(() => {
        useEGAStore.setState((state) => ({
          egas: { ...state.egas, [ega.id]: ega },
        }))
      })

      expect(result.current.egas['ega-1']).toEqual(ega)
      expect(Object.keys(result.current.egas)).toHaveLength(1)
    })

    it('should update EGA in state', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1')

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      const updatedEGA = {
        ...ega,
        status: 'In-Progress' as const,
        progress: 50,
      }

      act(() => {
        useEGAStore.setState((state) => ({
          egas: { ...state.egas, [ega.id]: updatedEGA },
        }))
      })

      expect(result.current.egas['ega-1'].status).toBe('In-Progress')
      expect(result.current.egas['ega-1'].progress).toBe(50)
    })

    it('should delete EGA from state', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1')

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      expect(result.current.egas['ega-1']).toBeDefined()

      act(() => {
        useEGAStore.setState((state) => {
          const newEGAs = { ...state.egas }
          delete newEGAs['ega-1']
          return { egas: newEGAs }
        })
      })

      expect(result.current.egas['ega-1']).toBeUndefined()
    })

    it('should handle multiple EGAs', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega1 = createMockEGA('ega-1', { name: 'Revenue Recognition' })
      const ega2 = createMockEGA('ega-2', { name: 'Inventory Valuation' })
      const ega3 = createMockEGA('ega-3', { name: 'Accounts Receivable' })

      act(() => {
        useEGAStore.setState({
          egas: {
            [ega1.id]: ega1,
            [ega2.id]: ega2,
            [ega3.id]: ega3,
          },
        })
      })

      expect(Object.keys(result.current.egas)).toHaveLength(3)
      expect(result.current.egas['ega-1']).toEqual(ega1)
      expect(result.current.egas['ega-2']).toEqual(ega2)
      expect(result.current.egas['ega-3']).toEqual(ega3)
    })
  })

  describe('Subscription Management', () => {
    it('should store subscription cleanup function', () => {
      const { result } = renderHook(() => useEGAStore())
      const mockCleanup = vi.fn()

      act(() => {
        useEGAStore.setState({ subscriptions: new Map() })
        useEGAStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', mockCleanup),
        }))
      })

      expect(result.current.subscriptions.get('project-1')).toBe(mockCleanup)
    })

    it('should handle multiple subscriptions', () => {
      const { result } = renderHook(() => useEGAStore())
      const cleanup1 = vi.fn()
      const cleanup2 = vi.fn()

      act(() => {
        useEGAStore.setState({ subscriptions: new Map() })
        useEGAStore.setState((state) => ({
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
      const { result } = renderHook(() => useEGAStore())
      const cleanup = vi.fn()

      act(() => {
        useEGAStore.setState({ subscriptions: new Map() })
        useEGAStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', cleanup),
        }))
      })

      expect(result.current.subscriptions.size).toBe(1)

      act(() => {
        const newSubscriptions = new Map()
        useEGAStore.setState({ subscriptions: newSubscriptions })
      })

      expect(result.current.subscriptions.size).toBe(0)
    })
  })

  describe('Loading State', () => {
    it('should set loading state', () => {
      const { result } = renderHook(() => useEGAStore())

      act(() => {
        useEGAStore.setState({ loading: true })
      })

      expect(result.current.loading).toBe(true)

      act(() => {
        useEGAStore.setState({ loading: false })
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('EGA Creation', () => {
    it('should handle EGA insert data structure', () => {
      const insertData: AuditEGAInsert = {
        project_id: 'project-1',
        name: 'Revenue Recognition',
        description: 'Testing revenue recognition',
        risk_level: 'High',
      }

      expect(insertData.project_id).toBe('project-1')
      expect(insertData.name).toBe('Revenue Recognition')
      expect(insertData.risk_level).toBe('High')
    })
  })

  describe('Record Organization', () => {
    it('should organize EGAs by ID in record structure', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega1 = createMockEGA('ega-1')
      const ega2 = createMockEGA('ega-2')

      act(() => {
        useEGAStore.setState({
          egas: {
            [ega1.id]: ega1,
            [ega2.id]: ega2,
          },
        })
      })

      const egas = result.current.egas
      expect(egas['ega-1']).toBe(ega1)
      expect(egas['ega-2']).toBe(ega2)
      expect(Object.keys(egas)).toEqual(expect.arrayContaining(['ega-1', 'ega-2']))
    })
  })

  describe('Error Handling', () => {
    it('should handle error state', () => {
      const { result } = renderHook(() => useEGAStore())

      act(() => {
        result.current.setError('Database connection failed')
      })

      expect(result.current.error).toBe('Database connection failed')
    })

    it('should clear error state', () => {
      const { result } = renderHook(() => useEGAStore())

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

  describe('EGA Status Updates', () => {
    it('should handle EGA status changes', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1', { status: 'Not-Started' })

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      expect(result.current.egas['ega-1'].status).toBe('Not-Started')

      const statusSequence: Array<'Not-Started' | 'In-Progress' | 'Completed'> = [
        'Not-Started',
        'In-Progress',
        'Completed',
      ]

      statusSequence.forEach((status) => {
        act(() => {
          const currentEGA = result.current.egas['ega-1']
          useEGAStore.setState({
            egas: {
              ...result.current.egas,
              [ega.id]: { ...currentEGA, status },
            },
          })
        })

        expect(result.current.egas['ega-1'].status).toBe(status)
      })
    })
  })

  describe('Risk Level Management', () => {
    it('should handle different risk levels', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1', { risk_level: 'Low' })

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      expect(result.current.egas['ega-1'].risk_level).toBe('Low')

      const riskLevels: Array<'Low' | 'Medium' | 'High' | 'Critical'> = [
        'Low',
        'Medium',
        'High',
        'Critical',
      ]

      riskLevels.forEach((riskLevel) => {
        act(() => {
          const currentEGA = result.current.egas['ega-1']
          useEGAStore.setState({
            egas: {
              ...result.current.egas,
              [ega.id]: { ...currentEGA, risk_level: riskLevel },
            },
          })
        })

        expect(result.current.egas['ega-1'].risk_level).toBe(riskLevel)
      })
    })
  })

  describe('Progress Tracking', () => {
    it('should track progress updates', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1', {
        progress: 0,
        total_tasks: 10,
        completed_tasks: 0,
      })

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      expect(result.current.egas['ega-1'].progress).toBe(0)
      expect(result.current.egas['ega-1'].completed_tasks).toBe(0)

      act(() => {
        const currentEGA = result.current.egas['ega-1']
        useEGAStore.setState({
          egas: {
            ...result.current.egas,
            [ega.id]: {
              ...currentEGA,
              progress: 50,
              completed_tasks: 5,
            },
          },
        })
      })

      expect(result.current.egas['ega-1'].progress).toBe(50)
      expect(result.current.egas['ega-1'].completed_tasks).toBe(5)
    })
  })

  describe('getEGAsByProject', () => {
    it('should filter EGAs by project ID', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega1 = createMockEGA('ega-1', { project_id: 'project-1' })
      const ega2 = createMockEGA('ega-2', { project_id: 'project-1' })
      const ega3 = createMockEGA('ega-3', { project_id: 'project-2' })

      act(() => {
        useEGAStore.setState({
          egas: {
            [ega1.id]: ega1,
            [ega2.id]: ega2,
            [ega3.id]: ega3,
          },
        })
      })

      const project1EGAs = result.current.getEGAsByProject('project-1')
      expect(project1EGAs).toHaveLength(2)
      expect(project1EGAs.map((e) => e.id)).toContain('ega-1')
      expect(project1EGAs.map((e) => e.id)).toContain('ega-2')

      const project2EGAs = result.current.getEGAsByProject('project-2')
      expect(project2EGAs).toHaveLength(1)
      expect(project2EGAs[0].id).toBe('ega-3')
    })

    it('should return empty array for non-existent project', () => {
      const { result } = renderHook(() => useEGAStore())
      const ega = createMockEGA('ega-1', { project_id: 'project-1' })

      act(() => {
        useEGAStore.setState({ egas: { [ega.id]: ega } })
      })

      const noProjectEGAs = result.current.getEGAsByProject('non-existent')
      expect(noProjectEGAs).toHaveLength(0)
    })
  })
})
