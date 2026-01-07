import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useStreamingChat } from '../useStreamingChat'
import { useChatStore } from '@/app/stores/useChatStore'
import { useArtifactStore } from '@/app/stores/useArtifactStore'

describe('useStreamingChat', () => {
  beforeEach(() => {
    // Clean up stores before each test
    useChatStore.getState().clearMessages()
    useArtifactStore.setState({
      artifacts: [],
      activeArtifactId: null,
      pinnedArtifactId: null,
      splitLayout: 'none',
      splitRatio: 0.4,
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Clean up stores after each test
    useChatStore.getState().clearMessages()
    useArtifactStore.setState({
      artifacts: [],
      activeArtifactId: null,
      pinnedArtifactId: null,
      splitLayout: 'none',
      splitRatio: 0.4,
    })
  })

  describe('Hook Initialization', () => {
    it('should initialize with correct default state', () => {
      const { result } = renderHook(() => useStreamingChat())

      expect(result.current.isStreaming).toBe(false)
      expect(typeof result.current.sendMessage).toBe('function')
    })
  })

  describe('Message Sending', () => {
    it('should add user message to chat store', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('Test message')
      })

      const messages = useChatStore.getState().messages
      const userMessage = messages.find((m) => m.sender === 'user')

      expect(userMessage).toBeDefined()
      expect(userMessage?.content).toBe('Test message')
    })

    it('should create AI message with streaming state', async () => {
      const { result } = renderHook(() => useStreamingChat())

      const promise = await act(async () => {
        await result.current.sendMessage('Test message')
      })

      // Check after completion
      const messages = useChatStore.getState().messages
      const aiMessage = messages.find((m) => m.sender === 'ai')
      expect(aiMessage).toBeDefined()
    })

    it('should update AI message after delay', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('dashboard')
      })

      const messages = useChatStore.getState().messages
      const aiMessage = messages.find((m) => m.sender === 'ai')

      expect(aiMessage).toBeDefined()
      expect(aiMessage?.streaming).toBe(false)
      expect(aiMessage?.content).toContain('dashboard overview')
    })

    it('should set isStreaming to true during execution', async () => {
      const { result } = renderHook(() => useStreamingChat())

      expect(result.current.isStreaming).toBe(false)

      // Start the send operation
      act(() => {
        result.current.sendMessage('Test')
      })

      // Wait for isStreaming to become true
      await waitFor(() => {
        expect(result.current.isStreaming).toBe(true)
      })

      // Wait for completion
      await waitFor(() => {
        expect(result.current.isStreaming).toBe(false)
      }, { timeout: 3000 })
    })

    it('should reset isStreaming after completion', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('Test')
      })

      expect(result.current.isStreaming).toBe(false)
    })
  })

  describe('Artifact Type Detection', () => {
    it('should detect dashboard artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('show me the dashboard')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts.length).toBeGreaterThan(0)
      expect(artifacts[0].artifact.type).toBe('dashboard')
    })

    it('should detect financial statements artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('show financial statements')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.type).toBe('financial-statements')
    })

    it('should detect issue details artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('show the issue')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.type).toBe('issue-details')
    })

    it('should detect task status artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('check task status')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.type).toBe('task-status')
    })

    it('should default to engagement plan for unknown queries', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('hello')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.type).toBe('engagement-plan')
    })
  })

  describe('Artifact Creation', () => {
    it('should create artifact with streaming status initially', async () => {
      const { result } = renderHook(() => useStreamingChat())

      act(() => {
        result.current.sendMessage('dashboard')
      })

      // Wait for artifact to be created
      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts
        expect(artifacts.length).toBeGreaterThan(0)
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.status).toBe('streaming')
    })

    it('should update artifact to complete status', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('dashboard')
      })

      const artifacts = useArtifactStore.getState().artifacts
      expect(artifacts[0].artifact.status).toBe('complete')
    })

    it('should link artifact to AI message', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('dashboard')
      })

      const messages = useChatStore.getState().messages
      const artifacts = useArtifactStore.getState().artifacts
      const aiMessage = messages.find((m) => m.sender === 'ai')

      expect(aiMessage?.artifactId).toBe(artifacts[0].artifact.id)
    })

    it('should generate correct artifact data for dashboard', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('dashboard')
      })

      const artifacts = useArtifactStore.getState().artifacts
      const dashboardData = artifacts[0].artifact.data as any

      expect(dashboardData.agents).toBeDefined()
      expect(dashboardData.tasks).toBeDefined()
      expect(dashboardData.riskHeatmap).toBeDefined()
    })
  })

  describe('Multiple Messages', () => {
    it('should handle multiple sequential messages', async () => {
      const { result } = renderHook(() => useStreamingChat())

      await act(async () => {
        await result.current.sendMessage('dashboard')
      })

      await act(async () => {
        await result.current.sendMessage('financial statements')
      })

      const messages = useChatStore.getState().messages
      const artifacts = useArtifactStore.getState().artifacts

      expect(messages.length).toBe(4) // 2 user + 2 AI
      expect(artifacts.length).toBe(2)
    })
  })
})
