import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTaskStore } from '../useTaskStore'
import type { AuditTask, AuditTaskInsert } from '../../types/supabase'

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

describe('useTaskStore', () => {
  beforeEach(() => {
    act(() => {
      useTaskStore.getState().clearTasks()
      useTaskStore.getState().setError(null)
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Helper function to create mock tasks
  const createMockTask = (id: string, overrides?: Partial<AuditTask>): AuditTask => ({
    id,
    project_id: 'project-1',
    thread_id: null,
    category: 'Risk Assessment',
    status: 'Pending',
    risk_score: 5,
    assignees: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  })

  describe('State Management', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useTaskStore())

      expect(result.current.tasks).toEqual({})
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe(null)
      expect(result.current.subscriptions.size).toBe(0)
    })

    it('should clear tasks', () => {
      const { result } = renderHook(() => useTaskStore())

      act(() => {
        const task = createMockTask('task-1')
        useTaskStore.setState({ tasks: { [task.id]: task } })
      })

      expect(result.current.tasks).not.toEqual({})

      act(() => {
        result.current.clearTasks()
      })

      expect(result.current.tasks).toEqual({})
      expect(result.current.error).toBeNull()
    })

    it('should set error', () => {
      const { result } = renderHook(() => useTaskStore())

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

  describe('Task Management', () => {
    it('should add task to state', () => {
      const { result } = renderHook(() => useTaskStore())
      const task = createMockTask('task-1')

      act(() => {
        useTaskStore.setState((state) => ({
          tasks: { ...state.tasks, [task.id]: task },
        }))
      })

      expect(result.current.tasks['task-1']).toEqual(task)
      expect(Object.keys(result.current.tasks)).toHaveLength(1)
    })

    it('should update task in state', () => {
      const { result } = renderHook(() => useTaskStore())
      const task = createMockTask('task-1')

      act(() => {
        useTaskStore.setState({ tasks: { [task.id]: task } })
      })

      const updatedTask = {
        ...task,
        status: 'In Progress' as const,
      }

      act(() => {
        useTaskStore.setState((state) => ({
          tasks: { ...state.tasks, [task.id]: updatedTask },
        }))
      })

      expect(result.current.tasks['task-1'].status).toBe('In Progress')
    })

    it('should delete task from state', () => {
      const { result } = renderHook(() => useTaskStore())
      const task = createMockTask('task-1')

      act(() => {
        useTaskStore.setState({ tasks: { [task.id]: task } })
      })

      expect(result.current.tasks['task-1']).toBeDefined()

      act(() => {
        useTaskStore.setState((state) => {
          const newTasks = { ...state.tasks }
          delete newTasks['task-1']
          return { tasks: newTasks }
        })
      })

      expect(result.current.tasks['task-1']).toBeUndefined()
    })

    it('should handle multiple tasks', () => {
      const { result } = renderHook(() => useTaskStore())
      const task1 = createMockTask('task-1')
      const task2 = createMockTask('task-2')
      const task3 = createMockTask('task-3')

      act(() => {
        useTaskStore.setState({
          tasks: {
            [task1.id]: task1,
            [task2.id]: task2,
            [task3.id]: task3,
          },
        })
      })

      expect(Object.keys(result.current.tasks)).toHaveLength(3)
      expect(result.current.tasks['task-1']).toEqual(task1)
      expect(result.current.tasks['task-2']).toEqual(task2)
      expect(result.current.tasks['task-3']).toEqual(task3)
    })
  })

  describe('Subscription Management', () => {
    it('should store subscription cleanup function', () => {
      const { result } = renderHook(() => useTaskStore())
      const mockCleanup = vi.fn()

      act(() => {
        useTaskStore.setState({ subscriptions: new Map() })
        useTaskStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', mockCleanup),
        }))
      })

      expect(result.current.subscriptions.get('project-1')).toBe(mockCleanup)
    })

    it('should handle multiple subscriptions', () => {
      const { result } = renderHook(() => useTaskStore())
      const cleanup1 = vi.fn()
      const cleanup2 = vi.fn()

      act(() => {
        useTaskStore.setState({ subscriptions: new Map() })
        useTaskStore.setState((state) => ({
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
      const { result } = renderHook(() => useTaskStore())
      const cleanup = vi.fn()

      act(() => {
        useTaskStore.setState({ subscriptions: new Map() })
        useTaskStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('project-1', cleanup),
        }))
      })

      expect(result.current.subscriptions.size).toBe(1)

      act(() => {
        const newSubscriptions = new Map()
        useTaskStore.setState({ subscriptions: newSubscriptions })
      })

      expect(result.current.subscriptions.size).toBe(0)
    })
  })

  describe('Loading State', () => {
    it('should set loading state', () => {
      const { result } = renderHook(() => useTaskStore())

      act(() => {
        useTaskStore.setState({ loading: true })
      })

      expect(result.current.loading).toBe(true)

      act(() => {
        useTaskStore.setState({ loading: false })
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('Task Creation', () => {
    it('should handle task insert data structure', () => {
      const insertData: AuditTaskInsert = {
        project_id: 'project-1',
        category: 'Risk Assessment',
      }

      expect(insertData.project_id).toBe('project-1')
      expect(insertData.category).toBe('Risk Assessment')
    })
  })

  describe('Record Organization', () => {
    it('should organize tasks by ID in record structure', () => {
      const { result } = renderHook(() => useTaskStore())
      const task1 = createMockTask('task-1')
      const task2 = createMockTask('task-2')

      act(() => {
        useTaskStore.setState({
          tasks: {
            [task1.id]: task1,
            [task2.id]: task2,
          },
        })
      })

      const tasks = result.current.tasks
      expect(tasks['task-1']).toBe(task1)
      expect(tasks['task-2']).toBe(task2)
      expect(Object.keys(tasks)).toEqual(expect.arrayContaining(['task-1', 'task-2']))
    })
  })

  describe('Error Handling', () => {
    it('should handle error state', () => {
      const { result } = renderHook(() => useTaskStore())

      act(() => {
        result.current.setError('Database connection failed')
      })

      expect(result.current.error).toBe('Database connection failed')
    })

    it('should clear error state', () => {
      const { result } = renderHook(() => useTaskStore())

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

  describe('Task Status Updates', () => {
    it('should handle task status changes', () => {
      const { result } = renderHook(() => useTaskStore())
      const task = createMockTask('task-1', { status: 'Pending' })

      act(() => {
        useTaskStore.setState({ tasks: { [task.id]: task } })
      })

      expect(result.current.tasks['task-1'].status).toBe('Pending')

      const statusSequence: Array<'Pending' | 'In Progress' | 'Completed' | 'Blocked'> = [
        'Pending',
        'In Progress',
        'Completed',
      ]

      statusSequence.forEach((status) => {
        act(() => {
          const currentTask = result.current.tasks['task-1']
          useTaskStore.setState({
            tasks: {
              ...result.current.tasks,
              [task.id]: { ...currentTask, status },
            },
          })
        })

        expect(result.current.tasks['task-1'].status).toBe(status)
      })
    })
  })
})
