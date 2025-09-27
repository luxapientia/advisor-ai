import { apiClient, streamChatMessage } from './api';
import { ChatSession, ChatMessage, ChatMessageForm } from '../types';

export const chatService = {
  // Create new chat session
  createSession: async (): Promise<ChatSession> => {
    return apiClient.post<ChatSession>('/chat/sessions');
  },

  // Get user's chat sessions
  getSessions: async (): Promise<ChatSession[]> => {
    return apiClient.get<ChatSession[]>('/chat/sessions');
  },

  // Get specific chat session
  getSession: async (sessionId: string): Promise<ChatSession> => {
    return apiClient.get<ChatSession>(`/chat/sessions/${sessionId}`);
  },

  // Get chat history for a session
  getChatHistory: async (sessionId: string): Promise<{ session_id: string; messages: ChatMessage[] }> => {
    return apiClient.get<{ session_id: string; messages: ChatMessage[] }>(`/chat/sessions/${sessionId}/messages`);
  },

  // Send message (non-streaming)
  sendMessage: async (sessionId: string, message: ChatMessageForm): Promise<ChatMessage> => {
    return apiClient.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, message);
  },

  // Send message with streaming
  sendStreamingMessage: async (
    sessionId: string,
    message: string,
    onChunk: (chunk: any) => void,
    onComplete: () => void,
    onError: (error: any) => void
  ) => {
    return streamChatMessage(sessionId, message, onChunk, onComplete, onError);
  },

  // Delete chat session
  deleteSession: async (sessionId: string): Promise<void> => {
    return apiClient.delete(`/chat/sessions/${sessionId}`);
  },

  // Update session context
  updateSessionContext: async (sessionId: string, context: Record<string, any>): Promise<ChatSession> => {
    return apiClient.put<ChatSession>(`/chat/sessions/${sessionId}/context`, { context });
  },
};