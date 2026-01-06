import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, CheckCircle2, Clock, Network, Sparkles } from 'lucide-react';
import { agents, tasks, riskHeatmap } from '../data/mockData';
import type { RiskLevel } from '../types/audit';
import { AskAIDrawer } from './workspace/AskAIDrawer';

export function Dashboard() {
  const [isAskAIOpen, setIsAskAIOpen] = useState(false);
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const inProgressTasks = tasks.filter(t => t.status === 'in-progress').length;
  const highRiskIssues = tasks.filter(t => t.riskLevel === 'critical' || t.riskLevel === 'high').length;
  const overallProgress = Math.round((completedTasks / totalTasks) * 100);

  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
      case 'critical': return '#dc2626';
      case 'high': return '#ea580c';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
    }
  };

  const agentsByRole = {
    partner: agents.filter(a => a.role === 'partner'),
    managers: agents.filter(a => a.role === 'manager'),
    staff: agents.filter(a => a.role === 'staff')
  };

  const tasksByPhase = [
    { phase: 'Planning', count: tasks.filter(t => t.phase === 'planning').length },
    { phase: 'Risk Assessment', count: tasks.filter(t => t.phase === 'risk-assessment').length },
    { phase: 'Controls Testing', count: tasks.filter(t => t.phase === 'controls-testing').length },
    { phase: 'Substantive', count: tasks.filter(t => t.phase === 'substantive-procedures').length },
    { phase: 'Completion', count: tasks.filter(t => t.phase === 'completion').length }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Audit Command Center</h1>
        <p className="text-gray-600">ABC Corporation - FY 2025 Audit</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Overall Progress</div>
            <Activity className="size-5 text-blue-600" />
          </div>
          <div className="text-3xl mb-1">{overallProgress}%</div>
          <div className="text-sm text-gray-500">{completedTasks}/{totalTasks} tasks completed</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">High Risk Issues</div>
            <AlertTriangle className="size-5 text-red-600" />
          </div>
          <div className="text-3xl mb-1">{highRiskIssues}</div>
          <div className="text-sm text-gray-500">Requiring attention</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">In Progress</div>
            <Clock className="size-5 text-amber-600" />
          </div>
          <div className="text-3xl mb-1">{inProgressTasks}</div>
          <div className="text-sm text-gray-500">Active tasks</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Completed</div>
            <CheckCircle2 className="size-5 text-green-600" />
          </div>
          <div className="text-3xl mb-1">{completedTasks}</div>
          <div className="text-sm text-gray-500">Tasks finished</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk-Based Heatmap */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="size-5 text-red-600" />
            <h2 className="text-xl">Risk Assessment Heatmap</h2>
          </div>
          <div className="space-y-3">
            {riskHeatmap.map((item) => (
              <div key={item.category + item.process} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-medium">{item.category}</span>
                    <span className="text-gray-500"> - {item.process}</span>
                  </div>
                  <span className="text-gray-600">{item.completedTasks}/{item.taskCount}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all"
                      style={{ 
                        width: `${item.riskScore}%`,
                        backgroundColor: getRiskColor(item.riskLevel)
                      }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-16 text-right">
                    {item.riskLevel.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Hierarchy Status */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Network className="size-5 text-blue-600" />
            <h2 className="text-xl">Multi-Agent Hierarchy Status</h2>
          </div>
          
          <div className="space-y-4">
            {/* Partner Level */}
            <div className="border-l-4 border-purple-500 pl-4">
              <div className="text-sm text-gray-600 mb-2">Partner AI</div>
              {agentsByRole.partner.map(agent => (
                <div key={agent.id} className="flex items-center justify-between bg-purple-50 rounded-lg p-3">
                  <div>
                    <div className="font-medium">{agent.name}</div>
                    <div className="text-sm text-gray-600">{agent.currentTask || 'Idle'}</div>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs ${
                    agent.status === 'working' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {agent.status}
                  </div>
                </div>
              ))}
            </div>

            {/* Manager Level */}
            <div className="border-l-4 border-blue-500 pl-4">
              <div className="text-sm text-gray-600 mb-2">Manager AI ({agentsByRole.managers.length})</div>
              <div className="space-y-2">
                {agentsByRole.managers.map(agent => (
                  <div key={agent.id} className="flex items-center justify-between bg-blue-50 rounded-lg p-2">
                    <div className="text-sm">
                      <div className="font-medium">{agent.name}</div>
                      <div className="text-xs text-gray-600">{agent.currentTask || 'Idle'}</div>
                    </div>
                    <div className={`px-2 py-0.5 rounded text-xs ${
                      agent.status === 'working' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {agent.status}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Staff Level */}
            <div className="border-l-4 border-emerald-500 pl-4">
              <div className="text-sm text-gray-600 mb-2">Staff AI ({agentsByRole.staff.length})</div>
              <div className="grid grid-cols-2 gap-2">
                {agentsByRole.staff.map(agent => (
                  <div key={agent.id} className="bg-emerald-50 rounded-lg p-2">
                    <div className="text-sm font-medium">{agent.name}</div>
                    <div className="flex items-center justify-between mt-1">
                      <div className="text-xs text-gray-600 truncate">{agent.currentTask || 'Idle'}</div>
                      <div className={`size-2 rounded-full ml-2 ${
                        agent.status === 'working' ? 'bg-green-500' : 'bg-gray-300'
                      }`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Task Distribution by Phase */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-xl mb-4">Task Distribution by Audit Phase</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={tasksByPhase}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="phase" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <button
        onClick={() => setIsAskAIOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-colors z-30"
        aria-label="Ask AI"
      >
        <Sparkles className="size-6" />
      </button>

      <AskAIDrawer
        isOpen={isAskAIOpen}
        onClose={() => setIsAskAIOpen(false)}
        context="Dashboard - ABC Corporation FY 2025 Audit Overview"
        onOpenInMainChat={() => {
          window.location.hash = '#/chat';
        }}
      />
    </div>
  );
}