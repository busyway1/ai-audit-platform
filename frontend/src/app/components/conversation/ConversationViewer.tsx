'use client';

/**
 * ConversationViewer Component
 * Displays agent conversations with filtering and styling.
 */

import React, { useRef, useEffect, useState, useMemo } from 'react';
import { cn } from '../ui/utils';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Toggle } from '../ui/toggle';
import {
  Send,
  MessageSquare,
  AlertCircle,
  AlertTriangle,
  Wrench,
  ArrowRight,
  Clock,
  RefreshCw,
} from 'lucide-react';
import type {
  AgentConversation,
  ConversationFilter,
  MessageType,
} from '@/app/types/conversation';

// --- Types ---

interface ConversationViewerProps {
  conversations: AgentConversation[];
  filter: ConversationFilter;
  onFilterChange: (filter: ConversationFilter) => void;
  loading?: boolean;
  title?: string;
}

// --- Helper Functions ---

const getAgentColor = (agent: string): string => {
  const agentLower = agent.toLowerCase();
  if (agentLower.includes('partner')) return 'bg-purple-50 border-purple-200';
  if (agentLower.includes('manager')) return 'bg-blue-50 border-blue-200';
  if (agentLower.includes('staff')) return 'bg-green-50 border-green-200';
  if (agentLower === 'human') return 'bg-yellow-50 border-yellow-200';
  if (agentLower.includes('validator')) return 'bg-orange-50 border-orange-200';
  if (agentLower.includes('ralph') || agentLower.includes('loop'))
    return 'bg-gray-50 border-gray-200';
  if (agentLower === 'hitl') return 'bg-red-50 border-red-200';
  return 'bg-white border-gray-200';
};

const getAgentBadgeColor = (agent: string): string => {
  const agentLower = agent.toLowerCase();
  if (agentLower.includes('partner')) return 'bg-purple-100 text-purple-800';
  if (agentLower.includes('manager')) return 'bg-blue-100 text-blue-800';
  if (agentLower.includes('staff')) return 'bg-green-100 text-green-800';
  if (agentLower === 'human') return 'bg-yellow-100 text-yellow-800';
  if (agentLower.includes('validator')) return 'bg-orange-100 text-orange-800';
  if (agentLower.includes('ralph') || agentLower.includes('loop'))
    return 'bg-gray-100 text-gray-800';
  return 'bg-gray-100 text-gray-800';
};

const getMessageIcon = (type: MessageType) => {
  switch (type) {
    case 'instruction':
      return <Send className="w-4 h-4 text-blue-500" />;
    case 'response':
      return <MessageSquare className="w-4 h-4 text-green-500" />;
    case 'error':
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    case 'escalation':
      return <AlertTriangle className="w-4 h-4 text-orange-500" />;
    case 'tool_use':
      return <Wrench className="w-4 h-4 text-purple-500" />;
    case 'question':
      return <MessageSquare className="w-4 h-4 text-yellow-500" />;
    case 'answer':
      return <MessageSquare className="w-4 h-4 text-green-500" />;
    case 'feedback':
      return <RefreshCw className="w-4 h-4 text-blue-500" />;
    default:
      return <MessageSquare className="w-4 h-4" />;
  }
};

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// --- ConversationBubble Component ---

interface ConversationBubbleProps {
  conversation: AgentConversation;
}

