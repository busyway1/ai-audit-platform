import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot } from 'lucide-react';
import { useChatStore } from '../../stores/useChatStore';
import { useStreamingChat } from '../../hooks/useStreamingChat';

export function ChatInterface() {
  const { messages } = useChatStore();
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { sendMessage } = useStreamingChat();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    sendMessage(inputValue);
    setInputValue('');
  };

  const formatTimestamp = (timestamp: Date) => {
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(timestamp);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 border-b">
        <div className="flex items-center gap-3">
          <div className="size-10 bg-white/20 rounded-full flex items-center justify-center">
            <Bot className="size-6" />
          </div>
          <div>
            <h2 className="text-lg">AI Assistant</h2>
            <div className="text-sm text-blue-100">Your intelligent audit assistant</div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <Bot className="size-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-2">Ask me anything about your audit</p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-2xl ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
              <div className={`flex items-center gap-2 mb-1 ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.sender === 'ai' && (
                  <div className="size-6 bg-blue-600 rounded-full flex items-center justify-center">
                    <Bot className="size-4 text-white" />
                  </div>
                )}
                <span className="text-xs text-gray-600">
                  {message.sender === 'user' ? 'You' : 'AI Assistant'}
                </span>
                <span className="text-xs text-gray-400">
                  {formatTimestamp(message.timestamp)}
                </span>
                {message.sender === 'user' && (
                  <div className="size-6 bg-gray-600 rounded-full flex items-center justify-center">
                    <User className="size-4 text-white" />
                  </div>
                )}
              </div>

              <div
                className={`rounded-lg p-4 ${
                  message.sender === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200'
                }`}
              >
                <div className={`whitespace-pre-wrap text-sm leading-relaxed ${message.streaming ? 'italic text-gray-500' : ''}`}>
                  {message.content}
                </div>
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="size-5" />
            Send
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Ask questions, request reports, or get insights about your audit
        </div>
      </div>
    </div>
  );
}
