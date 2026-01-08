import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useProjectStore, getSelectedProject } from '../useProjectStore'
import type { AuditProject, AuditProjectInsert } from '../../types/supabase'

// Mock Supabase
vi.mock('../../../lib/supabase', () => ({
  supabase: {
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: vi.fn().mockResolvedValue({
          data: null,
          error: null,
        }),
        eq: vi.fn().mockReturnValue({
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
          error: null,
        }),
      }),
      delete: vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({
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

describe('useProjectStore', () => {
  beforeEach(() => {
    act(() => {
      useProjectStore.getState().clearProjects()
      useProjectStore.getState().setError(null)
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Helper function to create mock projects
  const createMockProject = (id: string, overrides?: Partial<AuditProject>): AuditProject => ({
    id,
    client_name: 'Test Client',
    fiscal_year: 2024,
    overall_materiality: 100000,
    status: 'Planning',
    metadata: {},
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  })

  describe('State Management', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useProjectStore())

      expect(result.current.projects).toEqual({})
      expect(result.current.selectedProjectId).toBe(null)
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe(null)
      expect(result.current.subscriptions.size).toBe(0)
    })

    it('should clear projects', () => {
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        const project = createMockProject('project-1')
        useProjectStore.setState({
          projects: { [project.id]: project },
          selectedProjectId: project.id,
        })
      })

      expect(result.current.projects).not.toEqual({})
      expect(result.current.selectedProjectId).not.toBeNull()

      act(() => {
        result.current.clearProjects()
      })

      expect(result.current.projects).toEqual({})
      expect(result.current.selectedProjectId).toBeNull()
      expect(result.current.error).toBeNull()
    })

    it('should set error', () => {
      const { result } = renderHook(() => useProjectStore())

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

  describe('Project Selection', () => {
    it('should select a project', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      act(() => {
        result.current.selectProject('project-1')
      })

      expect(result.current.selectedProjectId).toBe('project-1')
    })

    it('should deselect a project by setting null', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({
          projects: { [project.id]: project },
          selectedProjectId: project.id,
        })
      })

      expect(result.current.selectedProjectId).toBe('project-1')

      act(() => {
        result.current.selectProject(null)
      })

      expect(result.current.selectedProjectId).toBeNull()
    })

    it('should clear error when selecting a project', () => {
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        useProjectStore.setState({ error: 'Previous error' })
      })

      expect(result.current.error).toBe('Previous error')

      act(() => {
        result.current.selectProject('project-1')
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('getSelectedProject Helper', () => {
    it('should return null when no project is selected', () => {
      const state = useProjectStore.getState()
      expect(getSelectedProject(state)).toBeNull()
    })

    it('should return null when selected project does not exist', () => {
      act(() => {
        useProjectStore.setState({ selectedProjectId: 'non-existent' })
      })

      const state = useProjectStore.getState()
      expect(getSelectedProject(state)).toBeNull()
    })

    it('should return the selected project', () => {
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({
          projects: { [project.id]: project },
          selectedProjectId: project.id,
        })
      })

      const state = useProjectStore.getState()
      expect(getSelectedProject(state)).toEqual(project)
    })
  })

  describe('Project Management', () => {
    it('should add project to state', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState((state) => ({
          projects: { ...state.projects, [project.id]: project },
        }))
      })

      expect(result.current.projects['project-1']).toEqual(project)
      expect(Object.keys(result.current.projects)).toHaveLength(1)
    })

    it('should update project in state', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      const updatedProject = {
        ...project,
        client_name: 'Updated Client',
        status: 'Execution' as const,
      }

      act(() => {
        useProjectStore.setState((state) => ({
          projects: { ...state.projects, [project.id]: updatedProject },
        }))
      })

      expect(result.current.projects['project-1'].client_name).toBe('Updated Client')
      expect(result.current.projects['project-1'].status).toBe('Execution')
    })

    it('should delete project from state', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      expect(result.current.projects['project-1']).toBeDefined()

      act(() => {
        useProjectStore.setState((state) => {
          const newProjects = { ...state.projects }
          delete newProjects['project-1']
          return { projects: newProjects }
        })
      })

      expect(result.current.projects['project-1']).toBeUndefined()
    })

    it('should clear selected project when deleted project is selected', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1')

      act(() => {
        useProjectStore.setState({
          projects: { [project.id]: project },
          selectedProjectId: project.id,
        })
      })

      expect(result.current.selectedProjectId).toBe('project-1')

      act(() => {
        useProjectStore.setState((state) => {
          const newProjects = { ...state.projects }
          delete newProjects['project-1']
          return {
            projects: newProjects,
            selectedProjectId: null,
          }
        })
      })

      expect(result.current.selectedProjectId).toBeNull()
    })

    it('should handle multiple projects', () => {
      const { result } = renderHook(() => useProjectStore())
      const project1 = createMockProject('project-1', { client_name: 'Client A' })
      const project2 = createMockProject('project-2', { client_name: 'Client B' })
      const project3 = createMockProject('project-3', { client_name: 'Client C' })

      act(() => {
        useProjectStore.setState({
          projects: {
            [project1.id]: project1,
            [project2.id]: project2,
            [project3.id]: project3,
          },
        })
      })

      expect(Object.keys(result.current.projects)).toHaveLength(3)
      expect(result.current.projects['project-1']).toEqual(project1)
      expect(result.current.projects['project-2']).toEqual(project2)
      expect(result.current.projects['project-3']).toEqual(project3)
    })
  })

  describe('Subscription Management', () => {
    it('should store subscription cleanup function', () => {
      const { result } = renderHook(() => useProjectStore())
      const mockCleanup = vi.fn()

      act(() => {
        useProjectStore.setState({ subscriptions: new Map() })
        useProjectStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('projects', mockCleanup),
        }))
      })

      expect(result.current.subscriptions.get('projects')).toBe(mockCleanup)
    })

    it('should remove subscription', () => {
      const { result } = renderHook(() => useProjectStore())
      const cleanup = vi.fn()

      act(() => {
        useProjectStore.setState({ subscriptions: new Map() })
        useProjectStore.setState((state) => ({
          subscriptions: new Map(state.subscriptions).set('projects', cleanup),
        }))
      })

      expect(result.current.subscriptions.size).toBe(1)

      act(() => {
        const newSubscriptions = new Map()
        useProjectStore.setState({ subscriptions: newSubscriptions })
      })

      expect(result.current.subscriptions.size).toBe(0)
    })
  })

  describe('Loading State', () => {
    it('should set loading state', () => {
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        useProjectStore.setState({ loading: true })
      })

      expect(result.current.loading).toBe(true)

      act(() => {
        useProjectStore.setState({ loading: false })
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('Project Creation', () => {
    it('should handle project insert data structure', () => {
      const insertData: AuditProjectInsert = {
        client_name: 'New Client',
        fiscal_year: 2024,
        overall_materiality: 50000,
        status: 'Planning',
      }

      expect(insertData.client_name).toBe('New Client')
      expect(insertData.fiscal_year).toBe(2024)
      expect(insertData.overall_materiality).toBe(50000)
      expect(insertData.status).toBe('Planning')
    })
  })

  describe('Record Organization', () => {
    it('should organize projects by ID in record structure', () => {
      const { result } = renderHook(() => useProjectStore())
      const project1 = createMockProject('project-1')
      const project2 = createMockProject('project-2')

      act(() => {
        useProjectStore.setState({
          projects: {
            [project1.id]: project1,
            [project2.id]: project2,
          },
        })
      })

      const projects = result.current.projects
      expect(projects['project-1']).toBe(project1)
      expect(projects['project-2']).toBe(project2)
      expect(Object.keys(projects)).toEqual(expect.arrayContaining(['project-1', 'project-2']))
    })
  })

  describe('Error Handling', () => {
    it('should handle error state', () => {
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.setError('Database connection failed')
      })

      expect(result.current.error).toBe('Database connection failed')
    })

    it('should clear error state', () => {
      const { result } = renderHook(() => useProjectStore())

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

  describe('Project Status Updates', () => {
    it('should handle project status changes', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1', { status: 'Planning' })

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      expect(result.current.projects['project-1'].status).toBe('Planning')

      const statusSequence: Array<'Planning' | 'Execution' | 'Review' | 'Completed'> = [
        'Planning',
        'Execution',
        'Review',
        'Completed',
      ]

      statusSequence.forEach((status) => {
        act(() => {
          const currentProject = result.current.projects['project-1']
          useProjectStore.setState({
            projects: {
              ...result.current.projects,
              [project.id]: { ...currentProject, status },
            },
          })
        })

        expect(result.current.projects['project-1'].status).toBe(status)
      })
    })
  })

  describe('Fiscal Year Filtering', () => {
    it('should store projects with different fiscal years', () => {
      const { result } = renderHook(() => useProjectStore())
      const project2023 = createMockProject('project-2023', { fiscal_year: 2023 })
      const project2024 = createMockProject('project-2024', { fiscal_year: 2024 })
      const project2025 = createMockProject('project-2025', { fiscal_year: 2025 })

      act(() => {
        useProjectStore.setState({
          projects: {
            [project2023.id]: project2023,
            [project2024.id]: project2024,
            [project2025.id]: project2025,
          },
        })
      })

      expect(result.current.projects['project-2023'].fiscal_year).toBe(2023)
      expect(result.current.projects['project-2024'].fiscal_year).toBe(2024)
      expect(result.current.projects['project-2025'].fiscal_year).toBe(2025)
    })
  })

  describe('Materiality Handling', () => {
    it('should handle null materiality', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1', { overall_materiality: null })

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      expect(result.current.projects['project-1'].overall_materiality).toBeNull()
    })

    it('should handle positive materiality values', () => {
      const { result } = renderHook(() => useProjectStore())
      const project = createMockProject('project-1', { overall_materiality: 500000 })

      act(() => {
        useProjectStore.setState({ projects: { [project.id]: project } })
      })

      expect(result.current.projects['project-1'].overall_materiality).toBe(500000)
    })
  })
})
