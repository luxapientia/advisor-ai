import React from 'react';
import { ChatMessage as ChatMessageType } from '../types';
import { User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: ChatMessageType;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isStreaming = message.is_streaming && !message.is_complete;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} message-enter`}>
      <div className={`flex max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
            isUser 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-200 text-gray-600'
          }`}>
            {isUser ? (
              <User className="h-4 w-4" />
            ) : (
              <Bot className="h-4 w-4" />
            )}
          </div>
        </div>

        {/* Message content */}
        <div className={`flex-1 ${isUser ? 'text-right' : 'text-left'}`}>
          <div className={`inline-block px-4 py-2 rounded-lg ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-gray-200 text-gray-900'
          }`}>
            {isAssistant && isStreaming ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-gray-500">Thinking...</span>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none">
                {isAssistant ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    className="markdown-content"
                  >
                    {message.content}
                  </ReactMarkdown>
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}
              </div>
            )}
          </div>

          {/* Message metadata */}
          <div className={`mt-1 text-xs text-gray-500 ${isUser ? 'text-right' : 'text-left'}`}>
            {new Date(message.created_at).toLocaleTimeString()}
            {message.model_used && (
              <span className="ml-2">• {message.model_used}</span>
            )}
            {message.tokens_used && (
              <span className="ml-2">• {message.tokens_used} tokens</span>
            )}
            {message.processing_time_ms && (
              <span className="ml-2">• {message.processing_time_ms}ms</span>
            )}
          </div>

          {/* Context sources */}
          {message.context_sources && message.context_sources.length > 0 && (
            <div className="mt-2 text-xs text-gray-500">
              <span className="font-medium">Sources:</span> {message.context_sources.join(', ')}
            </div>
          )}

          {/* Tool calls */}
          {message.tools_called && message.tools_called.length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-gray-500 mb-1">Tools used:</div>
              <div className="flex flex-wrap gap-1">
                {message.tools_called.map((tool, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {tool.function.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Error message */}
          {message.error_message && (
            <div className="mt-2 text-xs text-red-600">
              Error: {message.error_message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;