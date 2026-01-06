import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IssueDetailsArtifact } from '../IssueDetailsArtifact';
import type { IssueImpact, IssueStatus } from '../../../types/audit';

describe('IssueDetailsArtifact', () => {
  const mockIssueData = {
    id: '1',
    taskNumber: 'T-001',
    title: 'Revenue Recognition Issue',
    accountCategory: 'Revenue',
    impact: 'high' as IssueImpact,
    status: 'open' as IssueStatus,
    identifiedBy: 'Staff AI 1',
    identifiedDate: '2025-01-15',
    financialImpact: 500000,
    description: 'Potential revenue recognition issue identified',
    requiresAdjustment: true,
    includeInManagementLetter: true
  };

  it('should show Updating badge when status is streaming', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="streaming" />);

    expect(screen.getByText(/updating/i)).toBeInTheDocument();
  });

  it('should show Complete badge when status is complete', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    const badges = screen.getAllByText(/complete/i);
    const completeBadge = badges.find(el => el.closest('div')?.classList.contains('bg-green-100'));
    expect(completeBadge).toBeInTheDocument();
  });

  it('should show Error badge when status is error', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="error" />);

    expect(screen.getByText(/error loading issue/i)).toBeInTheDocument();
  });

  it('should render issue header with impact badge', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    expect(screen.getByRole('heading', { name: /revenue recognition issue/i })).toBeInTheDocument();
    expect(screen.getByText(/high impact/i)).toBeInTheDocument();
    expect(screen.getByText(/t-001/i)).toBeInTheDocument();
  });

  it('should display issue description', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    expect(screen.getByText(/potential revenue recognition issue identified/i)).toBeInTheDocument();
  });

  it('should show adjustment required flag', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    expect(screen.getByText(/adjustment required/i)).toBeInTheDocument();
    expect(screen.getByText(/this issue requires financial statement adjustment/i)).toBeInTheDocument();
  });

  it('should show management letter inclusion flag', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    expect(screen.getByText(/include in management letter/i)).toBeInTheDocument();
    expect(screen.getByText(/this finding will be communicated to management/i)).toBeInTheDocument();
  });

  it('should render client response when available', () => {
    const dataWithResponse = {
      ...mockIssueData,
      status: 'client-responded' as IssueStatus,
      clientResponse: 'We will implement corrective actions',
      clientResponseDate: '2025-01-20'
    };

    render(<IssueDetailsArtifact data={dataWithResponse} status="complete" />);

    expect(screen.getByText(/client response/i)).toBeInTheDocument();
    expect(screen.getByText(/we will implement corrective actions/i)).toBeInTheDocument();
  });

  it('should render resolution when available', () => {
    const dataWithResolution = {
      ...mockIssueData,
      status: 'resolved' as IssueStatus,
      resolution: 'Client implemented corrective controls',
      resolvedDate: '2025-01-25'
    };

    render(<IssueDetailsArtifact data={dataWithResolution} status="complete" />);

    expect(screen.getByText(/resolution/i)).toBeInTheDocument();
    expect(screen.getByText(/client implemented corrective controls/i)).toBeInTheDocument();
  });

  it('should format financial impact correctly', () => {
    render(<IssueDetailsArtifact data={mockIssueData} status="complete" />);

    expect(screen.getByText(/₩500,000/)).toBeInTheDocument();
  });
});
