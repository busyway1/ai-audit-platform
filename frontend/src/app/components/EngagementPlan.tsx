import { useState } from 'react';
import { Send, CheckCircle2, XCircle, FileText, User, Bot } from 'lucide-react';
import { engagementMessages } from '../data/mockData';
import type { EngagementMessage } from '../types/audit';

export function EngagementPlan() {
  const [messages, setMessages] = useState<EngagementMessage[]>(engagementMessages);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const newMessage: EngagementMessage = {
      id: `eng-${Date.now()}`,
      sender: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages([...messages, newMessage]);
    setInputValue('');

    // Simulate AI response
    setTimeout(() => {
      const aiResponse: EngagementMessage = {
        id: `eng-${Date.now()}`,
        sender: 'partner-agent',
        content: '메시지를 확인했습니다. 요청사항을 검토하고 곧 답변드리겠습니다.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1500);
  };

  const handleApprove = (messageId: string) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, status: 'approved' } : msg
    ));
  };

  const handleReject = (messageId: string) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, status: 'rejected' } : msg
    ));
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Engagement Planning</h1>
        <p className="text-gray-600">Collaborate with Partner AI to develop comprehensive audit plan</p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col h-[calc(100vh-200px)]">
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="size-10 bg-white/20 rounded-full flex items-center justify-center">
              <Bot className="size-6" />
            </div>
            <div>
              <h2 className="text-lg">Partner AI Agent</h2>
              <div className="text-sm text-purple-100">Expert in audit planning and risk assessment</div>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-2xl ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
                {/* Message Header */}
                <div className={`flex items-center gap-2 mb-1 ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {message.sender === 'partner-agent' && (
                    <div className="size-6 bg-purple-600 rounded-full flex items-center justify-center">
                      <Bot className="size-4 text-white" />
                    </div>
                  )}
                  <span className="text-xs text-gray-600">
                    {message.sender === 'user' ? 'You' : 'Partner AI'}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatTimestamp(message.timestamp)}
                  </span>
                  {message.sender === 'user' && (
                    <div className="size-6 bg-blue-600 rounded-full flex items-center justify-center">
                      <User className="size-4 text-white" />
                    </div>
                  )}
                </div>

                {/* Message Content */}
                <div
                  className={`rounded-lg p-4 ${
                    message.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-200'
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.content}
                  </div>

                  {/* Attachments */}
                  {message.attachments && message.attachments.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/20 space-y-2">
                      {message.attachments.map((attachment, idx) => (
                        <div
                          key={idx}
                          className={`flex items-center gap-2 p-2 rounded ${
                            message.sender === 'user' ? 'bg-blue-700' : 'bg-gray-50'
                          }`}
                        >
                          <FileText className="size-4" />
                          <span className="text-sm">{attachment.name}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Approval Actions */}
                  {message.status === 'pending-approval' && (
                    <div className="mt-4 pt-4 border-t border-gray-200 flex gap-2">
                      <button
                        onClick={() => handleApprove(message.id)}
                        className="flex-1 flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm"
                      >
                        <CheckCircle2 className="size-4" />
                        Approve Plan
                      </button>
                      <button
                        onClick={() => handleReject(message.id)}
                        className="flex-1 flex items-center justify-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm"
                      >
                        <XCircle className="size-4" />
                        Request Changes
                      </button>
                    </div>
                  )}

                  {/* Status Badge */}
                  {message.status === 'approved' && (
                    <div className="mt-3 inline-flex items-center gap-1 bg-green-100 text-green-700 px-3 py-1 rounded-full text-xs">
                      <CheckCircle2 className="size-3" />
                      Approved
                    </div>
                  )}
                  {message.status === 'rejected' && (
                    <div className="mt-3 inline-flex items-center gap-1 bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs">
                      <XCircle className="size-3" />
                      Changes Requested
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type your message to Partner AI..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-transparent"
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim()}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Send className="size-5" />
              Send
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Discuss audit scope, timelines, and risk assessment with the AI partner
          </div>
        </div>
      </div>
    </div>
  );
}