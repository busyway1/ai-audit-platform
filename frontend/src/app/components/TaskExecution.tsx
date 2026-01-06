import { useState } from 'react';
import { Search, ChevronRight, User, Bot, FileText, AlertCircle, Sparkles } from 'lucide-react';
import { tasks, agentMessages } from '../data/mockData';
import type { Task, TaskStatus, AuditPhase } from '../types/audit';
import { AskAIDrawer } from './workspace/AskAIDrawer';

export function TaskExecution() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(tasks[0]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<TaskStatus | 'all'>('all');
  const [filterPhase, setFilterPhase] = useState<AuditPhase | 'all'>('all');
  const [feedbackInput, setFeedbackInput] = useState('');
  const [isAskAIOpen, setIsAskAIOpen] = useState(false);

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         task.taskNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || task.status === filterStatus;
    const matchesPhase = filterPhase === 'all' || task.phase === filterPhase;
    return matchesSearch && matchesStatus && matchesPhase;
  });

  const taskMessages = selectedTask 
    ? agentMessages.filter(msg => msg.taskId === selectedTask.id)
    : [];

  const getStatusBadge = (status: TaskStatus) => {
    const styles = {
      'not-started': 'bg-gray-100 text-gray-700',
      'in-progress': 'bg-blue-100 text-blue-700',
      'pending-review': 'bg-amber-100 text-amber-700',
      'completed': 'bg-green-100 text-green-700',
      'rejected': 'bg-red-100 text-red-700'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs ${styles[status]}`}>
        {status.replace('-', ' ').toUpperCase()}
      </span>
    );
  };

  const getRoleIcon = (role: string) => {
    if (role === 'manager') {
      return <User className="size-4 text-blue-600" />;
    } else if (role === 'staff') {
      return <Bot className="size-4 text-emerald-600" />;
    }
    return <User className="size-4 text-purple-600" />;
  };

  const getRoleColor = (role: string) => {
    if (role === 'manager') return 'bg-blue-100 border-blue-300';
    if (role === 'staff') return 'bg-emerald-100 border-emerald-300';
    return 'bg-purple-100 border-purple-300';
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const handleSubmitFeedback = () => {
    if (!feedbackInput.trim() || !selectedTask) return;
    
    // In a real app, this would send to backend
    console.log('Feedback submitted:', feedbackInput);
    setFeedbackInput('');
    alert('Feedback submitted to agents for re-execution');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Task Execution & Management</h1>
        <p className="text-gray-600">Monitor and interact with AI agents performing audit procedures</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        {/* Task List */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
          <div className="bg-gray-800 text-white p-4">
            <h2 className="text-lg mb-3">Audit Tasks</h2>
            
            {/* Search */}
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tasks..."
                className="w-full pl-10 pr-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>

            {/* Filters */}
            <div className="grid grid-cols-2 gap-2">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as TaskStatus | 'all')}
                className="px-3 py-1.5 bg-gray-700 text-white rounded border border-gray-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="not-started">Not Started</option>
                <option value="in-progress">In Progress</option>
                <option value="pending-review">Pending Review</option>
                <option value="completed">Completed</option>
              </select>

              <select
                value={filterPhase}
                onChange={(e) => setFilterPhase(e.target.value as AuditPhase | 'all')}
                className="px-3 py-1.5 bg-gray-700 text-white rounded border border-gray-600 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Phases</option>
                <option value="planning">Planning</option>
                <option value="risk-assessment">Risk Assessment</option>
                <option value="controls-testing">Controls Testing</option>
                <option value="substantive-procedures">Substantive</option>
                <option value="completion">Completion</option>
              </select>
            </div>
          </div>

          {/* Task List Items */}
          <div className="flex-1 overflow-y-auto divide-y divide-gray-200">
            {filteredTasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedTask?.id === task.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="text-xs text-gray-500">{task.taskNumber}</div>
                  {getStatusBadge(task.status)}
                </div>
                <div className="font-medium text-sm mb-1">{task.title}</div>
                <div className="text-xs text-gray-600 mb-2">{task.accountCategory}</div>
                
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">{task.progress}% complete</span>
                  {task.requiresReview && (
                    <span className="flex items-center gap-1 text-amber-600">
                      <AlertCircle className="size-3" />
                      Review
                    </span>
                  )}
                </div>
                <div className="bg-gray-200 rounded-full h-1 mt-2">
                  <div 
                    className="bg-blue-600 h-1 rounded-full transition-all"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
            Showing {filteredTasks.length} of {tasks.length} tasks
          </div>
        </div>

        {/* Task Detail */}
        {selectedTask ? (
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
            {/* Task Header */}
            <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6 border-b">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-sm text-gray-400 mb-1">{selectedTask.taskNumber}</div>
                  <h2 className="text-2xl mb-2">{selectedTask.title}</h2>
                  <p className="text-sm text-gray-300">{selectedTask.description}</p>
                </div>
                {getStatusBadge(selectedTask.status)}
              </div>

              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-700">
                <div>
                  <div className="text-xs text-gray-400 mb-1">Account Category</div>
                  <div className="text-sm">{selectedTask.accountCategory}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400 mb-1">Business Process</div>
                  <div className="text-sm">{selectedTask.businessProcess}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400 mb-1">Due Date</div>
                  <div className="text-sm">{new Date(selectedTask.dueDate).toLocaleDateString('ko-KR')}</div>
                </div>
              </div>
            </div>

            {/* Agent Interaction Timeline */}
            <div className="flex-1 overflow-y-auto p-6 bg-gray-50 space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <div className="text-sm font-medium text-gray-700">Agent Interaction Timeline</div>
                <div className="text-xs text-gray-500">({taskMessages.length} messages)</div>
              </div>

              {taskMessages.map((message, idx) => (
                <div key={message.id} className="flex gap-3">
                  {/* Timeline Line */}
                  <div className="flex flex-col items-center">
                    <div className={`size-8 rounded-full border-2 flex items-center justify-center ${getRoleColor(message.agentRole)}`}>
                      {getRoleIcon(message.agentRole)}
                    </div>
                    {idx < taskMessages.length - 1 && (
                      <div className="w-0.5 flex-1 bg-gray-300 my-1" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{message.agentName}</span>
                      <span className="text-xs text-gray-500">{formatTimestamp(message.timestamp)}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        message.type === 'instruction' ? 'bg-blue-100 text-blue-700' :
                        message.type === 'tool-use' ? 'bg-purple-100 text-purple-700' :
                        message.type === 'human-feedback' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {message.type}
                      </span>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="text-sm text-gray-700 leading-relaxed">
                        {message.content}
                      </div>

                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                          {message.attachments.map((attachment, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 p-2 bg-gray-50 rounded border border-gray-200"
                            >
                              <FileText className="size-4 text-blue-600" />
                              <span className="text-sm text-gray-700">{attachment.name}</span>
                              <span className="text-xs text-gray-500 ml-auto">{attachment.type}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {taskMessages.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  <Bot className="size-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-sm">No agent interactions yet</p>
                  <p className="text-xs text-gray-400 mt-1">Agents will start working on this task soon</p>
                </div>
              )}
            </div>

            {/* Human Feedback Interface */}
            <div className="border-t border-gray-200 bg-white p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="size-5 text-amber-600" />
                <h3 className="font-medium">Human-in-the-Loop Feedback</h3>
              </div>
              
              <div className="space-y-3">
                <textarea
                  value={feedbackInput}
                  onChange={(e) => setFeedbackInput(e.target.value)}
                  placeholder="Provide feedback to the agents (e.g., 'Sample size is insufficient. Please increase to 50 items and rerun the analysis.')"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-600 focus:border-transparent resize-none"
                  rows={3}
                />
                
                <div className="flex gap-2">
                  <button
                    onClick={handleSubmitFeedback}
                    disabled={!feedbackInput.trim()}
                    className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  >
                    Reject & Request Re-execution
                  </button>
                  <button
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
                  >
                    Approve & Continue
                  </button>
                </div>
              </div>

              <div className="mt-3 text-xs text-gray-500">
                Your feedback will be sent to the assigned agents for review and action
              </div>
            </div>
          </div>
        ) : (
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <ChevronRight className="size-12 mx-auto mb-3 text-gray-400" />
              <p className="text-sm">Select a task to view details</p>
            </div>
          </div>
        )}
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
        context={selectedTask ? `Task ${selectedTask.taskNumber}: ${selectedTask.title}` : 'Task Execution & Management'}
        onOpenInMainChat={() => {
          window.location.hash = '#/chat';
        }}
      />
    </div>
  );
}