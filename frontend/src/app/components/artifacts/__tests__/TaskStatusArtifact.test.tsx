import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TaskStatusArtifact } from '../TaskStatusArtifact';
import type { RiskLevel, TaskStatus } from '../../../types/audit';

describe('TaskStatusArtifact', () => {
  const mockTaskData = {
    task: {
      id: '1',
      taskNumber: 'T-001',
      title: 'Revenue Recognition Testing',
      description: 'Test revenue recognition controls',
      status: 'in-progress' as TaskStatus,
      phase: 'controls-testing' as const,
      accountCategory: 'Revenue',
      businessProcess: 'Sales',
      assignedManager: 'Manager AI',
      assignedStaff: ['Staff AI 1', 'Staff AI 2'],
      progress: 65,
      riskLevel: 'high' as RiskLevel,
      requiresReview: true,
      dueDate: '2025-02-01',
      createdAt: '2025-01-01'
    },
    messages: [
      {
        id: '1',
        taskId: '1',
        agentId: 'manager-1',
        agentName: 'Manager AI',
        agentRole: 'manager' as const,
        content: 'Starting revenue testing procedures',
        timestamp: '2025-01-15T10:00:00Z',
        type: 'instruction' as const
      },
      {
        id: '2',
        taskId: '1',
        agentId: 'staff-1',
        agentName: 'Staff AI 1',
        agentRole: 'staff' as const,
        content: 'Completed sample selection',
        timestamp: '2025-01-15T11:00:00Z',
        type: 'response' as const
      }
    ]
  };

  it('should show Updating badge when status is streaming', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="streaming" />);

    expect(screen.getByText(/updating/i)).toBeInTheDocument();
  });

  it('should show Complete badge when status is complete', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    const badges = screen.getAllByText(/complete/i);
    const completeBadge = badges.find(el => el.closest('div')?.classList.contains('bg-green-100'));
    expect(completeBadge).toBeInTheDocument();
  });

  it('should show Error badge when status is error', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="error" />);

    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  it('should render task header information', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/t-001/i)).toBeInTheDocument();
    expect(screen.getByText(/revenue recognition testing/i)).toBeInTheDocument();
    expect(screen.getByText(/test revenue recognition controls/i)).toBeInTheDocument();
  });

  it('should display task status badge', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
  });

  it('should show progress bar with correct percentage', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/65%/)).toBeInTheDocument();
  });

  it('should render agent interaction timeline', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/agent interaction timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/\(2 messages\)/i)).toBeInTheDocument();
    expect(screen.getByText(/manager ai/i)).toBeInTheDocument();
    expect(screen.getByText(/staff ai 1/i)).toBeInTheDocument();
  });

  it('should render message content correctly', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/starting revenue testing procedures/i)).toBeInTheDocument();
    expect(screen.getByText(/completed sample selection/i)).toBeInTheDocument();
  });

  it('should show review required flag when applicable', () => {
    render(<TaskStatusArtifact data={mockTaskData} status="complete" />);

    expect(screen.getByText(/review required/i)).toBeInTheDocument();
    expect(screen.getByText(/this task requires human review before completion/i)).toBeInTheDocument();
  });

  it('should handle empty messages gracefully', () => {
    const dataWithoutMessages = {
      ...mockTaskData,
      messages: []
    };

    render(<TaskStatusArtifact data={dataWithoutMessages} status="complete" />);

    expect(screen.getByText(/no agent interactions yet/i)).toBeInTheDocument();
    expect(screen.getByText(/agents will start working on this task soon/i)).toBeInTheDocument();
  });

  it('should render message attachments when present', () => {
    const dataWithAttachments = {
      ...mockTaskData,
      messages: [
        {
          ...mockTaskData.messages[0],
          attachments: [
            { name: 'sample-data.xlsx', type: 'spreadsheet' }
          ]
        }
      ]
    };

    render(<TaskStatusArtifact data={dataWithAttachments} status="complete" />);

    expect(screen.getByText(/sample-data.xlsx/i)).toBeInTheDocument();
  });
});
