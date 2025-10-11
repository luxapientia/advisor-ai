import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useAuth } from '../hooks/useAuth';
import { authService } from '../services/auth';
import { chatService } from '../services/chat';
import { googleSyncService } from '../services/googleSync';
import { hubspotSyncService } from '../services/hubspotSync';
import { ChatMessage } from '../types';
import ChatMessageComponent from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import ChatHeader from '../components/ChatHeader';
import ChatSidebar from '../components/ChatSidebar';
import ChatEmptyState from '../components/ChatEmptyState';
import ContextBar from '../components/ContextBar';
import LoadingSpinner from '../components/LoadingSpinner';
import IntegrationsSyncModal from '../components/IntegrationsSyncModal';
import toast from 'react-hot-toast';
import { ChatSession } from '../types';

const Chat: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();
  const [connectingHubSpot, setConnectingHubSpot] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true); // Sidebar open by default on desktop
  const [showIntegrationsSyncModal, setShowIntegrationsSyncModal] = useState(false);
  const [syncChecked, setSyncChecked] = useState(false);
  
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

  // Handle HubSpot connection/disconnection
  const handleConnectHubSpot = async () => {
    try {
      setConnectingHubSpot(true);
      
      if (user?.has_hubspot_access) {
        // Disconnect HubSpot
        await authService.disconnectHubSpot();
        toast.success('HubSpot disconnected successfully');
        // Refresh user data to update the UI
        await refreshUser();
      } else {
        // Connect HubSpot
        const response = await authService.getHubSpotAuthUrl();
        const { authorization_url } = response;
        
        // Redirect to HubSpot OAuth
        window.location.href = authorization_url;
      }
    } catch (error) {
      console.error('Failed to handle HubSpot:', error);
      const action = user?.has_hubspot_access ? 'disconnect' : 'connect';
      toast.error(`Failed to ${action} HubSpot. Please try again.`);
    } finally {
      setConnectingHubSpot(false);
    }
  };

  // Check integrations sync status and show modal if needed
  useEffect(() => {
    const checkIntegrationsSync = async () => {
      if (!user || syncChecked) return;
      
      try {
        const [googleStatus, hubspotStatus] = await Promise.all([
          googleSyncService.getSyncStatus(),
          hubspotSyncService.getSyncStatus()
        ]);
        
        // Show modal if user has access to any service and modal is not already open
        if ((googleStatus.has_google_access || hubspotStatus.has_hubspot_access) && !showIntegrationsSyncModal) {
          setShowIntegrationsSyncModal(true);
        }
        setSyncChecked(true);
      } catch (error) {
        console.error('Failed to check integrations sync status:', error);
        setSyncChecked(true);
      }
    };

    checkIntegrationsSync();
  }, [user, syncChecked, showIntegrationsSyncModal]);

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      if (!user) return; // Don't load sessions if user is not authenticated
      
      try {
        const sessionsData = await chatService.getSessions();
        setSessions(sessionsData);
      } catch (error) {
        console.error('Failed to load sessions:', error);
        toast.error('Failed to load chat sessions');
      }
    };

    loadSessions();
  }, [user, setSessions]);

  // Load specific session or most recent session
  const loadSession = useCallback(async () => {
    if (!user) return; // Don't load session if user is not authenticated
    
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
  }, [user, sessionId, navigate, setCurrentSession, setMessages, setLoading]);

  // Handle session selection from sidebar
  const handleSessionSelect = useCallback((session: ChatSession) => {
    navigate(`/chat/${session.id}`);
  }, [navigate]);

  // Load session when sessionId changes
  useEffect(() => {
    loadSession();
  }, [loadSession]);

  // Create new session
  const createNewSession = useCallback(async () => {
    if (!user) return; // Don't create session if user is not authenticated
    
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
  }, [user, setCurrentSession, setSessions, setMessages, navigate, setLoading]);

  // Handle sending messages
  const handleSendMessage = async (content: string) => {
    if (!currentSession || !content.trim()) {
      console.log('Cannot send message:', { currentSession, content });
      return;
    }

    console.log('Sending message:', { sessionId: currentSession.id, content });

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content: content.trim(),
      is_streaming: false,
      is_complete: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {},
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
      metadata: {},
    };
    addMessage(assistantMessage);

    try {
      await chatService.sendStreamingMessage(
        currentSession.id,
        content,
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

  // Handle session updates from sidebar
  const handleSessionsUpdate = async () => {
    if (!user) return; // Don't update sessions if user is not authenticated
    
    try {
      const sessionsData = await chatService.getSessions();
      setSessions(sessionsData);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast.error('Failed to load chat sessions');
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      toast.error('Logout failed. Please try again.');
    }
  };

  if (isLoading && !currentSession) {
    return <LoadingSpinner />;
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        currentSession={currentSession}
        onNewChat={createNewSession}
        onSessionsUpdate={handleSessionsUpdate}
        isOpen={showSidebar}
        onClose={() => setShowSidebar(false)}
        onSessionSelect={handleSessionSelect}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <ChatHeader
          onLogout={handleLogout}
          hasHubSpotAccess={user?.has_hubspot_access || false}
          onConnectHubSpot={handleConnectHubSpot}
          connectingHubSpot={connectingHubSpot}
          user={user}
          onSidebarToggle={() => setShowSidebar(!showSidebar)}
        />

        {/* Context Bar */}
        <ContextBar
          hasGoogleAccess={user?.has_google_access || false}
          hasHubSpotAccess={user?.has_hubspot_access || false}
        />
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <ChatEmptyState />
          ) : (
            <div className="p-4 space-y-4">
              {messages.map((message) => (
                <ChatMessageComponent
                  key={message.id}
                  message={message}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            placeholder="Ask me anything about your emails, calendar, or contacts..."
          />
        </div>
      </div>

      {/* Integrations Sync Modal */}
      <IntegrationsSyncModal
        isOpen={showIntegrationsSyncModal}
        onSyncComplete={() => {
          setShowIntegrationsSyncModal(false);
        }}
      />
    </div>
  );
};

export default Chat;