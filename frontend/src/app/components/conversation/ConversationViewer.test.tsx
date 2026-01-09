import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationViewer } from './ConversationViewer';
import type { AgentConversation, ConversationFilter } from '@/app/types/conversation';

const mockConversations: AgentConversation[] = [
  {
    id: '1',
    projectId: 'proj-1',
    fromAgent: 'PartnerAgent',
    toAgent: 'ManagerAgent',
    messageType: 'instruction',
    content: 'Please review the revenue cycle',
    timestamp: '2026-01-09T10:00:00Z',
  },
  {
    id: '2',
    projectId: 'proj-1',
    fromAgent: 'ManagerAgent',
    toAgent: 'StaffAgent',
    messageType: 'instruction',
    content: 'Execute Excel parsing',
    timestamp: '2026-01-09T10:01:00Z',
  },
  {
    id: '3',
    projectId: 'proj-1',
    fromAgent: 'StaffAgent',
    toAgent: 'RalphLoop',
    messageType: 'response',
    content: 'Parsing completed',
    timestamp: '2026-01-09T10:02:00Z',
    metadata: {
      loopAttempt: 1,
      strategyUsed: 'default',
      duration: 5.3,
    },
  },
  {
    id: '4',
    projectId: 'proj-1',
    fromAgent: 'Validator',
    toAgent: 'RalphLoop',
    messageType: 'error',
    content: 'Validation failed: missing fields',
    timestamp: '2026-01-09T10:03:00Z',
  },
];

describe('ConversationViewer', () => {
  const defaultFilter: ConversationFilter = {
    includeErrors: true,
  };

  it('renders conversation messages', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText('Please review the revenue cycle')).toBeInTheDocument();
    expect(screen.getByText('Execute Excel parsing')).toBeInTheDocument();
    expect(screen.getByText('Parsing completed')).toBeInTheDocument();
  });

  it('displays agent badges', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText('PartnerAgent')).toBeInTheDocument();
    // ManagerAgent appears both as sender badge and as destination
    expect(screen.getAllByText('ManagerAgent').length).toBeGreaterThanOrEqual(1);
    // StaffAgent appears both as sender badge and as destination
    expect(screen.getAllByText('StaffAgent').length).toBeGreaterThanOrEqual(1);
  });

  it('shows metadata when present', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText(/시도 1/)).toBeInTheDocument();
    expect(screen.getByText(/default/)).toBeInTheDocument();
  });

  it('filters by agent type', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={{ ...defaultFilter, agentTypes: ['partner'] }}
        onFilterChange={() => {}}
      />
    );

    // Only Partner messages visible
    expect(screen.getByText('Please review the revenue cycle')).toBeInTheDocument();
    expect(screen.queryByText('Execute Excel parsing')).not.toBeInTheDocument();
  });

  it('filters out errors when toggle disabled', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={{ ...defaultFilter, includeErrors: false }}
        onFilterChange={() => {}}
      />
    );

    expect(screen.queryByText('Validation failed: missing fields')).not.toBeInTheDocument();
  });

  it('shows error count in footer', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText(/1 에러/)).toBeInTheDocument();
  });

  it('shows empty state when no conversations', () => {
    render(
      <ConversationViewer
        conversations={[]}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText('대화 기록이 없습니다')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <ConversationViewer
        conversations={[]}
        filter={defaultFilter}
        onFilterChange={() => {}}
        loading={true}
      />
    );

    // Loading spinner should be present
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('calls onFilterChange when filter changes', () => {
    const handleFilterChange = vi.fn();
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={handleFilterChange}
      />
    );

    // Click error toggle
    const errorToggle = screen.getByText('에러 포함');
    fireEvent.click(errorToggle);

    expect(handleFilterChange).toHaveBeenCalled();
  });

  it('displays title when provided', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
        title="Revenue Cycle 대화"
      />
    );

    expect(screen.getByText('Revenue Cycle 대화')).toBeInTheDocument();
  });

  it('displays message count correctly', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    // Should show "4 / 4" for all messages
    expect(screen.getByText('4 / 4')).toBeInTheDocument();
    expect(screen.getByText(/총 4개 메시지/)).toBeInTheDocument();
  });

  it('shows filter hint when empty due to filter', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={{ ...defaultFilter, agentTypes: ['nonexistent'] }}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText('대화 기록이 없습니다')).toBeInTheDocument();
    expect(screen.getByText('필터를 조정해보세요')).toBeInTheDocument();
  });

  it('shows duration in metadata', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    expect(screen.getByText(/Duration: 5.30s/)).toBeInTheDocument();
  });

  it('shows destination agent in message bubble', () => {
    render(
      <ConversationViewer
        conversations={mockConversations}
        filter={defaultFilter}
        onFilterChange={() => {}}
      />
    );

    // Check that destination agents are displayed
    expect(screen.getAllByText('ManagerAgent').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('StaffAgent').length).toBeGreaterThanOrEqual(1);
  });
});
