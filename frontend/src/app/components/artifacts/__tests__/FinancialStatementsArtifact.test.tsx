import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FinancialStatementsArtifact } from '../FinancialStatementsArtifact';
import type { RiskLevel, TaskStatus, AuditPhase } from '../../../types/audit';

describe('FinancialStatementsArtifact', () => {
  const mockFinancialData = {
    items: [
      {
        id: '1',
        category: 'Assets',
        account: 'Cash and Cash Equivalents',
        currentYear: 1000000,
        priorYear: 900000,
        variance: 100000,
        variancePercent: 11.1,
        taskCount: 5,
        completedTasks: 3,
        riskLevel: 'medium' as RiskLevel
      },
      {
        id: '2',
        category: 'Liabilities',
        account: 'Accounts Payable',
        currentYear: 500000,
        priorYear: 450000,
        variance: 50000,
        variancePercent: 11.1,
        taskCount: 3,
        completedTasks: 3,
        riskLevel: 'low' as RiskLevel
      }
    ],
    selectedAccount: null,
    relatedTasks: []
  };

  it('should show Updating badge when status is streaming', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="streaming" />);

    expect(screen.getByText(/updating financial statements/i)).toBeInTheDocument();
  });

  it('should show Complete badge when status is complete', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="complete" />);

    expect(screen.getByText(/analysis complete/i)).toBeInTheDocument();
  });

  it('should show Error badge when status is error', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="error" />);

    expect(screen.getByText(/error loading statements/i)).toBeInTheDocument();
  });

  it('should render financial statement sections', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="complete" />);

    expect(screen.getByText(/statement of financial position/i)).toBeInTheDocument();
    expect(screen.getByText(/cash and cash equivalents/i)).toBeInTheDocument();
    expect(screen.getByText(/accounts payable/i)).toBeInTheDocument();
  });

  it('should display task progress correctly', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="complete" />);

    expect(screen.getByText(/\(3\/5\)/)).toBeInTheDocument();
    expect(screen.getByText(/\(3\/3\)/)).toBeInTheDocument();
  });

  it('should show variance indicators', () => {
    render(<FinancialStatementsArtifact data={mockFinancialData} status="complete" />);

    const varianceElements = screen.getAllByText(/11.1%/);
    expect(varianceElements.length).toBeGreaterThan(0);
  });

  it('should render related tasks when selectedAccount exists', () => {
    const dataWithTasks = {
      ...mockFinancialData,
      selectedAccount: mockFinancialData.items[0],
      relatedTasks: [
        {
          id: '1',
          taskNumber: 'T-001',
          title: 'Cash Count',
          description: 'Physical cash count',
          status: 'in-progress' as TaskStatus,
          phase: 'substantive-procedures' as AuditPhase,
          accountCategory: 'Assets',
          businessProcess: 'Cash Management',
          assignedManager: 'Manager AI',
          assignedStaff: ['Staff AI 1'],
          progress: 75,
          riskLevel: 'medium' as RiskLevel,
          requiresReview: true,
          dueDate: '2025-01-20',
          createdAt: '2025-01-10'
        }
      ]
    };

    render(<FinancialStatementsArtifact data={dataWithTasks} status="complete" />);

    expect(screen.getByText(/related audit tasks/i)).toBeInTheDocument();
    expect(screen.getAllByText(/cash count/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/review required/i).length).toBeGreaterThan(0);
  });
});
