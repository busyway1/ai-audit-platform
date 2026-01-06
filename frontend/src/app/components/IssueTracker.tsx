import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, MessageCircle, FileWarning } from 'lucide-react';
import { issues } from '../data/mockData';
import type { IssueImpact, IssueStatus } from '../types/audit';

export function IssueTracker() {
  const [filterImpact, setFilterImpact] = useState<IssueImpact | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<IssueStatus | 'all'>('all');
  const [selectedIssue, setSelectedIssue] = useState(issues[0]);

  const filteredIssues = issues.filter(issue => {
    const matchesImpact = filterImpact === 'all' || issue.impact === filterImpact;
    const matchesStatus = filterStatus === 'all' || issue.status === filterStatus;
    return matchesImpact && matchesStatus;
  });

  const stats = {
    total: issues.length,
    open: issues.filter(i => i.status === 'open').length,
    resolved: issues.filter(i => i.status === 'resolved').length,
    requiresAdjustment: issues.filter(i => i.requiresAdjustment).length,
    managementLetter: issues.filter(i => i.includeInManagementLetter).length,
    totalImpact: issues.reduce((sum, i) => sum + (i.financialImpact || 0), 0)
  };

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

  const getStatusColor = (status: IssueStatus) => {
    switch (status) {
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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Issue & Deficiency Tracker</h1>
        <p className="text-gray-600">Manage exceptions, findings, and required adjustments</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Issues</div>
          <div className="text-2xl font-medium">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Open</div>
          <div className="text-2xl font-medium text-red-600">{stats.open}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Resolved</div>
          <div className="text-2xl font-medium text-green-600">{stats.resolved}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Adj. Required</div>
          <div className="text-2xl font-medium text-orange-600">{stats.requiresAdjustment}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Mgmt Letter</div>
          <div className="text-2xl font-medium text-purple-600">{stats.managementLetter}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Impact</div>
          <div className="text-lg font-medium text-blue-600">{formatCurrency(stats.totalImpact)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issue List */}
        <div className="lg:col-span-1 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col max-h-[calc(100vh-350px)]">
          <div className="bg-gray-800 text-white p-4">
            <h2 className="text-lg mb-3">Issues</h2>
            
            {/* Filters */}
            <div className="space-y-2">
              <select
                value={filterImpact}
                onChange={(e) => setFilterImpact(e.target.value as IssueImpact | 'all')}
                className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Impacts</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as IssueStatus | 'all')}
                className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="open">Open</option>
                <option value="client-responded">Client Responded</option>
                <option value="resolved">Resolved</option>
                <option value="waived">Waived</option>
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-200">
            {filteredIssues.map((issue) => (
              <div
                key={issue.id}
                onClick={() => setSelectedIssue(issue)}
                className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedIssue.id === issue.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="text-xs text-gray-500">{issue.taskNumber}</div>
                  <span className={`px-2 py-1 rounded text-xs border ${getImpactColor(issue.impact)}`}>
                    {issue.impact.toUpperCase()}
                  </span>
                </div>
                <div className="font-medium text-sm mb-2">{issue.title}</div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${getStatusColor(issue.status)}`}>
                    {issue.status.replace('-', ' ').toUpperCase()}
                  </span>
                  {issue.requiresAdjustment && (
                    <span className="text-xs text-orange-600 flex items-center gap-1">
                      <AlertTriangle className="size-3" />
                      Adj.
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
            Showing {filteredIssues.length} of {issues.length} issues
          </div>
        </div>

        {/* Issue Detail */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden">
          {selectedIssue && (
            <>
              {/* Header */}
              <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="text-sm text-gray-400 mb-1">{selectedIssue.taskNumber}</div>
                    <h2 className="text-2xl mb-2">{selectedIssue.title}</h2>
                    <div className="text-sm text-gray-300">{selectedIssue.accountCategory}</div>
                  </div>
                  <span className={`px-3 py-1 rounded border text-xs ${getImpactColor(selectedIssue.impact)}`}>
                    {selectedIssue.impact.toUpperCase()} IMPACT
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Identified By</div>
                    <div className="text-sm">{selectedIssue.identifiedBy}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Identified Date</div>
                    <div className="text-sm">{formatDate(selectedIssue.identifiedDate)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Financial Impact</div>
                    <div className="text-sm">{selectedIssue.financialImpact ? formatCurrency(selectedIssue.financialImpact) : 'N/A'}</div>
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
                    {selectedIssue.description}
                  </div>
                </section>

                {/* Status */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Current Status</h3>
                  <div className="pl-6">
                    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${getStatusColor(selectedIssue.status)}`}>
                      {selectedIssue.status === 'resolved' ? (
                        <CheckCircle2 className="size-5" />
                      ) : selectedIssue.status === 'client-responded' ? (
                        <MessageCircle className="size-5" />
                      ) : (
                        <Clock className="size-5" />
                      )}
                      <span className="font-medium">{selectedIssue.status.replace('-', ' ').toUpperCase()}</span>
                    </div>
                  </div>
                </section>

                {/* Client Response */}
                {selectedIssue.clientResponse && (
                  <section>
                    <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide flex items-center gap-2">
                      <MessageCircle className="size-4" />
                      Client Response
                    </h3>
                    <div className="pl-6">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="text-xs text-blue-600">
                            Responded on {formatDate(selectedIssue.clientResponseDate!)}
                          </div>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed">
                          {selectedIssue.clientResponse}
                        </div>
                      </div>
                    </div>
                  </section>
                )}

                {/* Resolution */}
                {selectedIssue.resolution && (
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
                            Resolved on {formatDate(selectedIssue.resolvedDate!)}
                          </div>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed">
                          {selectedIssue.resolution}
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
                      selectedIssue.requiresAdjustment ? 'bg-orange-50 border border-orange-200' : 'bg-gray-50 border border-gray-200'
                    }`}>
                      {selectedIssue.requiresAdjustment ? (
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
                      selectedIssue.includeInManagementLetter ? 'bg-purple-50 border border-purple-200' : 'bg-gray-50 border border-gray-200'
                    }`}>
                      {selectedIssue.includeInManagementLetter ? (
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

              {/* Action Bar */}
              {selectedIssue.status === 'open' && (
                <div className="border-t border-gray-200 bg-gray-50 p-4 flex gap-2">
                  <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                    Request Client Response
                  </button>
                  <button className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm">
                    Mark as Resolved
                  </button>
                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors text-sm">
                    Waive Issue
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
