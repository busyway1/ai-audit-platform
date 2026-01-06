import { CheckCircle2, Clock, AlertCircle, User, Bot, FileText } from 'lucide-react';
import type { Task, AgentMessage } from '../../types/audit';

interface TaskStatusArtifactProps {
  data: {
    task: Task;
    messages: AgentMessage[];
  };
  status: 'streaming' | 'complete' | 'error';
}

export function TaskStatusArtifact({ data, status }: TaskStatusArtifactProps) {
  const { task, messages } = data;

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

  const getStatusBadge = () => {
    if (status === 'streaming') {
      return (
        <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <Clock className="size-4 animate-spin" />
          Updating...
        </div>
      );
    }
    if (status === 'error') {
      return (
        <div className="inline-flex items-center gap-2 bg-red-100 text-red-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <AlertCircle className="size-4" />
          Error
        </div>
      );
    }
    return (
      <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-3 py-1.5 rounded-full text-sm font-medium">
        <CheckCircle2 className="size-4" />
        Complete
      </div>
    );
  };

  const getTaskStatusBadge = (taskStatus: string) => {
    const styles = {
      'not-started': 'bg-gray-100 text-gray-700',
      'in-progress': 'bg-blue-100 text-blue-700',
      'pending-review': 'bg-amber-100 text-amber-700',
      'completed': 'bg-green-100 text-green-700',
      'rejected': 'bg-red-100 text-red-700'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${styles[taskStatus as keyof typeof styles] || 'bg-gray-100 text-gray-700'}`}>
        {taskStatus.replace('-', ' ').toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Status Badge */}
      <div className="flex items-center justify-between">
        {getStatusBadge()}
        {getTaskStatusBadge(task.status)}
      </div>

      {/* Task Header */}
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6 rounded-lg">
        <div className="text-sm text-gray-400 mb-1">{task.taskNumber}</div>
        <h2 className="text-2xl mb-2">{task.title}</h2>
        <p className="text-sm text-gray-300">{task.description}</p>

        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-700">
          <div>
            <div className="text-xs text-gray-400 mb-1">Account Category</div>
            <div className="text-sm">{task.accountCategory}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Business Process</div>
            <div className="text-sm">{task.businessProcess}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Progress</div>
            <div className="text-sm">{task.progress}%</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Agent Interaction Timeline */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-700">Agent Interaction Timeline</h3>
          <span className="text-xs text-gray-500">({messages.length} messages)</span>
        </div>

        {messages.length > 0 ? (
          <div className="space-y-4">
            {messages.map((message, idx) => (
              <div key={message.id} className="flex gap-3">
                {/* Timeline Line */}
                <div className="flex flex-col items-center">
                  <div className={`size-8 rounded-full border-2 flex items-center justify-center ${getRoleColor(message.agentRole)}`}>
                    {getRoleIcon(message.agentRole)}
                  </div>
                  {idx < messages.length - 1 && (
                    <div className="w-0.5 flex-1 bg-gray-300 my-1 min-h-[40px]" />
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
                        {message.attachments.map((attachment, attachIdx) => (
                          <div
                            key={attachIdx}
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
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
            <Bot className="size-12 mx-auto mb-3 text-gray-400" />
            <p className="text-sm">No agent interactions yet</p>
            <p className="text-xs text-gray-400 mt-1">Agents will start working on this task soon</p>
          </div>
        )}
      </div>

      {/* Due Date and Review Status */}
      {task.requiresReview && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertCircle className="size-5 text-amber-600" />
          <div>
            <div className="text-sm font-medium text-amber-900">Review Required</div>
            <div className="text-xs text-amber-700 mt-0.5">
              This task requires human review before completion
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
