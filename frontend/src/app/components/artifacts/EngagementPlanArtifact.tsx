import { CheckCircle2, AlertTriangle, Calendar, Users, DollarSign, FileCheck, Clock, AlertCircle } from 'lucide-react';
import type { RiskLevel, EngagementPlanSummary } from '../../types/audit';

interface EngagementPlanArtifactProps {
  data: EngagementPlanSummary | null;
  status: 'streaming' | 'complete' | 'error';
}

export function EngagementPlanArtifact({ data, status }: EngagementPlanArtifactProps) {
  const plan = data;

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

  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
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

  const getTimelineStatus = (timelineStatus: string) => {
    switch (timelineStatus) {
      case 'completed':
        return 'bg-green-600';
      case 'in-progress':
        return 'bg-blue-600';
      default:
        return 'bg-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Badge */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl mb-2">Engagement Plan Summary</h1>
          <p className="text-gray-600">Formally approved audit plan and scope</p>
        </div>
        <div className="flex items-center gap-3">
          {status === 'streaming' && (
            <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full text-sm">
              <Clock className="size-4 animate-spin" />
              Updating...
            </div>
          )}
          {status === 'error' && (
            <div className="inline-flex items-center gap-2 bg-red-100 text-red-700 px-3 py-1.5 rounded-full text-sm">
              <AlertCircle className="size-4" />
              Error loading
            </div>
          )}
          {status === 'complete' && plan?.approvalStatus === 'approved' && (
            <div className="flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-lg border border-green-300">
              <CheckCircle2 className="size-5" />
              <div>
                <div className="text-sm font-medium">Approved</div>
                <div className="text-xs">by {plan.approvedBy} on {formatDate(plan.approvedAt!)}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {!plan && (
        <div className="text-center py-12 text-gray-500">
          No engagement plan data available
        </div>
      )}

      {plan && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Client Information */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl mb-4 flex items-center gap-2">
                <FileCheck className="size-5 text-blue-600" />
                Client & Engagement Information
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600 mb-1">Client Name</div>
                  <div className="font-medium">{plan.clientName}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 mb-1">Fiscal Year</div>
                  <div className="font-medium">{plan.fiscalYear}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 mb-1">Audit Period Start</div>
                  <div className="font-medium">{formatDate(plan.auditPeriod.start)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 mb-1">Audit Period End</div>
                  <div className="font-medium">{formatDate(plan.auditPeriod.end)}</div>
                </div>
              </div>
            </div>

            {/* Materiality */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl mb-4 flex items-center gap-2">
                <DollarSign className="size-5 text-green-600" />
                Materiality Thresholds
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
                  <div className="text-sm text-blue-700 mb-1">Overall Materiality</div>
                  <div className="text-2xl font-medium text-blue-900">{formatCurrency(plan.materiality.overall)}</div>
                  <div className="text-xs text-blue-600 mt-1">~1% of Revenue</div>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200">
                  <div className="text-sm text-purple-700 mb-1">Performance Materiality</div>
                  <div className="text-2xl font-medium text-purple-900">{formatCurrency(plan.materiality.performance)}</div>
                  <div className="text-xs text-purple-600 mt-1">75% of Overall</div>
                </div>
                <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4 border border-gray-200">
                  <div className="text-sm text-gray-700 mb-1">Trivial Threshold</div>
                  <div className="text-2xl font-medium text-gray-900">{formatCurrency(plan.materiality.trivial)}</div>
                  <div className="text-xs text-gray-600 mt-1">5% of Overall</div>
                </div>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
                <div className="text-xs text-blue-700">
                  <strong>Note:</strong> Misstatements below the trivial threshold will not be accumulated.
                  All identified misstatements above this threshold will be tracked and aggregated for evaluation.
                </div>
              </div>
            </div>

            {/* Key Audit Matters */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl mb-4 flex items-center gap-2">
                <AlertTriangle className="size-5 text-red-600" />
                Key Audit Matters (KAM)
              </h2>
              <div className="space-y-3">
                {plan.keyAuditMatters.map((kam, index) => (
                  <div key={kam.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-start gap-3">
                        <div className="size-8 bg-gray-100 rounded-full flex items-center justify-center text-sm font-medium text-gray-700">
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <h3 className="font-medium mb-1">{kam.matter}</h3>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded text-xs border ${getRiskColor(kam.riskLevel)}`}>
                        {kam.riskLevel.toUpperCase()}
                      </span>
                    </div>
                    <div className="ml-11">
                      <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded border border-gray-200">
                        <div className="font-medium text-gray-700 mb-1 text-xs">Audit Response:</div>
                        {kam.response}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Timeline */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl mb-4 flex items-center gap-2">
                <Calendar className="size-5 text-purple-600" />
                Audit Timeline
              </h2>
              <div className="space-y-4">
                {plan.timeline.map((phase, index) => (
                  <div key={index} className="relative">
                    <div className="flex items-start gap-4">
                      <div className="flex flex-col items-center">
                        <div className={`size-10 rounded-full ${getTimelineStatus(phase.status)} flex items-center justify-center text-white`}>
                          {phase.status === 'completed' ? (
                            <CheckCircle2 className="size-5" />
                          ) : (
                            <span className="text-sm">{index + 1}</span>
                          )}
                        </div>
                        {index < plan.timeline.length - 1 && (
                          <div className={`w-0.5 h-12 ${phase.status === 'completed' ? 'bg-green-600' : 'bg-gray-300'}`} />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className="font-medium">{phase.phase}</h3>
                          <span className={`px-2 py-1 rounded text-xs ${
                            phase.status === 'completed' ? 'bg-green-100 text-green-700' :
                            phase.status === 'in-progress' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {phase.status.replace('-', ' ').toUpperCase()}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600">
                          {formatDate(phase.startDate)} → {formatDate(phase.endDate)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar - Resources */}
          <div className="space-y-6">
            {/* Human Team */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg mb-4 flex items-center gap-2">
                <Users className="size-5 text-blue-600" />
                Human Audit Team
              </h2>
              <div className="space-y-3">
                {plan.resources.humanTeam.map((member, index) => (
                  <div key={index} className="flex items-start justify-between p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="flex items-start gap-3">
                      <div className="size-10 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm">
                        {member.name.split(' ')[0][0]}{member.name.split(' ')[1]?.[0] || ''}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{member.name}</div>
                        <div className="text-xs text-gray-600">{member.role}</div>
                      </div>
                    </div>
                    <div className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      {member.allocation}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Agents */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg mb-4 flex items-center gap-2">
                <Users className="size-5 text-purple-600" />
                AI Agent Allocation
              </h2>
              <div className="space-y-3">
                {plan.resources.aiAgents.map((agent, index) => (
                  <div key={index} className="p-3 bg-purple-50 rounded border border-purple-200">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium text-sm">{agent.name}</div>
                      <div className={`px-2 py-0.5 rounded text-xs ${
                        agent.role === 'partner' ? 'bg-purple-600 text-white' :
                        agent.role === 'manager' ? 'bg-blue-600 text-white' :
                        'bg-emerald-600 text-white'
                      }`}>
                        {agent.role.toUpperCase()}
                      </div>
                    </div>
                    <div className="text-xs text-gray-600">
                      {agent.assignedTasks} tasks assigned
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary Stats */}
            <div className="bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-lg p-6">
              <h3 className="text-lg mb-4">Plan Summary</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-white/20">
                  <span className="text-sm">Total Tasks</span>
                  <span className="text-xl font-medium">95</span>
                </div>
                <div className="flex items-center justify-between pb-2 border-b border-white/20">
                  <span className="text-sm">KAMs</span>
                  <span className="text-xl font-medium">{plan.keyAuditMatters.length}</span>
                </div>
                <div className="flex items-center justify-between pb-2 border-b border-white/20">
                  <span className="text-sm">Team Members</span>
                  <span className="text-xl font-medium">{plan.resources.humanTeam.length + plan.resources.aiAgents.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Duration</span>
                  <span className="text-xl font-medium">8 weeks</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
