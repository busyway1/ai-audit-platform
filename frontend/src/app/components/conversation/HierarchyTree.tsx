/**
 * HierarchyTree Component
 *
 * Displays the 3-level audit hierarchy (Business Process -> FSLI -> EGA -> Tasks)
 * with expandable nodes, conversation counts, and filtering support.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { cn } from '../ui/utils';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  FileText,
  CheckSquare,
  Search,
  Filter,
} from 'lucide-react';
import type {
  HierarchyItem,
  HierarchyLevel,
  HierarchyFilter,
  HierarchyStatus,
} from '@/app/types/hierarchy';

// --- Types ---

interface HierarchyTreeProps {
  projectId: string;
  items: HierarchyItem[];
  selectedId: string | null;
  onSelect: (item: HierarchyItem) => void;
  loading?: boolean;
  error?: string;
}

interface TreeNodeProps {
  item: HierarchyItem;
  depth: number;
  selectedId: string | null;
  expandedIds: Set<string>;
  onSelect: (item: HierarchyItem) => void;
  onToggle: (id: string) => void;
}

// --- Helper Functions ---

const getLevelIcon = (
  level: HierarchyLevel,
  isExpanded: boolean
): React.ReactNode => {
  switch (level) {
    case 'high':
      return isExpanded ? (
        <FolderOpen className="w-4 h-4 text-blue-500" />
      ) : (
        <Folder className="w-4 h-4 text-blue-500" />
      );
    case 'mid':
      return isExpanded ? (
        <FolderOpen className="w-4 h-4 text-green-500" />
      ) : (
        <Folder className="w-4 h-4 text-green-500" />
      );
    case 'low':
      return <FileText className="w-4 h-4 text-orange-500" />;
    case 'task':
      return <CheckSquare className="w-4 h-4 text-purple-500" />;
    default:
      return <FileText className="w-4 h-4" />;
  }
};

const getStatusColor = (status: HierarchyStatus): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'in_progress':
      return 'bg-blue-100 text-blue-800';
    case 'pending_review':
      return 'bg-yellow-100 text-yellow-800';
    case 'blocked':
      return 'bg-red-100 text-red-800';
    case 'not_started':
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const filterItems = (
  items: HierarchyItem[],
  filter: HierarchyFilter
): HierarchyItem[] => {
  const result: HierarchyItem[] = [];

  for (const item of items) {
    // Recursively filter children
    const filteredChildren = item.children
      ? filterItems(item.children, filter)
      : undefined;

    // Check if item matches filter
    let matches = true;

    if (filter.levels && filter.levels.length > 0) {
      matches = matches && filter.levels.includes(item.level);
    }

    if (filter.statuses && filter.statuses.length > 0) {
      matches = matches && filter.statuses.includes(item.status);
    }

    if (filter.searchTerm) {
      const searchLower = filter.searchTerm.toLowerCase();
      matches =
        matches &&
        (item.name.toLowerCase().includes(searchLower) ||
          (item.refNo?.toLowerCase().includes(searchLower) ?? false));
    }

    if (!filter.showCompleted && item.status === 'completed') {
      matches = false;
    }

    if (filter.showOnlyWithConversations && item.conversationCount === 0) {
      matches = false;
    }

    // Include if matches or has matching children
    if (matches || (filteredChildren && filteredChildren.length > 0)) {
      result.push({
        ...item,
        children: filteredChildren,
      });
    }
  }

  return result;
};

// --- TreeNode Component ---

const TreeNode: React.FC<TreeNodeProps> = ({
  item,
  depth,
  selectedId,
  expandedIds,
  onSelect,
  onToggle,
}) => {
  const hasChildren = item.children && item.children.length > 0;
  const isExpanded = expandedIds.has(item.id);
  const isSelected = selectedId === item.id;

  const handleClick = useCallback(() => {
    onSelect(item);
  }, [item, onSelect]);

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggle(item.id);
    },
    [item.id, onToggle]
  );

  return (
    <div className="select-none">
      {/* Node Row */}
      <div
        className={cn(
          'flex items-center py-1.5 px-2 rounded-md cursor-pointer',
          'hover:bg-gray-100 transition-colors',
          isSelected && 'bg-blue-50 border border-blue-200'
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={handleClick}
        role="treeitem"
        aria-selected={isSelected}
        aria-expanded={hasChildren ? isExpanded : undefined}
      >
        {/* Expand/Collapse Toggle */}
        {hasChildren ? (
          <button
            className="p-0.5 hover:bg-gray-200 rounded mr-1"
            onClick={handleToggle}
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        ) : (
          <span className="w-5" /> // Spacer for alignment
        )}

        {/* Level Icon */}
        <span className="mr-2">{getLevelIcon(item.level, isExpanded)}</span>

        {/* Name */}
        <span className="flex-1 truncate text-sm font-medium">{item.name}</span>

        {/* Ref Number */}
        {item.refNo && (
          <span className="text-xs text-gray-400 mr-2">{item.refNo}</span>
        )}

        {/* Conversation Count Badge */}
        {item.conversationCount > 0 && (
          <Badge variant="secondary" className="ml-1 text-xs">
            {item.conversationCount}
          </Badge>
        )}

        {/* Status Badge */}
        <Badge
          className={cn('ml-2 text-xs capitalize', getStatusColor(item.status))}
        >
          {item.status.replace(/_/g, ' ')}
        </Badge>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div role="group">
          {item.children!.map((child) => (
            <TreeNode
              key={child.id}
              item={child}
              depth={depth + 1}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// --- Main HierarchyTree Component ---

export const HierarchyTree: React.FC<HierarchyTreeProps> = ({
  items,
  selectedId,
  onSelect,
  loading = false,
  error,
}) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<HierarchyFilter>({
    showCompleted: true,
  });
  const [searchTerm, setSearchTerm] = useState('');

  // Filter items based on current filter state
  const filteredItems = useMemo(() => {
    const currentFilter: HierarchyFilter = {
      ...filter,
      searchTerm,
    };
    return filterItems(items, currentFilter);
  }, [items, filter, searchTerm]);

  // Toggle expand/collapse
  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // Expand all
  const expandAll = useCallback(() => {
    const allIds = new Set<string>();
    const collectIds = (hierarchyItems: HierarchyItem[]) => {
      hierarchyItems.forEach((item) => {
        if (item.children && item.children.length > 0) {
          allIds.add(item.id);
          collectIds(item.children);
        }
      });
    };
    collectIds(items);
    setExpandedIds(allIds);
  }, [items]);

  // Collapse all
  const collapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  // Toggle completed filter
  const toggleShowCompleted = useCallback(() => {
    setFilter((prev) => ({
      ...prev,
      showCompleted: !prev.showCompleted,
    }));
  }, []);

  if (loading) {
    return (
      <div
        className="flex items-center justify-center h-64"
        role="status"
        aria-label="Loading"
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-500">
        <p>Error loading hierarchy: {error}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-3 border-b space-y-2">
        <h3 className="font-semibold text-sm">Audit Hierarchy</h3>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={expandAll}
            className="text-xs"
          >
            Expand All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={collapseAll}
            className="text-xs"
          >
            Collapse All
          </Button>
          <Button
            variant={filter.showCompleted ? 'ghost' : 'secondary'}
            size="sm"
            onClick={toggleShowCompleted}
            className="text-xs ml-auto"
          >
            <Filter className="w-3 h-3 mr-1" />
            {filter.showCompleted ? 'Hide Completed' : 'Show Completed'}
          </Button>
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto p-2" role="tree">
        {filteredItems.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            {searchTerm ? 'No results found' : 'No items'}
          </div>
        ) : (
          filteredItems.map((item) => (
            <TreeNode
              key={item.id}
              item={item}
              depth={0}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggle={handleToggle}
            />
          ))
        )}
      </div>

      {/* Summary Footer */}
      <div className="p-2 border-t text-xs text-gray-500">
        {filteredItems.length} / {items.length} items
      </div>
    </div>
  );
};

export default HierarchyTree;
