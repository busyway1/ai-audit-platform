"use client";

import { useState, useEffect, useMemo, useCallback, memo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  ListTodo,
  Search,
  Filter,
  FolderTree,
  FileText,
  CheckSquare,
  ExpandIcon,
  MinimizeIcon
} from 'lucide-react';
import { useTaskStore } from '../../stores/useTaskStore';
import { useProjectStore, getSelectedProject } from '../../stores/useProjectStore';
import { cn } from '../ui/utils';
import type { AuditTask, AuditTaskStatus, Json } from '../../types/supabase';

// Task levels for the 3-level hierarchy
type TaskLevel = 'High' | 'Mid' | 'Low';

// Extended task type with hierarchy info from metadata
interface HierarchicalTask extends AuditTask {
  task_level: TaskLevel;
  parent_task_id: string | null;
  name: string;
  description?: string;
}

// Tree node for rendering
interface TaskTreeNode {
  task: HierarchicalTask;
  children: TaskTreeNode[];
}

interface TaskHierarchyTreeProps {
  onSelectTask?: (task: HierarchicalTask) => void;
  selectedTaskId?: string;
}

// Extract hierarchical info from task metadata
function extractHierarchicalTask(task: AuditTask): HierarchicalTask {
  const metadata = task.metadata as Record<string, Json> | null;
  return {
    ...task,
    task_level: (metadata?.task_level as TaskLevel) || 'High',
    parent_task_id: (metadata?.parent_task_id as string) || null,
    name: (metadata?.name as string) || task.category || 'Unnamed Task',
    description: metadata?.description as string | undefined,
  };
}

// Build tree structure from flat list
function buildTaskTree(tasks: HierarchicalTask[]): TaskTreeNode[] {
  const taskMap = new Map<string, TaskTreeNode>();
  const rootNodes: TaskTreeNode[] = [];

  // First pass: create all nodes
  tasks.forEach(task => {
    taskMap.set(task.id, { task, children: [] });
  });

  // Second pass: build parent-child relationships
  tasks.forEach(task => {
    const node = taskMap.get(task.id)!;
    if (task.parent_task_id && taskMap.has(task.parent_task_id)) {
      taskMap.get(task.parent_task_id)!.children.push(node);
    } else {
      rootNodes.push(node);
    }
  });

  // Sort children by creation date
  const sortChildren = (nodes: TaskTreeNode[]) => {
    nodes.sort((a, b) =>
      new Date(a.task.created_at).getTime() - new Date(b.task.created_at).getTime()
    );
    nodes.forEach(node => sortChildren(node.children));
  };
  sortChildren(rootNodes);

  return rootNodes;
}

// Status helpers
const getStatusStyles = (status: AuditTaskStatus) => {
  switch (status) {
    case 'Completed':
      return 'bg-green-100 text-green-700';
    case 'In-Progress':
      return 'bg-blue-100 text-blue-700';
    case 'Review-Required':
      return 'bg-amber-100 text-amber-700';
    case 'Failed':
      return 'bg-red-100 text-red-700';
    case 'Pending':
    default:
      return 'bg-gray-100 text-gray-700';
  }
};

const getStatusIcon = (status: AuditTaskStatus) => {
  switch (status) {
    case 'Completed':
      return <CheckCircle2 className="size-3.5" />;
    case 'In-Progress':
      return <Clock className="size-3.5" />;
    case 'Review-Required':
      return <AlertCircle className="size-3.5" />;
    case 'Failed':
      return <XCircle className="size-3.5" />;
    case 'Pending':
    default:
      return <ListTodo className="size-3.5" />;
  }
};

// Level indicator styles
const getLevelStyles = (level: TaskLevel) => {
  switch (level) {
    case 'High':
      return {
        bg: 'bg-purple-50',
        border: 'border-purple-200 hover:border-purple-300',
        badge: 'bg-purple-100 text-purple-700',
        icon: <FolderTree className="size-4 text-purple-600" />,
      };
    case 'Mid':
      return {
        bg: 'bg-blue-50',
        border: 'border-blue-200 hover:border-blue-300',
        badge: 'bg-blue-100 text-blue-700',
        icon: <FileText className="size-4 text-blue-600" />,
      };
    case 'Low':
      return {
        bg: 'bg-gray-50',
        border: 'border-gray-200 hover:border-gray-300',
        badge: 'bg-gray-100 text-gray-700',
        icon: <CheckSquare className="size-4 text-gray-600" />,
      };
  }
};

// Memoized task node component for performance
interface TaskNodeProps {
  node: TaskTreeNode;
  depth: number;
  selectedTaskId?: string;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect?: (task: HierarchicalTask) => void;
}

