import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useAuth } from '../hooks/useAuth';
import { authService } from '../services/auth';
import { chatService } from '../services/chat';
import { googleSyncService } from '../services/googleSync';
import { ChatMessage, ChatSession } from '../types';
import ChatMessageComponent from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import ChatHeader from '../components/ChatHeader';
import ChatSidebar from '../components/ChatSidebar';
import ChatEmptyState from '../components/ChatEmptyState';
import ContextBar from '../components/ContextBar';
import LoadingSpinner from '../components/LoadingSpinner';
import GoogleSyncModal from '../components/GoogleSyncModal';
import toast from 'react-hot-toast';

const Chat: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { user, refreshUser, logout } = useAuth();
  const [connectingHubSpot, setConnectingHubSpot] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true); // Sidebar open by default on desktop
  const [showGoogleSyncModal, setShowGoogleSyncModal] = useState(false);
  
  const {
    currentSession,
    sessions,
    messages,
    isLoading,
    setCurrentSession,
    setSessions,
    setMessages,
    addMessage,
    updateMessage,
    setLoading,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loadedSessionId = useRef<string | null>(null);
  const hasLoadedSession = useRef(false);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle HubSpot OAuth callback
  useEffect(() => {
    const handleHubSpotCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const accessToken = urlParams.get('access_token');
      const refreshToken = urlParams.get('refresh_token');
      const error = urlParams.get('error');

      if (error) {
        toast.error('HubSpot connection failed. Please try again.');
        setConnectingHubSpot(false);
        return;
      }

      if (accessToken && refreshToken) {
        try {
          // Refresh user data to get updated HubSpot access
          await refreshUser();
          toast.success('HubSpot connected successfully!');
        } catch (error) {
          console.error('Failed to refresh user data:', error);
          toast.error('Connection successful but failed to update user data.');
        } finally {
          setConnectingHubSpot(false);
        }
      }
    };

    // Only handle callback if we're connecting HubSpot
    if (connectingHubSpot) {
      handleHubSpotCallback();
    }
  }, [connectingHubSpot, refreshUser]);

  const handleConnectHubSpot = async () => {
    setConnectingHubSpot(true);
    try {
      const { authorization_url } = await authService.getHubSpotAuthUrl();
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate HubSpot connection:', error);
      toast.error('Failed to connect HubSpot. Please try again.');
      setConnectingHubSpot(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSessionSelect = (session: ChatSession) => {
    setCurrentSession(session);
    navigate(`/chat/${session.id}`);
    setShowSidebar(false); // Close sidebar on mobile after selection
  };

  const handleSessionsUpdate = async () => {
    try {
      const sessionsData = await chatService.getSessions();
      setSessions(sessionsData);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast.error('Failed to load chat sessions');
    }
  };

  // Check Google sync status and show modal if needed
  useEffect(() => {
    const checkGoogleSync = async () => {
      if (!user) return;
      
      try {
        const syncStatus = await googleSyncService.getSyncStatus();
        
        // Show modal if sync is needed
        if (syncStatus.needed) {
          setShowGoogleSyncModal(true);
        }
      } catch (error) {
        console.error('Failed to check Google sync status:', error);
      }
    };

    checkGoogleSync();
  }, [user]);

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const sessionsData = await chatService.getSessions();
        setSessions(sessionsData);
      } catch (error) {
        console.error('Failed to load sessions:', error);
        toast.error('Failed to load chat sessions');
      }
    };

    loadSessions();
  }, [setSessions]);

  const createNewSession = useCallback(async () => {
    try {
      setLoading(true);
      const newSession = await chatService.createSession();
      setCurrentSession(newSession);
      setSessions(prev => [newSession, ...prev]);
      setMessages([]);
      navigate(`/chat/${newSession.id}`);
    } catch (error) {
      console.error('Failed to create session:', error);
      toast.error('Failed to create new chat session');
    } finally {
      setLoading(false);
    }
  }, [setCurrentSession, setSessions, setMessages, navigate, setLoading]);

  // Load specific session or most recent session
  const loadSession = useCallback(async () => {
    if (sessionId) {
      // Only load if we haven't already loaded this session
      if (loadedSessionId.current === sessionId) {
        return;
      }
      
      try {
        setLoading(true);
        const session = await chatService.getSession(sessionId);
        setCurrentSession(session);
        
        const history = await chatService.getChatHistory(sessionId);
        setMessages(history.messages);
        
        // Mark this session as loaded
        loadedSessionId.current = sessionId;
      } catch (error) {
        console.error('Failed to load session:', error);
        toast.error('Failed to load chat session');
        navigate('/chat');
      } finally {
        setLoading(false);
      }
    } else {
      // No sessionId - load the most recent session if available
      // Only navigate if we don't already have a current session loaded
      if (!hasLoadedSession.current) {
        hasLoadedSession.current = true;
        chatService.getSessions().then(sessionList => {
          if (sessionList.length > 0) {
            const mostRecentSession = sessionList[0];
            setCurrentSession(mostRecentSession);
            navigate(`/chat/${mostRecentSession.id}`);
          }
        }).catch(error => {
          console.error('Failed to get sessions:', error);
        });
      }
    }
  }, [sessionId, navigate, setCurrentSession, setMessages, setLoading]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const handleSendMessage = async (message: string) => {
    if (!currentSession || !message.trim()) return;

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content: message,
      is_streaming: false,
      is_complete: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    addMessage(userMessage);

    // Create assistant message placeholder
    const assistantMessage: ChatMessage = {
      id: `temp-assistant-${Date.now()}`,
      session_id: currentSession.id,
      role: 'assistant',
      content: '',
      is_streaming: true,
      is_complete: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    addMessage(assistantMessage);

    try {
      await chatService.sendStreamingMessage(
        currentSession.id,
        message,
        (chunk) => {
          if (chunk.type === 'content') {
            updateMessage(assistantMessage.id, {
              content: (assistantMessage.content || '') + chunk.content,
            });
          } else if (chunk.type === 'finish') {
            updateMessage(assistantMessage.id, {
              content: chunk.content,
              is_streaming: false,
              is_complete: true,
              model_used: chunk.model_used,
              tools_called: chunk.tools_called,
            });
          } else if (chunk.type === 'error') {
            updateMessage(assistantMessage.id, {
              content: chunk.content || 'Sorry, I encountered an error.',
              is_streaming: false,
              is_complete: true,
              error_message: chunk.error,
            });
          }
        },
        () => {
          // Stream completed
        },
        (error) => {
          console.error('Streaming error:', error);
          updateMessage(assistantMessage.id, {
            content: 'Sorry, I encountered an error while processing your message.',
            is_streaming: false,
            is_complete: true,
            error_message: error.message,
          });
          toast.error('Failed to send message');
        }
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      updateMessage(assistantMessage.id, {
        content: 'Sorry, I encountered an error while processing your message.',
        is_streaming: false,
        is_complete: true,
        error_message: 'Failed to send message',
      });
      toast.error('Failed to send message');
    }
  };

  if (isLoading && !currentSession) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <ChatHeader
        onLogout={handleLogout}
        hasHubSpotAccess={user?.has_hubspot_access || false}
        onConnectHubSpot={handleConnectHubSpot}
        connectingHubSpot={connectingHubSpot}
        user={user}
        onSidebarToggle={() => setShowSidebar(!showSidebar)}
      />

      {/* Context Information Bar */}
      <ContextBar
        hasGoogleAccess={user?.has_google_access || false}
        hasHubSpotAccess={user?.has_hubspot_access || false}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat Sidebar */}
        <ChatSidebar
          isOpen={showSidebar}
          onClose={() => setShowSidebar(false)}
          sessions={sessions}
          currentSession={currentSession}
          onSessionSelect={handleSessionSelect}
          onNewChat={createNewSession}
          onSessionsUpdate={handleSessionsUpdate}
        />

        {/* Chat Content */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
            {messages.length === 0 ? (
              <ChatEmptyState />
            ) : (
              messages.map((message) => (
                <ChatMessageComponent key={message.id} message={message} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="max-w-4xl mx-auto">
              <ChatInput
                onSendMessage={handleSendMessage}
                disabled={isLoading}
                placeholder="Ask anything about your clients, schedule meetings, or manage your CRM..."
              />
            </div>
          </div>
        </div>
      </div>

      {/* Google Sync Modal */}
      <GoogleSyncModal
        isOpen={showGoogleSyncModal}
        onSyncComplete={() => {
          setShowGoogleSyncModal(false);
        }}
      />
    </div>
  );
};

export default Chat;