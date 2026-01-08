/**
 * Agent Conversation Panel
 *
 * A real-time conversation panel for Partner/Manager/Staff agents.
 * Shows messages from different agent roles with visual distinction,
 * role indicators, timestamps, and auto-scroll functionality.
 *
 * @module components/agents/AgentConversationPanel
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import { Users, UserCog, User, Briefcase, Wifi, WifiOff, Loader2, MessageSquare } from 'lucide-react';
import type { AgentMessage, AgentRole } from '../../types/audit';

/**
 * Role configuration for visual styling
 */
interface RoleConfig {
  icon: typeof Users;
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  accentColor: string;
}

const ROLE_CONFIGS: Record<AgentRole, RoleConfig> = {
  partner: {
    icon: Briefcase,
    label: 'Partner',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    accentColor: 'bg-purple-600',
  },
  manager: {
    icon: UserCog,
    label: 'Manager',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    accentColor: 'bg-blue-600',
  },
  staff: {
    icon: User,
    label: 'Staff',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    accentColor: 'bg-green-600',
  },
};

/**
 * Connection status types
 */
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Props for AgentConversationPanel
 */
interface AgentConversationPanelProps {
  /** List of agent messages to display */
  messages: AgentMessage[];
  /** Task ID for the current conversation */
  taskId?: string;
  /** Task title to display in header */
  taskTitle?: string;
  /** Whether messages are currently streaming */
  isStreaming?: boolean;
  /** Current SSE connection status */
  connectionStatus?: ConnectionStatus;
  /** Filter messages by specific agent role */
  roleFilter?: AgentRole | 'all';
  /** Callback when a message is clicked */
  onMessageClick?: (message: AgentMessage) => void;
  /** Show compact view */
  compact?: boolean;
  /** Maximum height (CSS value) */
  maxHeight?: string;
  /** Custom class name */
  className?: string;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Format relative time (e.g., "2 minutes ago")
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes === 1) return '1 minute ago';
  if (diffMinutes < 60) return `${diffMinutes} minutes ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours === 1) return '1 hour ago';
  if (diffHours < 24) return `${diffHours} hours ago`;

  return formatTimestamp(timestamp);
}

/**
 * Get message type badge styling
 */
function getMessageTypeBadge(type: AgentMessage['type']): { label: string; className: string } | null {
  const badges: Record<AgentMessage['type'], { label: string; className: string }> = {
    instruction: { label: 'Instruction', className: 'bg-amber-100 text-amber-700' },
    response: { label: 'Response', className: 'bg-gray-100 text-gray-700' },
    'tool-use': { label: 'Tool Use', className: 'bg-cyan-100 text-cyan-700' },
    'file-upload': { label: 'File', className: 'bg-indigo-100 text-indigo-700' },
    'human-feedback': { label: 'Human Feedback', className: 'bg-pink-100 text-pink-700' },
  };
  return badges[type] || null;
}

/**
 * Connection status indicator component
 */
function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const configs: Record<ConnectionStatus, { icon: typeof Wifi; label: string; className: string }> = {
    connected: { icon: Wifi, label: 'Connected', className: 'text-green-600' },
    connecting: { icon: Loader2, label: 'Connecting...', className: 'text-amber-600 animate-spin' },
    disconnected: { icon: WifiOff, label: 'Disconnected', className: 'text-gray-400' },
    error: { icon: WifiOff, label: 'Connection Error', className: 'text-red-600' },
  };

  const config = configs[status];
  const Icon = config.icon;

  return (
    <div className={`flex items-center gap-1.5 text-xs ${config.className}`}>
      <Icon className="size-3.5" />
      <span>{config.label}</span>
    </div>
  );
}

/**
 * Single message component
 */
function AgentMessageItem({
  message,
  compact,
  onClick,
}: {
  message: AgentMessage;
  compact?: boolean;
  onClick?: () => void;
}) {
  const roleConfig = ROLE_CONFIGS[message.agentRole];
  const RoleIcon = roleConfig.icon;
  const typeBadge = getMessageTypeBadge(message.type);

  return (
    <div
      className={`group flex gap-3 ${compact ? 'py-2' : 'py-3'} ${onClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
      onClick={onClick}
    >
      {/* Role Icon */}
      <div
        className={`flex-shrink-0 size-8 rounded-full flex items-center justify-center ${roleConfig.accentColor}`}
      >
        <RoleIcon className="size-4 text-white" />
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0">
        {/* Header: Agent name, role badge, timestamp */}
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className="font-medium text-sm text-gray-900">{message.agentName}</span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleConfig.bgColor} ${roleConfig.textColor}`}
          >
            {roleConfig.label}
          </span>
          {typeBadge && (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${typeBadge.className}`}
            >
              {typeBadge.label}
            </span>
          )}
          <span className="text-xs text-gray-400 ml-auto" title={formatTimestamp(message.timestamp)}>
            {formatRelativeTime(message.timestamp)}
          </span>
        </div>

        {/* Message body */}
        <div className={`text-sm text-gray-700 leading-relaxed ${compact ? 'line-clamp-2' : ''}`}>
          {message.content}
        </div>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message.attachments.map((attachment, index) => (
              <a
                key={index}
                href={attachment.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 hover:bg-gray-200 rounded-md text-xs text-gray-700 transition-colors"
              >
                <span className="truncate max-w-32">{attachment.name}</span>
                <span className="text-gray-400">({attachment.type})</span>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Role filter tabs component
 */
function RoleFilterTabs({
  activeFilter,
  onChange,
  messageCounts,
}: {
  activeFilter: AgentRole | 'all';
  onChange: (filter: AgentRole | 'all') => void;
  messageCounts: Record<AgentRole | 'all', number>;
}) {
  const filters: Array<{ value: AgentRole | 'all'; label: string }> = [
    { value: 'all', label: 'All' },
    { value: 'partner', label: 'Partner' },
    { value: 'manager', label: 'Manager' },
    { value: 'staff', label: 'Staff' },
  ];

  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
      {filters.map((filter) => {
        const isActive = activeFilter === filter.value;
        const count = messageCounts[filter.value];
        const config = filter.value !== 'all' ? ROLE_CONFIGS[filter.value] : null;

        return (
          <button
            key={filter.value}
            onClick={() => onChange(filter.value)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
              isActive ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {config && <config.icon className="size-3.5" />}
            {filter.label}
            {count > 0 && (
              <span
                className={`ml-1 px-1.5 py-0.5 rounded-full text-xs ${
                  isActive ? 'bg-gray-100 text-gray-700' : 'bg-gray-200 text-gray-600'
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Agent Conversation Panel
 *
 * Displays agent messages with role indicators, timestamps, and real-time streaming support.
 *
 * @example
 * ```tsx
 * <AgentConversationPanel
 *   messages={agentMessages}
 *   taskId="task-123"
 *   taskTitle="Revenue Recognition Testing"
 *   isStreaming={true}
 *   connectionStatus="connected"
 * />
 * ```
 */
export function AgentConversationPanel({
  messages,
  taskId,
  taskTitle,
  isStreaming = false,
  connectionStatus = 'disconnected',
  roleFilter: initialRoleFilter = 'all',
  onMessageClick,
  compact = false,
  maxHeight = '600px',
  className = '',
}: AgentConversationPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [roleFilter, setRoleFilter] = useState<AgentRole | 'all'>(initialRoleFilter);
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter messages by role
  const filteredMessages =
    roleFilter === 'all' ? messages : messages.filter((m) => m.agentRole === roleFilter);

  // Calculate message counts per role
  const messageCounts: Record<AgentRole | 'all', number> = {
    all: messages.length,
    partner: messages.filter((m) => m.agentRole === 'partner').length,
    manager: messages.filter((m) => m.agentRole === 'manager').length,
    staff: messages.filter((m) => m.agentRole === 'staff').length,
  };

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [autoScroll]);

  useEffect(() => {
    scrollToBottom();
  }, [filteredMessages.length, scrollToBottom]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  }, []);

  // Get unique agents from messages
  const uniqueAgents = Array.from(
    new Map(messages.map((m) => [m.agentId, { id: m.agentId, name: m.agentName, role: m.agentRole }]))
  ).map(([, agent]) => agent);

  return (
    <div
      className={`flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-4 border-b">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="size-10 bg-white/20 rounded-full flex items-center justify-center">
              <Users className="size-6" />
            </div>
            <div>
              <h2 className="text-lg font-medium">
                {taskTitle || 'Agent Conversation'}
              </h2>
              {taskId && (
                <div className="text-sm text-gray-300">Task ID: {taskId}</div>
              )}
            </div>
          </div>
          <ConnectionIndicator status={connectionStatus} />
        </div>

        {/* Active Agents */}
        {uniqueAgents.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {uniqueAgents.map((agent) => {
              const config = ROLE_CONFIGS[agent.role];
              const Icon = config.icon;
              return (
                <div
                  key={agent.id}
                  className="inline-flex items-center gap-1.5 px-2 py-1 bg-white/10 rounded-full text-xs"
                >
                  <div className={`size-4 rounded-full ${config.accentColor} flex items-center justify-center`}>
                    <Icon className="size-2.5 text-white" />
                  </div>
                  <span>{agent.name}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="px-4 py-2 border-b border-gray-100">
        <RoleFilterTabs
          activeFilter={roleFilter}
          onChange={setRoleFilter}
          messageCounts={messageCounts}
        />
      </div>

      {/* Messages Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto px-4 bg-gray-50"
        style={{ maxHeight }}
        onScroll={handleScroll}
      >
        {filteredMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <MessageSquare className="size-12 mb-3 opacity-50" />
            <p className="text-lg">No messages yet</p>
            <p className="text-sm mt-1">
              {roleFilter !== 'all'
                ? `No ${roleFilter} agent messages`
                : 'Agent conversations will appear here'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredMessages.map((message) => (
              <AgentMessageItem
                key={message.id}
                message={message}
                compact={compact}
                onClick={onMessageClick ? () => onMessageClick(message) : undefined}
              />
            ))}
          </div>
        )}

        {/* Streaming Indicator */}
        {isStreaming && (
          <div className="flex items-center gap-2 py-3 text-gray-500">
            <Loader2 className="size-4 animate-spin" />
            <span className="text-sm">Agent is thinking...</span>
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Footer with auto-scroll toggle */}
      {!autoScroll && filteredMessages.length > 5 && (
        <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
          <button
            onClick={() => {
              setAutoScroll(true);
              scrollToBottom();
            }}
            className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>Scroll to latest</span>
            <span className="text-gray-400">({filteredMessages.length} messages)</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default AgentConversationPanel;