const TaskNode = memo(function TaskNode({
  node,
  depth,
  selectedTaskId,
  expandedIds,
  onToggle,
  onSelect,
}: TaskNodeProps) {
  const { task, children } = node;
  const hasChildren = children.length > 0;
  const isExpanded = expandedIds.has(task.id);
  const isSelected = selectedTaskId === task.id;

  const levelStyles = getLevelStyles(task.task_level);

  const handleToggle = useCallback(() => {
    if (hasChildren) {
      onToggle(task.id);
    }
  }, [hasChildren, onToggle, task.id]);

  const handleSelect = useCallback(() => {
    onSelect?.(task);
  }, [onSelect, task]);

  return (
    <div className="select-none">
      <div
        className={cn(
          'flex items-center gap-2 p-2 rounded-lg border transition-all cursor-pointer',
          levelStyles.border,
          isSelected && 'ring-2 ring-blue-400 border-blue-400',
          !isSelected && levelStyles.bg
        )}
        style={{ marginLeft: `${depth * 24}px` }}
        onClick={handleSelect}
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelected}
      >
        {/* Expand/Collapse Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleToggle();
          }}
          className={cn(
            'p-0.5 rounded hover:bg-black/5 transition-colors',
            !hasChildren && 'invisible'
          )}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? (
            <ChevronDown className="size-4 text-gray-500" />
          ) : (
            <ChevronRight className="size-4 text-gray-500" />
          )}
        </button>

        {/* Level Icon */}
        {levelStyles.icon}

        {/* Task Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{task.name}</span>
            <span className={cn(
              'px-1.5 py-0.5 rounded text-xs font-medium shrink-0',
              levelStyles.badge
            )}>
              {task.task_level}
            </span>
          </div>
          {task.description && (
            <p className="text-xs text-gray-500 truncate mt-0.5">
              {task.description}
            </p>
          )}
        </div>

        {/* Status Badge */}
        <div className={cn(
          'flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium shrink-0',
          getStatusStyles(task.status)
        )}>
          {getStatusIcon(task.status)}
          <span>{task.status.replace('-', ' ')}</span>
        </div>

        {/* Risk Score */}
        {task.risk_score !== null && (
          <div className="text-xs text-gray-500 shrink-0">
            Risk: {task.risk_score}%
          </div>
        )}

        {/* Child Count */}
        {hasChildren && (
          <div className="text-xs text-gray-400 shrink-0">
            ({children.length})
          </div>
        )}
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div className="mt-1 space-y-1">
          {children.map(child => (
            <TaskNode
              key={child.task.id}
              node={child}
              depth={depth + 1}
              selectedTaskId={selectedTaskId}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
});

export function TaskHierarchyTree({ onSelectTask, selectedTaskId }: TaskHierarchyTreeProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<AuditTaskStatus | 'all'>('all');
  const [filterLevel, setFilterLevel] = useState<TaskLevel | 'all'>('all');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const { tasks, loading, error, fetchTasks, subscribeToUpdates, unsubscribeFromUpdates } = useTaskStore();
  const selectedProject = useProjectStore(getSelectedProject);

  // Fetch tasks when project changes
  useEffect(() => {
    if (selectedProject?.id) {
      fetchTasks(selectedProject.id);
      const cleanup = subscribeToUpdates(selectedProject.id);
      return () => {
        cleanup();
        unsubscribeFromUpdates(selectedProject.id);
      };
    }
  }, [selectedProject?.id, fetchTasks, subscribeToUpdates, unsubscribeFromUpdates]);

  // Convert tasks to hierarchical format
  const hierarchicalTasks = useMemo(() => {
    return Object.values(tasks).map(extractHierarchicalTask);
  }, [tasks]);

  // Filter tasks
  const filteredTasks = useMemo(() => {
    return hierarchicalTasks.filter(task => {
      const matchesSearch = searchQuery === '' ||
        task.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.category.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = filterStatus === 'all' || task.status === filterStatus;
      const matchesLevel = filterLevel === 'all' || task.task_level === filterLevel;
      return matchesSearch && matchesStatus && matchesLevel;
    });
  }, [hierarchicalTasks, searchQuery, filterStatus, filterLevel]);

  // Build tree structure
  const taskTree = useMemo(() => {
    return buildTaskTree(filteredTasks);
  }, [filteredTasks]);

  // Calculate stats
  const stats = useMemo(() => {
    const allTasks = hierarchicalTasks;
    return {
      total: allTasks.length,
      high: allTasks.filter(t => t.task_level === 'High').length,
      mid: allTasks.filter(t => t.task_level === 'Mid').length,
      low: allTasks.filter(t => t.task_level === 'Low').length,
      completed: allTasks.filter(t => t.status === 'Completed').length,
      inProgress: allTasks.filter(t => t.status === 'In-Progress').length,
      pending: allTasks.filter(t => t.status === 'Pending').length,
    };
  }, [hierarchicalTasks]);

  // Toggle node expansion
  const handleToggle = useCallback((id: string) => {
    setExpandedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  // Expand all nodes
  const handleExpandAll = useCallback(() => {
    const allIds = new Set(hierarchicalTasks.map(t => t.id));
    setExpandedIds(allIds);
  }, [hierarchicalTasks]);

  // Collapse all nodes
  const handleCollapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  // Error state
  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertCircle className="size-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 mb-2">Failed to load tasks</p>
        <p className="text-sm text-gray-500">{error}</p>
        <button
          onClick={() => selectedProject?.id && fetchTasks(selectedProject.id)}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Task Hierarchy</h1>
        <p className="text-gray-600">
          {selectedProject?.client_name || 'No project selected'} - Task Overview
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Total Tasks</div>
            <FolderTree className="size-5 text-purple-600" />
          </div>
          <div className="text-2xl font-medium">{stats.total}</div>
          <div className="text-xs text-gray-500">
            {stats.high} High / {stats.mid} Mid / {stats.low} Low
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Completed</div>
            <CheckCircle2 className="size-5 text-green-600" />
          </div>
          <div className="text-2xl font-medium text-green-600">{stats.completed}</div>
          <div className="text-xs text-gray-500">
            {stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}% complete
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">In Progress</div>
            <Clock className="size-5 text-blue-600" />
          </div>
          <div className="text-2xl font-medium text-blue-600">{stats.inProgress}</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Pending</div>
            <ListTodo className="size-5 text-gray-600" />
          </div>
          <div className="text-2xl font-medium text-gray-600">{stats.pending}</div>
        </div>
      </div>

      {/* Filters & Controls */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Filter className="size-5 text-gray-500" />
            <h2 className="font-medium">Filters & Controls</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExpandAll}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ExpandIcon className="size-4" />
              Expand All
            </button>
            <button
              onClick={handleCollapseAll}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <MinimizeIcon className="size-4" />
              Collapse All
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Level Filter */}
          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value as TaskLevel | 'all')}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Levels</option>
            <option value="High">High (EGA)</option>
            <option value="Mid">Mid (Assertion)</option>
            <option value="Low">Low (Procedure)</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as AuditTaskStatus | 'all')}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="In-Progress">In Progress</option>
            <option value="Review-Required">Review Required</option>
            <option value="Completed">Completed</option>
            <option value="Failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Task Tree */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <FolderTree className="size-5 text-purple-600" />
          <h2 className="font-medium">Task Tree</h2>
          <span className="text-sm text-gray-500">
            ({filteredTasks.length} tasks)
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin size-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-500">Loading tasks...</p>
          </div>
        ) : taskTree.length === 0 ? (
          <div className="p-8 text-center">
            <FolderTree className="size-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">No tasks found</p>
            <p className="text-sm text-gray-400">
              {hierarchicalTasks.length === 0
                ? 'No tasks have been created for this project yet.'
                : 'Try adjusting your filters to see more results.'}
            </p>
          </div>
        ) : (
          <div className="space-y-1" role="tree" aria-label="Task hierarchy">
            {taskTree.map(node => (
              <TaskNode
                key={node.task.id}
                node={node}
                depth={0}
                selectedTaskId={selectedTaskId}
                expandedIds={expandedIds}
                onToggle={handleToggle}
                onSelect={onSelectTask}
              />
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="font-medium mb-3">Legend</h3>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500 font-medium">Levels:</span>
            <div className="flex items-center gap-1.5">
              <FolderTree className="size-4 text-purple-600" />
              <span className="text-sm">High (EGA)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <FileText className="size-4 text-blue-600" />
              <span className="text-sm">Mid (Assertion)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckSquare className="size-4 text-gray-600" />
              <span className="text-sm">Low (Procedure)</span>
            </div>
          </div>
          <div className="border-l border-gray-200 pl-4 flex items-center gap-4">
            <span className="text-sm text-gray-500 font-medium">Status:</span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="size-4 text-green-600" />
              <span className="text-sm">Completed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="size-4 text-blue-600" />
              <span className="text-sm">In Progress</span>
            </div>
            <div className="flex items-center gap-1.5">
              <AlertCircle className="size-4 text-amber-600" />
              <span className="text-sm">Review Required</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      {filteredTasks.length > 0 && filteredTasks.length !== hierarchicalTasks.length && (
        <div className="text-center text-sm text-gray-500">
          Showing {filteredTasks.length} of {hierarchicalTasks.length} tasks
        </div>
      )}
    </div>
  );
}
