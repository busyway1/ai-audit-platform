'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Clock,
  CheckCircle,
  Edit,
  Eye,
  ChevronDown,
  ChevronUp,
  User,
  Loader2,
} from 'lucide-react';
import { cn } from '../ui/utils';
import {
  type HITLRequestCardProps,
  getPriorityConfig,
  getRequestTypeLabel,
  getAgentRoleLabel,
  formatDeadline,
  isDeadlineUrgent,
  isDeadlinePassed,
} from '../../types/hitl';

/**
 * ChatHITLRequestCard - A card component for displaying HITL requests in the chat interface
 *
 * Design:
 * ┌─────────────────────────────────────────┐
 * │ [Warning] Manager requests approval      │
 * │ ─────────────────────────────────────── │
 * │ Task: 매출채권 샘플링 검증              │
 * │ Priority: High | Deadline: 2h           │
 * │                                         │
 * │ Context: 중요성 기준 초과 항목 발견...  │
 * │                                         │
 * │ Options:                                │
 * │ [Approve] [Request Edit] [Review]       │
 * └─────────────────────────────────────────┘
 */
export function ChatHITLRequestCard({
  request,
  onRespond,
  isLoading = false,
  className,
}: HITLRequestCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [customResponse, setCustomResponse] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const priorityConfig = getPriorityConfig(request.priority);
  const requestTypeLabel = getRequestTypeLabel(request.request_type);
  const agentRoleLabel = getAgentRoleLabel(request.requester_agent);

  const hasDeadline = !!request.deadline;
  const deadlineDisplay = hasDeadline ? formatDeadline(request.deadline!) : null;
  const isUrgent = hasDeadline && isDeadlineUrgent(request.deadline!);
  const isPastDeadline = hasDeadline && isDeadlinePassed(request.deadline!);

  const handleOptionClick = (option: string) => {
    if (option === 'custom') {
      setShowCustomInput(true);
    } else {
      onRespond(request.id, option);
    }
  };

  const handleCustomSubmit = () => {
    if (customResponse.trim()) {
      onRespond(request.id, customResponse.trim());
      setCustomResponse('');
      setShowCustomInput(false);
    }
  };

  const handleCancelCustom = () => {
    setCustomResponse('');
    setShowCustomInput(false);
  };

  // Get icon based on request type
  const getRequestIcon = () => {
    switch (request.request_type) {
      case 'critical_decision':
        return <AlertTriangle className="size-5" />;
      case 'agent_completion_review':
        return <CheckCircle className="size-5" />;
      case 'task_assignment_approval':
        return <User className="size-5" />;
      case 'final_report_approval':
        return <Eye className="size-5" />;
      case 'mid_conversation_query':
        return <Edit className="size-5" />;
      default:
        return <AlertTriangle className="size-5" />;
    }
  };

  // Default options based on request type if not provided
  const getDefaultOptions = (): string[] => {
    switch (request.request_type) {
      case 'critical_decision':
        return ['Approve', 'Reject', 'Request More Info'];
      case 'agent_completion_review':
        return ['Approve', 'Request Edit', 'Direct Review'];
      case 'task_assignment_approval':
        return ['Approve', 'Reassign', 'Reject'];
      case 'final_report_approval':
        return ['Sign Off', 'Request Revision', 'Escalate'];
      case 'mid_conversation_query':
        return ['Provide Answer', 'Escalate', 'Skip'];
      default:
        return ['Approve', 'Reject'];
    }
  };

  const options = request.options?.length ? request.options : getDefaultOptions();

  // Get button variant based on option
  const getButtonVariant = (option: string, index: number): string => {
    const lowerOption = option.toLowerCase();
    if (lowerOption.includes('approve') || lowerOption.includes('sign off')) {
      return 'bg-green-600 hover:bg-green-700 text-white';
    }
    if (lowerOption.includes('reject') || lowerOption.includes('escalate')) {
      return 'bg-red-600 hover:bg-red-700 text-white';
    }
    if (index === 0) {
      return 'bg-blue-600 hover:bg-blue-700 text-white';
    }
    return 'bg-gray-100 hover:bg-gray-200 text-gray-700';
  };

  // Get button icon based on option
  const getButtonIcon = (option: string) => {
    const lowerOption = option.toLowerCase();
    if (lowerOption.includes('approve') || lowerOption.includes('sign off')) {
      return <CheckCircle className="size-4" />;
    }
    if (lowerOption.includes('edit') || lowerOption.includes('revision')) {
      return <Edit className="size-4" />;
    }
    if (lowerOption.includes('review') || lowerOption.includes('direct')) {
      return <Eye className="size-4" />;
    }
    return null;
  };

  const isPending = request.status === 'pending' || request.status === undefined;

  return (
    <div
      className={cn(
        'rounded-lg border-2 overflow-hidden',
        priorityConfig.borderColor,
        priorityConfig.bgColor,
        className
      )}
    >
      {/* Header */}
      <div className={cn('px-4 py-3 border-b', priorityConfig.borderColor)}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={cn('flex-shrink-0', priorityConfig.iconColor)}>
              {getRequestIcon()}
            </span>
            <span className={cn('font-semibold text-sm', priorityConfig.textColor)}>
              HITL
            </span>
            <span className="text-gray-600 text-sm">
              {agentRoleLabel} requests {requestTypeLabel.toLowerCase()}
            </span>
          </div>
          {hasDeadline && (
            <div
              className={cn(
                'flex items-center gap-1 text-xs px-2 py-1 rounded-full',
                isPastDeadline
                  ? 'bg-red-100 text-red-700'
                  : isUrgent
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-gray-100 text-gray-600'
              )}
            >
              <Clock className="size-3" />
              <span>{deadlineDisplay}</span>
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        {/* Title */}
        <h4 className="font-medium text-gray-900">{request.title}</h4>

        {/* Meta info */}
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span
            className={cn(
              'px-2 py-0.5 rounded text-xs font-medium',
              priorityConfig.bgColor,
              priorityConfig.textColor,
              'border',
              priorityConfig.borderColor
            )}
          >
            {priorityConfig.label}
          </span>
          {hasDeadline && (
            <>
              <span className="text-gray-300">|</span>
              <span>Deadline: {deadlineDisplay}</span>
            </>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-gray-700">{request.description}</p>

        {/* Expandable Context */}
        {request.context && Object.keys(request.context).length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="size-4" />
                  <span>Hide context</span>
                </>
              ) : (
                <>
                  <ChevronDown className="size-4" />
                  <span>Show context</span>
                </>
              )}
            </button>

            {isExpanded && (
              <div className="mt-2 p-3 bg-white/50 rounded-lg border border-gray-200 text-sm">
                {request.context.task && (
                  <div className="mb-2">
                    <span className="font-medium text-gray-700">Task:</span>{' '}
                    <span className="text-gray-600">
                      {request.context.task.title} ({request.context.task.status})
                    </span>
                  </div>
                )}
                {request.context.financialData && (
                  <div className="mb-2">
                    <span className="font-medium text-gray-700">Amount:</span>{' '}
                    <span className="text-gray-600">
                      {request.context.financialData.currency || 'KRW'}{' '}
                      {request.context.financialData.amount?.toLocaleString()}
                    </span>
                  </div>
                )}
                {request.context.auditProcedure && (
                  <div className="mb-2">
                    <span className="font-medium text-gray-700">Procedure:</span>{' '}
                    <span className="text-gray-600">
                      {request.context.auditProcedure.name} (
                      {request.context.auditProcedure.riskLevel} risk)
                    </span>
                  </div>
                )}
                {/* Render any additional context fields */}
                {Object.entries(request.context)
                  .filter(
                    ([key]) =>
                      !['task', 'financialData', 'auditProcedure', 'relatedMessages'].includes(key)
                  )
                  .map(([key, value]) => (
                    <div key={key} className="mb-2">
                      <span className="font-medium text-gray-700 capitalize">
                        {key.replace(/_/g, ' ')}:
                      </span>{' '}
                      <span className="text-gray-600">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Response Options */}
        {isPending && !showCustomInput && (
          <div className="pt-2">
            <div className="text-xs text-gray-500 mb-2">Options:</div>
            <div className="flex flex-wrap gap-2">
              {options.map((option, index) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => handleOptionClick(option)}
                  disabled={isLoading}
                  className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    getButtonVariant(option, index)
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    getButtonIcon(option)
                  )}
                  <span>{option}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Custom Response Input */}
        {isPending && showCustomInput && (
          <div className="pt-2 space-y-2">
            <label htmlFor="custom-response" className="text-xs text-gray-500 block">
              Your response:
            </label>
            <textarea
              id="custom-response"
              value={customResponse}
              onChange={(e) => setCustomResponse(e.target.value)}
              placeholder="Enter your response..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              disabled={isLoading}
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelCustom}
                disabled={isLoading}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCustomSubmit}
                disabled={isLoading || !customResponse.trim()}
                className={cn(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isLoading && <Loader2 className="size-4 animate-spin" />}
                <span>Submit</span>
              </button>
            </div>
          </div>
        )}

        {/* Status indicator for non-pending requests */}
        {!isPending && (
          <div
            className={cn(
              'mt-3 px-3 py-2 rounded-lg text-sm',
              request.status === 'approved'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : request.status === 'rejected'
                  ? 'bg-red-50 border border-red-200 text-red-700'
                  : 'bg-gray-50 border border-gray-200 text-gray-700'
            )}
          >
            <span className="font-medium">
              {request.status === 'approved'
                ? 'Approved'
                : request.status === 'rejected'
                  ? 'Rejected'
                  : 'Expired'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatHITLRequestCard;
