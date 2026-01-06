import { useState } from 'react';
import { Settings, Wrench, ToggleLeft, ToggleRight, Users, Activity, Shield } from 'lucide-react';
import { agentTools, agents } from '../data/mockData';
import type { AgentTool } from '../types/audit';

export function AgentToolRegistry() {
  const [tools, setTools] = useState<AgentTool[]>(agentTools);
  const [selectedTool, setSelectedTool] = useState<AgentTool | null>(agentTools[0]);

  const toggleToolEnabled = (toolId: string) => {
    setTools(prevTools =>
      prevTools.map(tool =>
        tool.id === toolId ? { ...tool, enabled: !tool.enabled } : tool
      )
    );
    if (selectedTool?.id === toolId) {
      setSelectedTool(prev => prev ? { ...prev, enabled: !prev.enabled } : null);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'data-extraction':
        return '📊';
      case 'analysis':
        return '📈';
      case 'communication':
        return '📧';
      case 'integration':
        return '🔗';
      case 'verification':
        return '✅';
      default:
        return '🔧';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'data-extraction':
        return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'analysis':
        return 'bg-purple-100 text-purple-700 border-purple-300';
      case 'communication':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'integration':
        return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'verification':
        return 'bg-red-100 text-red-700 border-red-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const toolsByCategory = tools.reduce((acc, tool) => {
    if (!acc[tool.category]) {
      acc[tool.category] = [];
    }
    acc[tool.category].push(tool);
    return acc;
  }, {} as Record<string, AgentTool[]>);

  const enabledCount = tools.filter(t => t.enabled).length;
  const totalUsage = tools.reduce((sum, t) => sum + t.usageCount, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Agent & Tool Registry</h1>
        <p className="text-gray-600">Manage AI agent capabilities and tool permissions</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Tools</div>
          <div className="text-2xl font-medium">{tools.length}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Enabled</div>
          <div className="text-2xl font-medium text-green-600">{enabledCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Usage</div>
          <div className="text-2xl font-medium text-blue-600">{totalUsage}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Categories</div>
          <div className="text-2xl font-medium text-purple-600">{Object.keys(toolsByCategory).length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool List */}
        <div className="lg:col-span-1 space-y-4">
          {Object.entries(toolsByCategory).map(([category, categoryTools]) => (
            <div key={category} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className={`px-4 py-3 border-b border-gray-200 flex items-center gap-2 ${getCategoryColor(category)} bg-opacity-20`}>
                <span className="text-xl">{getCategoryIcon(category)}</span>
                <h3 className="font-medium capitalize">{category.replace('-', ' ')}</h3>
                <span className="ml-auto text-xs px-2 py-1 bg-white rounded">
                  {categoryTools.length}
                </span>
              </div>
              <div className="divide-y divide-gray-200">
                {categoryTools.map((tool) => (
                  <div
                    key={tool.id}
                    onClick={() => setSelectedTool(tool)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedTool?.id === tool.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="font-medium text-sm mb-1">{tool.name}</div>
                        <div className="text-xs text-gray-500">Used {tool.usageCount} times</div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleToolEnabled(tool.id);
                        }}
                        className="ml-2"
                      >
                        {tool.enabled ? (
                          <ToggleRight className="size-6 text-green-600" />
                        ) : (
                          <ToggleLeft className="size-6 text-gray-400" />
                        )}
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      {tool.enabled ? (
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">ACTIVE</span>
                      ) : (
                        <span className="text-xs px-2 py-1 bg-gray-100 text-gray-500 rounded">DISABLED</span>
                      )}
                      {tool.assignedAgents.length > 0 && (
                        <span className="text-xs text-gray-500">{tool.assignedAgents.length} agents</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Tool Detail */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden">
          {selectedTool ? (
            <>
              {/* Header */}
              <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start gap-3 flex-1">
                    <span className="text-3xl">{getCategoryIcon(selectedTool.category)}</span>
                    <div>
                      <h2 className="text-2xl mb-2">{selectedTool.name}</h2>
                      <p className="text-sm text-gray-300">{selectedTool.description}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleToolEnabled(selectedTool.id)}
                    className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                      selectedTool.enabled
                        ? 'bg-green-600 hover:bg-green-700'
                        : 'bg-gray-600 hover:bg-gray-700'
                    }`}
                  >
                    {selectedTool.enabled ? (
                      <>
                        <ToggleRight className="size-5" />
                        <span className="text-sm">Enabled</span>
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="size-5" />
                        <span className="text-sm">Disabled</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Category</div>
                    <div className="text-sm capitalize">{selectedTool.category.replace('-', ' ')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Usage Count</div>
                    <div className="text-sm">{selectedTool.usageCount} times</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Last Used</div>
                    <div className="text-sm">{formatDate(selectedTool.lastUsed)}</div>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
                {/* Assigned Agents */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide flex items-center gap-2">
                    <Users className="size-4" />
                    Assigned Agents ({selectedTool.assignedAgents.length})
                  </h3>
                  <div className="pl-6">
                    {selectedTool.assignedAgents.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {selectedTool.assignedAgents.map((agentId) => {
                          const agent = agents.find(a => a.id === agentId);
                          if (!agent) return null;
                          return (
                            <div key={agentId} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                              <div className={`size-10 rounded-full flex items-center justify-center text-white ${
                                agent.role === 'manager' ? 'bg-blue-600' : 'bg-emerald-600'
                              }`}>
                                {agent.name[0]}
                              </div>
                              <div className="flex-1">
                                <div className="font-medium text-sm">{agent.name}</div>
                                <div className="text-xs text-gray-500">{agent.role.toUpperCase()}</div>
                              </div>
                              <div className={`size-2 rounded-full ${
                                agent.status === 'working' ? 'bg-green-500' : 'bg-gray-300'
                              }`} />
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500 bg-gray-50 p-4 rounded border border-gray-200">
                        No agents assigned to this tool
                      </div>
                    )}
                  </div>
                </section>

                {/* Permissions */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide flex items-center gap-2">
                    <Shield className="size-4" />
                    Required Permissions
                  </h3>
                  <div className="pl-6">
                    <div className="flex flex-wrap gap-2">
                      {selectedTool.permissions.map((permission, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs border border-blue-300"
                        >
                          {permission}
                        </span>
                      ))}
                    </div>
                  </div>
                </section>

                {/* Usage Statistics */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide flex items-center gap-2">
                    <Activity className="size-4" />
                    Usage Statistics
                  </h3>
                  <div className="pl-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <div className="text-xs text-blue-700 mb-1">Total Executions</div>
                        <div className="text-2xl font-medium text-blue-900">{selectedTool.usageCount}</div>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                        <div className="text-xs text-purple-700 mb-1">Agents Using</div>
                        <div className="text-2xl font-medium text-purple-900">{selectedTool.assignedAgents.length}</div>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Tool Configuration */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide flex items-center gap-2">
                    <Settings className="size-4" />
                    Configuration
                  </h3>
                  <div className="pl-6">
                    <div className={`p-4 rounded-lg border-2 ${
                      selectedTool.enabled
                        ? 'bg-green-50 border-green-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}>
                      <div className="flex items-start gap-3 mb-4">
                        {selectedTool.enabled ? (
                          <>
                            <Activity className="size-5 text-green-600 flex-shrink-0 mt-0.5" />
                            <div className="flex-1">
                              <div className="font-medium text-green-900 mb-1">Tool is Active</div>
                              <div className="text-sm text-green-700">
                                This tool is currently enabled and can be used by assigned AI agents during task execution.
                              </div>
                            </div>
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="size-5 text-gray-500 flex-shrink-0 mt-0.5" />
                            <div className="flex-1">
                              <div className="font-medium text-gray-900 mb-1">Tool is Disabled</div>
                              <div className="text-sm text-gray-600">
                                This tool is currently disabled. Enable it to allow AI agents to use this capability.
                              </div>
                            </div>
                          </>
                        )}
                      </div>

                      <div className="pt-4 border-t border-gray-300">
                        <div className="text-xs text-gray-600 mb-2">Controllability & Governance</div>
                        <div className="text-sm text-gray-700">
                          Auditors maintain full control over which tools AI agents can access, ensuring compliance with firm policies and regulatory requirements.
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>

              {/* Action Bar */}
              <div className="border-t border-gray-200 bg-gray-50 p-4 flex gap-2">
                <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                  Assign to Agents
                </button>
                <button className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors text-sm">
                  Edit Permissions
                </button>
                <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors text-sm">
                  View Logs
                </button>
              </div>
            </>
          ) : (
            <div className="p-12 text-center">
              <Wrench className="size-16 mx-auto mb-4 text-gray-300" />
              <p className="text-gray-600">Select a tool to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
