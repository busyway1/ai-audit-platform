import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStreamingChat } from '../useStreamingChat';
import { useChatStore } from '@/app/stores/useChatStore';
import { useArtifactStore } from '@/app/stores/useArtifactStore';

// Mock nanoid to generate predictable IDs
let mockIdCounter = 0;
vi.mock('nanoid', () => ({
  nanoid: vi.fn(() => `mock-id-${mockIdCounter++}`),
}));

describe('useStreamingChat', () => {
  beforeEach(() => {
    mockIdCounter = 0;

    // Clear all stores before each test
    useChatStore.getState().clearMessages();
    useArtifactStore.setState({
      artifacts: [],
      activeArtifactId: null,
      pinnedArtifactId: null,
      splitLayout: 'none',
      splitRatio: 0.4,
    });

    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Artifact Type Detection', () => {
    it('should create dashboard artifact from "dashboard" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      // Act: Send message with "dashboard" keyword
      await result.current.sendMessage('Show me the dashboard');

      // Assert: Check artifact was created with correct type
      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('dashboard');
        expect(artifacts[0].artifact.title).toBe('Dashboard Overview');
      });

      const artifacts = useArtifactStore.getState().artifacts;
      const dashboardData = artifacts[0].artifact.data;

      // Assert: Verify data structure
      expect(dashboardData).toHaveProperty('agents');
      expect(dashboardData).toHaveProperty('tasks');
      expect(dashboardData).toHaveProperty('riskHeatmap');

      // Assert: Verify agents data
      expect(dashboardData.agents).toHaveLength(2);
      expect(dashboardData.agents?.[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
        role: expect.stringMatching(/^(partner|manager|staff)$/),
        status: expect.stringMatching(/^(working|idle)$/),
      });

      // Assert: Verify tasks data
      expect(dashboardData.tasks).toHaveLength(2);
      expect(dashboardData.tasks?.[0]).toMatchObject({
        id: expect.any(String),
        status: expect.stringMatching(/^(completed|in-progress|pending)$/),
        riskLevel: expect.stringMatching(/^(low|medium|high|critical)$/),
        phase: expect.any(String),
      });

      // Assert: Verify risk heatmap data
      expect(dashboardData.riskHeatmap).toHaveLength(2);
      expect(dashboardData.riskHeatmap?.[0]).toMatchObject({
        category: expect.any(String),
        process: expect.any(String),
        riskScore: expect.any(Number),
        riskLevel: expect.stringMatching(/^(low|medium|high|critical)$/),
        taskCount: expect.any(Number),
        completedTasks: expect.any(Number),
      });

      // Assert: Artifact status progression (streaming → complete)
      await waitFor(() => {
        const updatedArtifacts = useArtifactStore.getState().artifacts;
        expect(updatedArtifacts[0].artifact.status).toBe('complete');
      });
    }, 10000);

    it('should create financial-statements artifact from "financial" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show financial statements');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('financial-statements');
        expect(artifacts[0].artifact.title).toBe('Financial Statements Overview');
      });

      const artifacts = useArtifactStore.getState().artifacts;
      const fsData = artifacts[0].artifact.data;

      // Verify financial statements data structure
      expect(fsData).toHaveProperty('items');
      expect(fsData).toHaveProperty('selectedAccount');
      expect(fsData).toHaveProperty('relatedTasks');

      // Verify items data
      expect(fsData.items).toHaveLength(2);
      expect(fsData.items[0]).toMatchObject({
        id: expect.any(String),
        category: expect.any(String),
        account: expect.any(String),
        currentYear: expect.any(Number),
        priorYear: expect.any(Number),
        variance: expect.any(Number),
        variancePercent: expect.any(Number),
        taskCount: expect.any(Number),
        completedTasks: expect.any(Number),
        riskLevel: expect.stringMatching(/^(low|medium|high|critical)$/),
      });

      // Verify exact values for first item
      expect(fsData.items[0].category).toBe('Assets');
      expect(fsData.items[0].account).toBe('Cash and Equivalents');
      expect(fsData.items[0].currentYear).toBe(1500000);
      expect(fsData.items[0].priorYear).toBe(1200000);
      expect(fsData.items[0].variance).toBe(300000);
      expect(fsData.items[0].variancePercent).toBe(25.0);
    }, 10000);

    it('should create financial-statements artifact from "statement" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Analyze the statement of income');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts[0].artifact.type).toBe('financial-statements');
      });
    }, 10000);

    it('should create issue-details artifact from "issue" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show me issue details');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('issue-details');
        expect(artifacts[0].artifact.title).toBe('Issue Details');
      });

      const artifacts = useArtifactStore.getState().artifacts;
      const issueData = artifacts[0].artifact.data;

      // Verify issue data structure
      expect(issueData).toMatchObject({
        id: expect.any(String),
        taskId: expect.any(String),
        taskNumber: expect.any(String),
        title: expect.any(String),
        description: expect.any(String),
        accountCategory: expect.any(String),
        impact: expect.stringMatching(/^(low|medium|high|critical)$/),
        status: expect.stringMatching(/^(open|client-responded|resolved|waived)$/),
        identifiedBy: expect.any(String),
        identifiedDate: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        financialImpact: expect.any(Number),
        requiresAdjustment: expect.any(Boolean),
        includeInManagementLetter: expect.any(Boolean),
      });

      // Verify exact values
      expect(issueData.taskNumber).toBe('A-100');
      expect(issueData.title).toBe('Revenue Recognition Timing Issue');
      expect(issueData.impact).toBe('high');
      expect(issueData.status).toBe('open');
      expect(issueData.financialImpact).toBe(250000);
      expect(issueData.requiresAdjustment).toBe(true);
    }, 10000);

    it('should create task-status artifact from "task" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show task status');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('task-status');
        expect(artifacts[0].artifact.title).toBe('Task Status Details');
      });

      const artifacts = useArtifactStore.getState().artifacts;
      const taskData = artifacts[0].artifact.data;

      // Verify task data structure
      expect(taskData).toHaveProperty('task');
      expect(taskData).toHaveProperty('messages');

      // Verify task object
      expect(taskData.task).toMatchObject({
        id: expect.any(String),
        taskNumber: expect.any(String),
        title: expect.any(String),
        description: expect.any(String),
        status: expect.stringMatching(/^(not-started|in-progress|pending-review|completed|rejected)$/),
        phase: expect.stringMatching(/^(planning|risk-assessment|controls-testing|substantive-procedures|completion)$/),
        accountCategory: expect.any(String),
        businessProcess: expect.any(String),
        assignedManager: expect.any(String),
        assignedStaff: expect.any(Array),
        progress: expect.any(Number),
        riskLevel: expect.stringMatching(/^(low|medium|high|critical)$/),
        requiresReview: expect.any(Boolean),
        dueDate: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        createdAt: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      });

      // Verify messages array
      expect(taskData.messages).toHaveLength(2);
      expect(taskData.messages[0]).toMatchObject({
        id: expect.any(String),
        taskId: expect.any(String),
        agentId: expect.any(String),
        agentName: expect.any(String),
        agentRole: expect.stringMatching(/^(partner|manager|staff)$/),
        content: expect.any(String),
        timestamp: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/),
        type: expect.stringMatching(/^(instruction|response|tool-use|file-upload|human-feedback)$/),
      });

      // Verify exact values
      expect(taskData.task.taskNumber).toBe('A-100');
      expect(taskData.task.status).toBe('in-progress');
      expect(taskData.task.progress).toBe(65);
      expect(taskData.task.riskLevel).toBe('high');
    }, 10000);

    it('should create engagement-plan artifact from "engagement" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show engagement plan');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('engagement-plan');
        expect(artifacts[0].artifact.title).toBe('Engagement Plan');
      });

      const artifacts = useArtifactStore.getState().artifacts;
      const planData = artifacts[0].artifact.data;

      // Verify engagement plan data structure
      expect(planData).toMatchObject({
        clientName: expect.any(String),
        fiscalYear: expect.stringMatching(/^\d{4}$/),
        auditPeriod: {
          start: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
          end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        },
        materiality: {
          overall: expect.any(Number),
          performance: expect.any(Number),
          trivial: expect.any(Number),
        },
        keyAuditMatters: expect.any(Array),
        timeline: expect.any(Array),
        resources: {
          humanTeam: expect.any(Array),
          aiAgents: expect.any(Array),
        },
        approvalStatus: expect.stringMatching(/^(draft|pending-approval|approved|rejected)$/),
      });

      // Verify exact values
      expect(planData.clientName).toBe('Mock Client Corporation');
      expect(planData.fiscalYear).toBe('2024');
      expect(planData.materiality.overall).toBe(1000000);
      expect(planData.approvalStatus).toBe('draft');
    }, 10000);

    it('should create engagement-plan artifact from "plan" query', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Create a plan for the audit');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts[0].artifact.type).toBe('engagement-plan');
      });
    }, 10000);

    it('should default to engagement-plan for unmatched queries', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Tell me about the audit');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('engagement-plan');
      });
    }, 10000);

    it('should handle empty query with default artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('engagement-plan');
      });
    }, 10000);

    it('should prioritize first matching keyword when multiple keywords present', async () => {
      const { result } = renderHook(() => useStreamingChat());

      // "dashboard" appears before "task" in query
      await result.current.sendMessage('Show dashboard with task status');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts[0].artifact.type).toBe('dashboard');
      });
    }, 10000);
  });

  describe('Streaming Workflow', () => {
    it('should add user message to chat store', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Test message');

      const messages = useChatStore.getState().messages;
      const userMessage = messages.find(m => m.sender === 'user');

      expect(userMessage).toBeDefined();
      expect(userMessage?.content).toBe('Test message');
      expect(userMessage?.sender).toBe('user');
      expect(userMessage?.timestamp).toBeInstanceOf(Date);
    }, 10000);

    it('should create AI message with streaming state initially', async () => {
      const { result } = renderHook(() => useStreamingChat());

      const promise = result.current.sendMessage('Test message');

      // Check immediately after sending (before stream completes)
      await waitFor(() => {
        const messages = useChatStore.getState().messages;
        const aiMessage = messages.find(m => m.sender === 'ai');
        expect(aiMessage).toBeDefined();
      });

      await promise;
    }, 10000);

    it('should create artifact in artifact store', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact).toBeDefined();
        expect(artifacts[0].artifact.id).toBeTruthy();
        expect(artifacts[0].artifact.createdAt).toBeInstanceOf(Date);
      });
    }, 10000);

    it('should update AI message with final content and artifact reference', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');

      await waitFor(() => {
        const messages = useChatStore.getState().messages;
        const aiMessage = messages.find(m => m.sender === 'ai');

        expect(aiMessage?.streaming).toBe(false);
        expect(aiMessage?.content).toBe("I've created a dashboard overview for you. Check the artifact panel →");
        expect(aiMessage?.artifactId).toBeTruthy();
      });

      // Verify artifact ID matches
      const messages = useChatStore.getState().messages;
      const artifacts = useArtifactStore.getState().artifacts;
      const aiMessage = messages.find(m => m.sender === 'ai');
      expect(aiMessage?.artifactId).toBe(artifacts[0].artifact.id);
    }, 10000);

    it('should mark artifact as complete after delay', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts[0].artifact.status).toBe('complete');
      });
    }, 10000);

    it('should handle complete workflow sequence', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show financial statements');

      await waitFor(() => {
        const messages = useChatStore.getState().messages;
        const artifacts = useArtifactStore.getState().artifacts;

        // Verify complete workflow
        expect(messages).toHaveLength(2); // User + AI message
        expect(messages[0].sender).toBe('user');
        expect(messages[1].sender).toBe('ai');
        expect(messages[1].streaming).toBe(false);
        expect(messages[1].artifactId).toBe(artifacts[0].artifact.id);

        expect(artifacts).toHaveLength(1);
        expect(artifacts[0].artifact.type).toBe('financial-statements');
        expect(artifacts[0].artifact.status).toBe('complete');
      });
    }, 10000);
  });

  describe('Store Integration', () => {
    it('should call useChatStore.addMessage for user and AI messages', async () => {
      const addMessageSpy = vi.spyOn(useChatStore.getState(), 'addMessage');
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Test');

      expect(addMessageSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          sender: 'user',
          content: 'Test',
        })
      );
      expect(addMessageSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          sender: 'ai',
          streaming: true,
        })
      );
    }, 10000);

    it('should call useChatStore.updateMessage for AI message finalization', async () => {
      const updateMessageSpy = vi.spyOn(useChatStore.getState(), 'updateMessage');
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show issue');

      expect(updateMessageSpy).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          streaming: false,
          artifactId: expect.any(String),
          content: "I've documented the issue details. Check the artifact panel →",
        })
      );
    }, 10000);

    it('should call useArtifactStore.addArtifact with correct artifact', async () => {
      const addArtifactSpy = vi.spyOn(useArtifactStore.getState(), 'addArtifact');
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show task status');

      expect(addArtifactSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'task-status',
          status: 'streaming',
        })
      );
    }, 10000);

    it('should call useArtifactStore.updateArtifact to mark complete', async () => {
      const updateArtifactSpy = vi.spyOn(useArtifactStore.getState(), 'updateArtifact');
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');

      await waitFor(() => {
        expect(updateArtifactSpy).toHaveBeenCalledWith(expect.any(String), { status: 'complete' });
      });
    }, 10000);
  });

  describe('Edge Cases', () => {
    it('should handle case-insensitive keyword matching', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('SHOW DASHBOARD');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts[0].artifact.type).toBe('dashboard');
      });
    }, 10000);

    it('should generate unique IDs for each artifact', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');
      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(1);
      });

      await result.current.sendMessage('Show issue');
      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        expect(artifacts).toHaveLength(2);
      });

      const artifacts = useArtifactStore.getState().artifacts;
      expect(artifacts[0].artifact.id).not.toBe(artifacts[1].artifact.id);
    }, 10000);

    it('should set artifact as active when added', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show dashboard');

      await waitFor(() => {
        const { activeArtifactId, artifacts } = useArtifactStore.getState();
        expect(activeArtifactId).toBe(artifacts[0].artifact.id);
      });
    }, 10000);

    it('should create different AI responses for each artifact type', async () => {
      const { result } = renderHook(() => useStreamingChat());

      const queries = [
        { query: 'Show dashboard', expected: "I've created a dashboard overview for you. Check the artifact panel →" },
        {
          query: 'Show financial',
          expected: "I've prepared the financial statements analysis. Check the artifact panel →",
        },
        { query: 'Show issue', expected: "I've documented the issue details. Check the artifact panel →" },
        {
          query: 'Show task',
          expected: "I've retrieved the task status and agent messages. Check the artifact panel →",
        },
        { query: 'Show plan', expected: "I've created an engagement plan for you. Check the artifact panel →" },
      ];

      for (const { query, expected } of queries) {
        useChatStore.getState().clearMessages();

        await result.current.sendMessage(query);

        await waitFor(() => {
          const messages = useChatStore.getState().messages;
          const aiMessage = messages.find(m => m.sender === 'ai');
          expect(aiMessage?.content).toBe(expected);
        });
      }
    }, 15000);
  });

  describe('Mock Data Validation', () => {
    it('should generate realistic dates in ISO format', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show engagement plan');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        const planData = artifacts[0].artifact.data;

        // Verify date formats
        expect(planData.auditPeriod.start).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(planData.auditPeriod.end).toMatch(/^\d{4}-\d{2}-\d{2}$/);

        // Verify createdAt and updatedAt are Date objects
        expect(artifacts[0].artifact.createdAt).toBeInstanceOf(Date);
        expect(artifacts[0].artifact.updatedAt).toBeInstanceOf(Date);
      });
    }, 10000);

    it('should generate realistic numeric values', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show financial statements');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        const fsData = artifacts[0].artifact.data;

        // Verify all numeric fields are numbers
        expect(fsData.items[0].currentYear).toBeGreaterThan(0);
        expect(fsData.items[0].priorYear).toBeGreaterThan(0);
        expect(fsData.items[0].variance).toBeDefined();
        expect(fsData.items[0].variancePercent).toBeDefined();

        // Verify variance calculation is correct
        const item = fsData.items[0];
        expect(item.variance).toBe(item.currentYear - item.priorYear);
      });
    }, 10000);

    it('should generate valid enum values for all fields', async () => {
      const { result } = renderHook(() => useStreamingChat());

      await result.current.sendMessage('Show task status');

      await waitFor(() => {
        const artifacts = useArtifactStore.getState().artifacts;
        const taskData = artifacts[0].artifact.data;

        // Verify all enums are valid
        expect(['not-started', 'in-progress', 'pending-review', 'completed', 'rejected']).toContain(
          taskData.task.status
        );
        expect(['planning', 'risk-assessment', 'controls-testing', 'substantive-procedures', 'completion']).toContain(
          taskData.task.phase
        );
        expect(['low', 'medium', 'high', 'critical']).toContain(taskData.task.riskLevel);
        expect(['partner', 'manager', 'staff']).toContain(taskData.messages[0].agentRole);
        expect(['instruction', 'response', 'tool-use', 'file-upload', 'human-feedback']).toContain(
          taskData.messages[0].type
        );
      });
    }, 10000);
  });
});
