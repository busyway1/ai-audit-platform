import { CheckCircle2, Clock, AlertTriangle, MessageCircle, FileWarning } from 'lucide-react';
import type { IssueImpact, IssueStatus } from '../../types/audit';

interface IssueDetailsArtifactProps {
  data: {
    id: string;
    taskNumber: string;
    title: string;
    accountCategory: string;
    impact: IssueImpact;
    status: IssueStatus;
    identifiedBy: string;
    identifiedDate: string;
    financialImpact?: number;
    description: string;
    clientResponse?: string;
    clientResponseDate?: string;
    resolution?: string;
    resolvedDate?: string;
    requiresAdjustment: boolean;
    includeInManagementLetter: boolean;
  };
  status: 'streaming' | 'complete' | 'error';
}

export function IssueDetailsArtifact({ data, status }: IssueDetailsArtifactProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(date);
  };

  const getImpactColor = (impact: IssueImpact) => {
    switch (impact) {
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-300';
      case 'high':
        return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'low':
        return 'bg-green-100 text-green-700 border-green-300';
    }
  };

  const getStatusColor = (issueStatus: IssueStatus) => {
    switch (issueStatus) {
      case 'open':
        return 'bg-red-100 text-red-700';
      case 'client-responded':
        return 'bg-blue-100 text-blue-700';
      case 'resolved':
        return 'bg-green-100 text-green-700';
      case 'waived':
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="space-y-4">
      {/* Streaming Status Badge */}
      {status === 'streaming' && (
        <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <Clock className="size-4 animate-spin" />
          Updating...
        </div>
      )}
      {status === 'error' && (
        <div className="inline-flex items-center gap-2 bg-red-100 text-red-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <AlertTriangle className="size-4" />
          Error loading issue
        </div>
      )}
      {status === 'complete' && (
        <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <CheckCircle2 className="size-4" />
          Complete
        </div>
      )}

      {/* Issue Detail Content (Extracted from IssueTracker.tsx) */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <div className="text-sm text-gray-400 mb-1">{data.taskNumber}</div>
              <h2 className="text-2xl mb-2">{data.title}</h2>
              <div className="text-sm text-gray-300">{data.accountCategory}</div>
            </div>
            <span className={`px-3 py-1 rounded border text-xs ${getImpactColor(data.impact)}`}>
              {data.impact.toUpperCase()} IMPACT
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
            <div>
              <div className="text-xs text-gray-400 mb-1">Identified By</div>
              <div className="text-sm">{data.identifiedBy}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Identified Date</div>
              <div className="text-sm">{formatDate(data.identifiedDate)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Financial Impact</div>
              <div className="text-sm">{data.financialImpact ? formatCurrency(data.financialImpact) : 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Description */}
          <section>
            <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide flex items-center gap-2">
              <FileWarning className="size-4" />
              Issue Description
            </h3>
            <div className="pl-6 text-sm text-gray-700 leading-relaxed bg-gray-50 p-4 rounded border border-gray-200">
              {data.description}
            </div>
          </section>

          {/* Status */}
          <section>
            <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Current Status</h3>
            <div className="pl-6">
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${getStatusColor(data.status)}`}>
                {data.status === 'resolved' ? (
                  <CheckCircle2 className="size-5" />
                ) : data.status === 'client-responded' ? (
                  <MessageCircle className="size-5" />
                ) : (
                  <Clock className="size-5" />
                )}
                <span className="font-medium">{data.status.replace('-', ' ').toUpperCase()}</span>
              </div>
            </div>
          </section>

          {/* Client Response */}
          {data.clientResponse && (
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide flex items-center gap-2">
                <MessageCircle className="size-4" />
                Client Response
              </h3>
              <div className="pl-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-xs text-blue-600">
                      Responded on {formatDate(data.clientResponseDate!)}
                    </div>
                  </div>
                  <div className="text-sm text-gray-700 leading-relaxed">
                    {data.clientResponse}
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Resolution */}
          {data.resolution && (
            <section>
              <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide flex items-center gap-2">
                <CheckCircle2 className="size-4" />
                Resolution
              </h3>
              <div className="pl-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="size-4 text-green-600" />
                    <div className="text-xs text-green-700">
                      Resolved on {formatDate(data.resolvedDate!)}
                    </div>
                  </div>
                  <div className="text-sm text-gray-700 leading-relaxed">
                    {data.resolution}
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Action Items */}
          <section>
            <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Action Items</h3>
            <div className="pl-6 space-y-2">
              <div className={`flex items-center gap-3 p-3 rounded-lg ${
                data.requiresAdjustment ? 'bg-orange-50 border border-orange-200' : 'bg-gray-50 border border-gray-200'
              }`}>
                {data.requiresAdjustment ? (
                  <>
                    <AlertTriangle className="size-5 text-orange-600" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-orange-900">Adjustment Required</div>
                      <div className="text-xs text-orange-700">This issue requires financial statement adjustment</div>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="size-5 text-green-600" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-green-900">No Adjustment Required</div>
                    </div>
                  </>
                )}
              </div>

              <div className={`flex items-center gap-3 p-3 rounded-lg ${
                data.includeInManagementLetter ? 'bg-purple-50 border border-purple-200' : 'bg-gray-50 border border-gray-200'
              }`}>
                {data.includeInManagementLetter ? (
                  <>
                    <FileWarning className="size-5 text-purple-600" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-purple-900">Include in Management Letter</div>
                      <div className="text-xs text-purple-700">This finding will be communicated to management</div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="size-5" />
                    <div className="flex-1">
                      <div className="text-sm text-gray-700">Not included in Management Letter</div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