const ConversationBubble: React.FC<ConversationBubbleProps> = ({
  conversation,
}) => {
  const { fromAgent, toAgent, messageType, content, timestamp, metadata } =
    conversation;

  return (
    <div
      className={cn(
        'p-3 rounded-lg border transition-all',
        getAgentColor(fromAgent),
        messageType === 'error' && 'border-red-300',
        messageType === 'escalation' && 'border-orange-300'
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2 text-sm">
        {getMessageIcon(messageType)}
        <Badge className={cn('text-xs', getAgentBadgeColor(fromAgent))}>
          {fromAgent}
        </Badge>
        <ArrowRight className="w-3 h-3 text-gray-400" />
        <span className="text-gray-600">{toAgent}</span>
        <span className="ml-auto text-gray-400 text-xs flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatTimestamp(timestamp)}
        </span>
      </div>

      {/* Content */}
      <div className="whitespace-pre-wrap text-sm leading-relaxed">
        {content}
      </div>

      {/* Metadata */}
      {metadata && (
        <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-gray-500 space-y-1">
          {metadata.toolCall && (
            <div className="flex items-center gap-1">
              <Wrench className="w-3 h-3" />
              <span>Tool: {metadata.toolCall}</span>
            </div>
          )}
          {metadata.loopAttempt !== undefined && (
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                시도 {metadata.loopAttempt}
                {metadata.strategyUsed && ` (${metadata.strategyUsed})`}
              </Badge>
            </div>
          )}
          {metadata.duration !== undefined && (
            <span>Duration: {metadata.duration.toFixed(2)}s</span>
          )}
          {metadata.fileRefs && metadata.fileRefs.length > 0 && (
            <div>Files: {metadata.fileRefs.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  );
};

// --- Main ConversationViewer Component ---

export const ConversationViewer: React.FC<ConversationViewerProps> = ({
  conversations,
  filter,
  onFilterChange,
  loading = false,
  title,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [conversations, autoScroll]);

  // Filter conversations
  const filteredConversations = useMemo(() => {
    return conversations.filter((conv) => {
      // Agent type filter
      if (filter.agentTypes && filter.agentTypes.length > 0) {
        const matchesAgent = filter.agentTypes.some((type) =>
          conv.fromAgent.toLowerCase().includes(type.toLowerCase())
        );
        if (!matchesAgent) return false;
      }

      // Message type filter
      if (filter.messageTypes && filter.messageTypes.length > 0) {
        if (!filter.messageTypes.includes(conv.messageType)) return false;
      }

      // Error filter
      if (!filter.includeErrors && conv.messageType === 'error') {
        return false;
      }

      return true;
    });
  }, [conversations, filter]);

  // Handle agent filter change
  const handleAgentFilterChange = (value: string) => {
    const agentTypes = value === 'all' ? undefined : value.split(',');
    onFilterChange({ ...filter, agentTypes });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header with Filters */}
      <div className="p-3 border-b space-y-2">
        {title && <h3 className="font-semibold text-sm">{title}</h3>}

        <div className="flex items-center gap-2 flex-wrap">
          {/* Agent Filter */}
          <Select
            value={filter.agentTypes?.join(',') || 'all'}
            onValueChange={handleAgentFilterChange}
          >
            <SelectTrigger className="w-32 h-8 text-xs">
              <SelectValue placeholder="Agent 필터" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">모든 Agent</SelectItem>
              <SelectItem value="partner">Partner</SelectItem>
              <SelectItem value="manager">Manager</SelectItem>
              <SelectItem value="staff">Staff</SelectItem>
              <SelectItem value="human">Human</SelectItem>
              <SelectItem value="ralph">Ralph Loop</SelectItem>
            </SelectContent>
          </Select>

          {/* Error Toggle */}
          <Toggle
            pressed={filter.includeErrors ?? true}
            onPressedChange={(pressed) =>
              onFilterChange({ ...filter, includeErrors: pressed })
            }
            className="h-8 text-xs"
          >
            <AlertCircle className="w-3 h-3 mr-1" />
            에러 포함
          </Toggle>

          {/* Auto-scroll Toggle */}
          <Toggle
            pressed={autoScroll}
            onPressedChange={setAutoScroll}
            className="h-8 text-xs ml-auto"
          >
            자동 스크롤
          </Toggle>

          {/* Message Count */}
          <span className="text-xs text-gray-500">
            {filteredConversations.length} / {conversations.length}
          </span>
        </div>
      </div>

      {/* Conversation List */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {loading ? (
          <div className="flex items-center justify-center h-32" role="status">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>대화 기록이 없습니다</p>
            {filter.agentTypes || !filter.includeErrors ? (
              <p className="text-xs mt-1">필터를 조정해보세요</p>
            ) : null}
          </div>
        ) : (
          filteredConversations.map((conv) => (
            <ConversationBubble key={conv.id} conversation={conv} />
          ))
        )}
      </div>

      {/* Summary Footer */}
      <div className="p-2 border-t text-xs text-gray-500 flex justify-between">
        <span>
          총 {filteredConversations.length}개 메시지
        </span>
        {filteredConversations.filter((c) => c.messageType === 'error').length >
          0 && (
          <span className="text-red-500">
            {
              filteredConversations.filter((c) => c.messageType === 'error')
                .length
            }{' '}
            에러
          </span>
        )}
        {filteredConversations.filter((c) => c.messageType === 'escalation')
          .length > 0 && (
          <span className="text-orange-500">
            {
              filteredConversations.filter(
                (c) => c.messageType === 'escalation'
              ).length
            }{' '}
            에스컬레이션
          </span>
        )}
      </div>
    </div>
  );
};

export default ConversationViewer;
