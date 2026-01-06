import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DashboardArtifact } from '../DashboardArtifact';
import type { RiskLevel } from '../../../types/audit';

describe('DashboardArtifact', () => {
  const mockDashboardData = {
    agents: [
      {
        id: '1',
        name: 'Partner AI',
        role: 'partner' as const,
        status: 'working' as const,
        currentTask: 'Reviewing audit plan'
      }
    ],
    tasks: [
      {
        id: '1',
        status: 'completed' as const,
        riskLevel: 'high' as RiskLevel,
        phase: 'planning'
      }
    ],
    riskHeatmap: [
      {
        category: 'Revenue',
        process: 'Sales',
        riskScore: 75,
        riskLevel: 'high' as RiskLevel,
        taskCount: 10,
        completedTasks: 5
      }
    ]
  };

  it('should show Updating badge when status is streaming', () => {
    render(<DashboardArtifact data={mockDashboardData} status="streaming" />);

    const updatingBadge = screen.getByText(/updating/i);
    expect(updatingBadge).toBeInTheDocument();
    expect(updatingBadge.closest('div')).toHaveClass('bg-blue-100');
  });

  it('should show Complete badge when status is complete', () => {
    render(<DashboardArtifact data={mockDashboardData} status="complete" />);

    const badges = screen.getAllByText(/complete/i);
    const completeBadge = badges.find(el => el.closest('div')?.classList.contains('bg-green-100'));
    expect(completeBadge).toBeInTheDocument();
    expect(screen.queryByText(/updating/i)).not.toBeInTheDocument();
  });

  it('should show Error badge when status is error', () => {
    render(<DashboardArtifact data={mockDashboardData} status="error" />);

    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  it('should render all dashboard sections correctly', () => {
    render(<DashboardArtifact data={mockDashboardData} status="complete" />);

    expect(screen.getByText(/audit command center/i)).toBeInTheDocument();
    expect(screen.getByText(/overall progress/i)).toBeInTheDocument();
    expect(screen.getByText(/high risk issues/i)).toBeInTheDocument();
    expect(screen.getByText(/risk assessment heatmap/i)).toBeInTheDocument();
    expect(screen.getByText(/multi-agent hierarchy status/i)).toBeInTheDocument();
  });

  it('should handle empty data gracefully', () => {
    const emptyData = {
      agents: [],
      tasks: [],
      riskHeatmap: []
    };

    render(<DashboardArtifact data={emptyData} status="complete" />);

    expect(screen.getByText(/0%/)).toBeInTheDocument();
    expect(screen.getByText(/no agent data available/i)).toBeInTheDocument();
    expect(screen.getByText(/no risk data available/i)).toBeInTheDocument();
  });

  it('should handle status transitions correctly', () => {
    const mockData = { agents: [], tasks: [], riskHeatmap: [] };
    const { rerender } = render(<DashboardArtifact data={mockData} status="streaming" />);

    expect(screen.getByText(/updating/i)).toBeInTheDocument();

    rerender(<DashboardArtifact data={mockData} status="complete" />);

    expect(screen.queryByText(/updating/i)).not.toBeInTheDocument();
    const completeBadges = screen.getAllByText(/complete/i);
    const statusBadge = completeBadges.find(el => el.closest('div')?.classList.contains('bg-green-100'));
    expect(statusBadge).toBeInTheDocument();
  });
});
