import { useState, useRef, useEffect } from 'react';
import { X, ArrowUpRight, Send, Sparkles } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AskAIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  context?: string;
  onOpenInMainChat?: () => void;
}

export function AskAIDrawer({
  isOpen,
  onClose,
  context,
  onOpenInMainChat
}: AskAIDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    setTimeout(() => {
      const aiResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `I understand your question about "${inputValue}". ${
          context ? `Given the context of ${context}, ` : ''
        }I can help you with that.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiResponse]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleOpenInMainChat = () => {
    if (onOpenInMainChat) {
      onOpenInMainChat();
    }
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 md:hidden transition-opacity duration-300"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <div
        className={`
          fixed z-50 bg-white shadow-2xl
          transition-transform duration-300 ease-in-out
          flex flex-col
          md:right-0 md:top-0 md:h-full md:w-[400px]
          max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:h-[60vh] max-md:rounded-t-2xl
          ${
            isOpen
              ? 'md:translate-x-0 max-md:translate-y-0'
              : 'md:translate-x-full max-md:translate-y-full'
          }
        `}
        role="dialog"
        aria-label="AI Assistant Drawer"
        aria-modal="true"
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-600" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">Ask AI</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close AI drawer"
          >
            <X className="w-5 h-5 text-gray-500" aria-hidden="true" />
          </button>
        </div>

        {context && (
          <div className="px-4 py-3 bg-blue-50 border-b border-blue-100">
            <div className="flex items-start gap-2">
              <div className="mt-0.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-blue-900 mb-0.5">
                  Context
                </p>
                <p className="text-sm text-blue-700 break-words">{context}</p>
              </div>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <Sparkles
                className="w-12 h-12 text-gray-300 mb-3"
                aria-hidden="true"
              />
              <p className="text-sm font-medium text-gray-900 mb-1">
                How can I help?
              </p>
              <p className="text-xs text-gray-500">
                Ask me anything about your workspace
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`
                    max-w-[85%] rounded-lg px-4 py-2.5
                    ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-gray-200 text-gray-900'
                    }
                  `}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  <p
                    className={`text-xs mt-1.5 ${
                      message.role === 'user'
                        ? 'text-blue-100'
                        : 'text-gray-500'
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg px-4 py-2.5">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.1s' }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-gray-200 bg-white space-y-3">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question..."
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              disabled={isLoading}
              aria-label="Message input"
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>

          {onOpenInMainChat && (
            <button
              onClick={handleOpenInMainChat}
              className="w-full px-4 py-2.5 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors flex items-center justify-center gap-2"
              aria-label="Open in main chat"
            >
              <ArrowUpRight className="w-4 h-4" aria-hidden="true" />
              Open in Main Chat
            </button>
          )}
        </div>
      </div>
    </>
  );
}
