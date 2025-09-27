"""
Chat models for conversation management and message storage.

This module defines models for chat sessions, messages, and related
conversation data for the AI assistant.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class ChatSession(Base):
    """
    Chat session model for grouping related messages.
    
    Each chat session represents a conversation thread between
    a user and the AI assistant.
    """
    
    __tablename__ = "chat_sessions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session information
    title = Column(String(255), nullable=True)
    context = Column(JSON, nullable=True, default=dict)  # RAG context, filters, etc.
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
    
    @property
    def message_count(self) -> int:
        """Get the number of messages in this session."""
        return len(self.messages) if self.messages else 0
    
    def to_dict(self) -> dict:
        """Convert session to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "context": self.context,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }


class ChatMessage(Base):
    """
    Chat message model for storing individual messages in conversations.
    
    This model stores both user messages and AI responses, including
    metadata about the message content and any actions taken.
    """
    
    __tablename__ = "chat_messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    
    # Message information
    role = Column(String(20), nullable=False, index=True)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    
    # Message metadata
    message_type = Column(String(50), nullable=True)  # 'text', 'action', 'error', etc.
    message_metadata = Column(JSON, nullable=True, default=dict)
    
    # AI-specific fields
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # RAG context
    context_sources = Column(JSON, nullable=True)  # Sources used for RAG
    context_embeddings = Column(JSON, nullable=True)  # Embedding metadata
    
    # Tool calling
    tools_called = Column(JSON, nullable=True)  # Tools invoked by the AI
    tool_results = Column(JSON, nullable=True)  # Results from tool calls
    
    # Message status
    is_streaming = Column(Boolean, default=False, nullable=False)
    is_complete = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role}, session_id={self.session_id})>"
    
    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == "user"
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == "assistant"
    
    @property
    def is_system_message(self) -> bool:
        """Check if this is a system message."""
        return self.role == "system"
    
    @property
    def has_tools(self) -> bool:
        """Check if this message involved tool calls."""
        return self.tools_called is not None and len(self.tools_called) > 0
    
    @property
    def has_context(self) -> bool:
        """Check if this message used RAG context."""
        return self.context_sources is not None and len(self.context_sources) > 0
    
    def to_dict(self) -> dict:
        """Convert message to dictionary representation."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "processing_time_ms": self.processing_time_ms,
            "context_sources": self.context_sources,
            "tools_called": self.tools_called,
            "tool_results": self.tool_results,
            "is_streaming": self.is_streaming,
            "is_complete": self.is_complete,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatContext(Base):
    """
    Chat context model for storing RAG context and conversation state.
    
    This model helps maintain context across conversations and
    provides persistent storage for RAG-related data.
    """
    
    __tablename__ = "chat_contexts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to session
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    
    # Context information
    context_type = Column(String(50), nullable=False)  # 'rag', 'memory', 'instruction', etc.
    context_data = Column(JSON, nullable=False)
    
    # Context metadata
    source = Column(String(100), nullable=True)  # 'gmail', 'hubspot', 'calendar', etc.
    relevance_score = Column(Integer, nullable=True)  # 0-100 relevance score
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("ChatSession")
    
    def __repr__(self) -> str:
        return f"<ChatContext(id={self.id}, type={self.context_type}, session_id={self.session_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the context is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert context to dictionary representation."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "context_type": self.context_type,
            "context_data": self.context_data,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }