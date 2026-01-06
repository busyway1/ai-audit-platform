import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EngagementPlanArtifact } from '../EngagementPlanArtifact';
import type { RiskLevel } from '../../../types/audit';

describe('EngagementPlanArtifact', () => {
  const mockEngagementData = {
    clientName: 'ABC Corporation',
    fiscalYear: 'FY 2025',
    auditPeriod: {
      start: '2025-01-01',
      end: '2025-12-31'
    },
    materiality: {
      overall: 1000000,
      performance: 750000,
      trivial: 50000
    },
    keyAuditMatters: [
      {
        id: '1',
        matter: 'Revenue Recognition',
        riskLevel: 'high' as RiskLevel,
        response: 'Detailed testing of revenue transactions'
      }
    ],
    timeline: [
      {
        phase: 'Planning',
        startDate: '2025-01-01',
        endDate: '2025-02-01',
        status: 'completed' as const
      }
    ],
    resources: {
      humanTeam: [
        { name: 'John Doe', role: 'Partner', allocation: '50%' }
      ],
      aiAgents: [
        { name: 'Partner AI', role: 'partner' as const, assignedTasks: 10 }
      ]
    },
    approvalStatus: 'approved' as const,
    approvedBy: 'John Doe',
    approvedAt: '2025-01-15'
  };

  it('should show Updating badge when status is streaming', () => {
    render(<EngagementPlanArtifact data={mockEngagementData} status="streaming" />);

    expect(screen.getByText(/updating/i)).toBeInTheDocument();
  });

  it('should show Error badge when status is error', () => {
    render(<EngagementPlanArtifact data={mockEngagementData} status="error" />);

    expect(screen.getByText(/error loading/i)).toBeInTheDocument();
  });

  it('should show Approved badge when status is complete and approved', () => {
    render(<EngagementPlanArtifact data={mockEngagementData} status="complete" />);

    const approvedElements = screen.getAllByText(/approved/i);
    const approvedBadge = approvedElements.find(el => el.classList.contains('font-medium'));
    expect(approvedBadge).toBeInTheDocument();
    expect(screen.getAllByText(/john doe/i).length).toBeGreaterThan(0);
  });

  it('should render all engagement plan sections', () => {
    render(<EngagementPlanArtifact data={mockEngagementData} status="complete" />);

    expect(screen.getByText(/engagement plan summary/i)).toBeInTheDocument();
    expect(screen.getByText(/client & engagement information/i)).toBeInTheDocument();
    expect(screen.getByText(/materiality thresholds/i)).toBeInTheDocument();
    expect(screen.getByText(/key audit matters/i)).toBeInTheDocument();
    expect(screen.getByText(/audit timeline/i)).toBeInTheDocument();
  });

  it('should handle null plan data gracefully', () => {
    render(<EngagementPlanArtifact data={null} status="complete" />);

    expect(screen.getByText(/no engagement plan data available/i)).toBeInTheDocument();
  });

  it('should display materiality values correctly', () => {
    render(<EngagementPlanArtifact data={mockEngagementData} status="complete" />);

    expect(screen.getByText(/₩1,000,000/)).toBeInTheDocument();
    expect(screen.getByText(/₩750,000/)).toBeInTheDocument();
    expect(screen.getByText(/₩50,000/)).toBeInTheDocument();
  });

  it('should consistently use streaming badge styles', () => {
    render(<EngagementPlanArtifact data={null} status="streaming" />);
    const engagementBadge = screen.getByText(/updating/i);

    expect(engagementBadge.closest('div')).toHaveClass('bg-blue-100');
  });
});
