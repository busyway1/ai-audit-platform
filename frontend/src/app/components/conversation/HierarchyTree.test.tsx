import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HierarchyTree } from './HierarchyTree';
import type { HierarchyItem } from '@/app/types/hierarchy';

const mockItems: HierarchyItem[] = [
  {
    id: '1',
    projectId: 'proj-1',
    level: 'high',
    name: 'Revenue Cycle',
    status: 'in_progress',
    conversationCount: 5,
    children: [
      {
        id: '1-1',
        projectId: 'proj-1',
        level: 'mid',
        parentId: '1',
        name: 'Trade Receivables',
        status: 'in_progress',
        conversationCount: 3,
        refNo: '1000-1000',
        children: [
          {
            id: '1-1-1',
            projectId: 'proj-1',
            level: 'low',
            parentId: '1-1',
            name: 'Bank Inquiry EGA',
            status: 'completed',
            conversationCount: 2,
          },
        ],
      },
    ],
  },
  {
    id: '2',
    projectId: 'proj-1',
    level: 'high',
    name: 'Purchase Cycle',
    status: 'not_started',
    conversationCount: 0,
  },
];

describe('HierarchyTree', () => {
  it('renders hierarchy items', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('Revenue Cycle')).toBeInTheDocument();
    expect(screen.getByText('Purchase Cycle')).toBeInTheDocument();
  });

  it('expands and collapses nodes', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    // Initially collapsed - children not visible
    expect(screen.queryByText('Trade Receivables')).not.toBeInTheDocument();

    // Click expand button (first button with aria-label containing 'Expand')
    const expandButtons = screen.getAllByRole('button', { name: /expand/i });
    fireEvent.click(expandButtons[0]);

    // Children now visible
    expect(screen.getByText('Trade Receivables')).toBeInTheDocument();
  });

  it('calls onSelect when item clicked', () => {
    const handleSelect = vi.fn();
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={handleSelect}
      />
    );

    fireEvent.click(screen.getByText('Revenue Cycle'));
    expect(handleSelect).toHaveBeenCalledWith(mockItems[0]);
  });

  it('highlights selected item', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId="1"
        onSelect={() => {}}
      />
    );

    const selectedItem = screen.getByText('Revenue Cycle').closest('div');
    expect(selectedItem).toHaveClass('bg-blue-50');
  });

  it('shows conversation count badges', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('5')).toBeInTheDocument(); // Revenue Cycle count
  });

  it('filters by search term', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'Purchase' } });

    expect(screen.getByText('Purchase Cycle')).toBeInTheDocument();
    expect(screen.queryByText('Revenue Cycle')).not.toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={[]}
        selectedId={null}
        onSelect={() => {}}
        loading={true}
      />
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows error state', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={[]}
        selectedId={null}
        onSelect={() => {}}
        error="Failed to load"
      />
    );

    expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
  });

  it('expands all when button clicked', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    fireEvent.click(screen.getByText('Expand All'));

    // All levels should be visible
    expect(screen.getByText('Trade Receivables')).toBeInTheDocument();
    expect(screen.getByText('Bank Inquiry EGA')).toBeInTheDocument();
  });

  it('collapses all when button clicked', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    // First expand all
    fireEvent.click(screen.getByText('Expand All'));
    expect(screen.getByText('Trade Receivables')).toBeInTheDocument();

    // Then collapse all
    fireEvent.click(screen.getByText('Collapse All'));
    expect(screen.queryByText('Trade Receivables')).not.toBeInTheDocument();
  });

  it('shows correct status badges', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('in progress')).toBeInTheDocument();
    expect(screen.getByText('not started')).toBeInTheDocument();
  });

  it('displays item count in footer', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('2 / 2 items')).toBeInTheDocument();
  });

  it('filters out completed items when toggle clicked', () => {
    const itemsWithCompleted: HierarchyItem[] = [
      {
        id: '1',
        projectId: 'proj-1',
        level: 'high',
        name: 'Completed Task',
        status: 'completed',
        conversationCount: 0,
      },
      {
        id: '2',
        projectId: 'proj-1',
        level: 'high',
        name: 'In Progress Task',
        status: 'in_progress',
        conversationCount: 0,
      },
    ];

    render(
      <HierarchyTree
        projectId="proj-1"
        items={itemsWithCompleted}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    // Both items visible initially
    expect(screen.getByText('Completed Task')).toBeInTheDocument();
    expect(screen.getByText('In Progress Task')).toBeInTheDocument();

    // Click hide completed button
    fireEvent.click(screen.getByText('Hide Completed'));

    // Completed item should be hidden
    expect(screen.queryByText('Completed Task')).not.toBeInTheDocument();
    expect(screen.getByText('In Progress Task')).toBeInTheDocument();
  });

  it('shows empty state when no items', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={[]}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('shows no results message when search has no matches', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'NonExistentItem' } });

    expect(screen.getByText('No results found')).toBeInTheDocument();
  });

  it('displays reference numbers when available', () => {
    render(
      <HierarchyTree
        projectId="proj-1"
        items={mockItems}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    // Expand to see nested items with refNo
    fireEvent.click(screen.getByText('Expand All'));

    expect(screen.getByText('1000-1000')).toBeInTheDocument();
  });
});
