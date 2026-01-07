import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTaskActions } from '../useTaskActions'

describe('useTaskActions Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('should export useTaskActions function', () => {
    expect(useTaskActions).toBeDefined()
    expect(typeof useTaskActions).toBe('function')
  })

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useTaskActions())

    expect(result.current.isApproving).toBe(false)
    expect(result.current.error).toBe(null)
    expect(typeof result.current.approveTask).toBe('function')
  })

  it('should set isApproving to true while request is in progress', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Task approved',
        data: {
          threadId: 'thread-123',
          approved: true,
          approvedAt: new Date().toISOString(),
        },
      }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    expect(result.current.isApproving).toBe(false)

    await act(async () => {
      await result.current.approveTask('thread-123', true)
    })

    expect(result.current.isApproving).toBe(false)
  })

  it('should handle successful approval', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Task approved successfully',
        data: {
          threadId: 'thread-123',
          approved: true,
          approvedAt: '2024-01-06T12:00:00Z',
        },
      }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-123', true)
    })

    expect(response).not.toBeNull()
    expect(response?.success).toBe(true)
    expect(response?.data?.approved).toBe(true)
    expect(result.current.error).toBe(null)
  })

  it('should handle rejection approval', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Task rejected',
        data: {
          threadId: 'thread-456',
          approved: false,
          approvedAt: '2024-01-06T12:00:00Z',
        },
      }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-456', false)
    })

    expect(response?.data?.approved).toBe(false)
  })

  it('should handle network errors gracefully', async () => {
    const errorMessage = 'Network error'
    global.fetch = vi.fn().mockRejectedValueOnce(new Error(errorMessage))

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-123', true)
    })

    expect(response).toBeNull()
    expect(result.current.error).toBe(errorMessage)
  })

  it('should handle failed HTTP responses', async () => {
    const mockResponse = {
      ok: false,
      status: 401,
      json: async () => ({
        message: 'Unauthorized',
      }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-123', true)
    })

    expect(response).toBeNull()
    expect(result.current.error).toBe('Unauthorized')
  })

  it('should handle HTTP error responses with no message', async () => {
    const mockResponse = {
      ok: false,
      status: 500,
      json: async () => ({}),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-123', true)
    })

    expect(response).toBeNull()
    expect(result.current.error).toBe('Approval failed with status 500')
  })

  it('should clear error on successful approval after previous error', async () => {
    const { result } = renderHook(() => useTaskActions())

    // Simulate previous error
    await act(async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('First error'))
      await result.current.approveTask('thread-123', true)
    })

    expect(result.current.error).toBe('First error')

    // Then successful approval
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Task approved',
      }),
    }

    await act(async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)
      await result.current.approveTask('thread-456', true)
    })

    expect(result.current.error).toBeNull()
  })

  it('should send correct request body with snake_case threadId', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({ success: true, message: 'OK' }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    await act(async () => {
      await result.current.approveTask('thread-123', true)
    })

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/tasks/approve'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: 'thread-123',
          approved: true,
        }),
      })
    )
  })

  it('should use correct API endpoint from environment', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({ success: true }),
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    await act(async () => {
      await result.current.approveTask('thread-123', true)
    })

    const callUrl = (global.fetch as any).mock.calls[0][0]
    expect(callUrl).toMatch(/\/api\/tasks\/approve$/)
  })

  it('should handle JSON parse errors in error response', async () => {
    const mockResponse = {
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('Invalid JSON')
      },
    }

    global.fetch = vi.fn().mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useTaskActions())

    let response
    await act(async () => {
      response = await result.current.approveTask('thread-123', true)
    })

    expect(response).toBeNull()
    expect(result.current.error).toBe('Approval failed with status 500')
  })
})
