'use client'

import * as React from 'react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { cn } from '../ui/utils'
import type { HITLRequest, HITLRequestType } from '../../types/supabase'

interface HITLRequestCardProps {
  request: HITLRequest
  onApprove: (requestId: string, response?: string) => Promise<void>
  onReject: (requestId: string, response?: string) => Promise<void>
  className?: string
  disabled?: boolean
}

type UrgencyLevel = 'critical' | 'high' | 'medium' | 'low'

function getUrgencyLevel(score: number): UrgencyLevel {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

function getUrgencyBadgeStyles(level: UrgencyLevel): string {
  const styles: Record<UrgencyLevel, string> = {
    critical: 'bg-red-600 text-white border-red-700',
    high: 'bg-orange-500 text-white border-orange-600',
    medium: 'bg-yellow-500 text-black border-yellow-600',
    low: 'bg-green-500 text-white border-green-600',
  }
  return styles[level]
}

function getRequestTypeBadgeStyles(type: HITLRequestType): string {
  const styles: Record<HITLRequestType, string> = {
    approval: 'bg-blue-100 text-blue-800 border-blue-200',
    clarification: 'bg-purple-100 text-purple-800 border-purple-200',
    escalation: 'bg-red-100 text-red-800 border-red-200',
    review: 'bg-gray-100 text-gray-800 border-gray-200',
  }
  return styles[type]
}

function formatRequestType(type: HITLRequestType): string {
  const labels: Record<HITLRequestType, string> = {
    approval: 'Approval Required',
    clarification: 'Clarification Needed',
    escalation: 'Escalation',
    review: 'Review Required',
  }
  return labels[type]
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

export function HITLRequestCard({
  request,
  onApprove,
  onReject,
  className,
  disabled = false,
}: HITLRequestCardProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [responseText, setResponseText] = React.useState('')
  const [showResponseInput, setShowResponseInput] = React.useState(false)
  const [actionType, setActionType] = React.useState<'approve' | 'reject' | null>(null)

  const urgencyLevel = getUrgencyLevel(request.urgency_score)
  const isPending = request.status === 'pending'

  const handleAction = async (type: 'approve' | 'reject') => {
    if (showResponseInput && actionType === type) {
      setIsLoading(true)
      try {
        if (type === 'approve') {
          await onApprove(request.id, responseText || undefined)
        } else {
          await onReject(request.id, responseText || undefined)
        }
      } finally {
        setIsLoading(false)
        setShowResponseInput(false)
        setResponseText('')
        setActionType(null)
      }
    } else {
      setShowResponseInput(true)
      setActionType(type)
    }
  }

  const handleCancel = () => {
    setShowResponseInput(false)
    setResponseText('')
    setActionType(null)
  }

  return (
    <Card className={cn('relative', className)}>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge className={cn('text-xs', getUrgencyBadgeStyles(urgencyLevel))}>
                {urgencyLevel.charAt(0).toUpperCase() + urgencyLevel.slice(1)} Urgency
              </Badge>
              <Badge className={cn('text-xs', getRequestTypeBadgeStyles(request.request_type))}>
                {formatRequestType(request.request_type)}
              </Badge>
            </div>
            <CardTitle className="text-lg font-semibold">{request.title}</CardTitle>
          </div>
          <CardAction>
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {formatRelativeTime(request.created_at)}
            </span>
          </CardAction>
        </div>
        <CardDescription className="mt-2 text-sm">
          Task ID: {request.task_id.substring(0, 8)}...
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-1">Context</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {request.context}
            </p>
          </div>

          {request.options && Array.isArray(request.options) && request.options.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Options</h4>
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                {(request.options as string[]).map((option, index) => (
                  <li key={index}>{option}</li>
                ))}
              </ul>
            </div>
          )}

          {showResponseInput && (
            <div className="mt-4">
              <label htmlFor="response-input" className="text-sm font-medium mb-1 block">
                {actionType === 'approve' ? 'Approval Comment' : 'Rejection Reason'} (Optional)
              </label>
              <textarea
                id="response-input"
                className="w-full px-3 py-2 text-sm border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                rows={3}
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder={
                  actionType === 'approve'
                    ? 'Add an optional comment for approval...'
                    : 'Provide a reason for rejection...'
                }
                disabled={isLoading}
              />
            </div>
          )}

          {!isPending && (
            <div className="mt-4 p-3 rounded-md bg-muted">
              <div className="flex items-center gap-2 mb-1">
                <Badge
                  variant={request.status === 'approved' ? 'default' : 'destructive'}
                  className="text-xs"
                >
                  {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                </Badge>
                {request.responded_at && (
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(request.responded_at)}
                  </span>
                )}
              </div>
              {request.response && (
                <p className="text-sm text-muted-foreground mt-1">{request.response}</p>
              )}
            </div>
          )}
        </div>
      </CardContent>

      {isPending && (
        <CardFooter className="flex gap-2 justify-end">
          {showResponseInput ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                variant={actionType === 'approve' ? 'default' : 'destructive'}
                size="sm"
                onClick={() => handleAction(actionType!)}
                disabled={isLoading || disabled}
              >
                {isLoading
                  ? 'Processing...'
                  : actionType === 'approve'
                    ? 'Confirm Approval'
                    : 'Confirm Rejection'}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleAction('reject')}
                disabled={disabled || isLoading}
              >
                Reject
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => handleAction('approve')}
                disabled={disabled || isLoading}
              >
                Approve
              </Button>
            </>
          )}
        </CardFooter>
      )}
    </Card>
  )
}

export default HITLRequestCard
