"""
Chat schemas for request/response validation.

This module defines Pydantic models for chat-related
API requests and responses, including messages and sessions.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""
    
    message: str = Field(..., description="Message content", min_length=1, max_length=4000)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Who mentioned their kid plays baseball?",
                "context": {
                    "sources": ["gmail", "hubspot"],
                    "date_range": "last_month"
                }
            }
        }


class ChatMessageResponse(BaseModel):
    """Response schema for chat messages."""
    
    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    message_type: Optional[str] = Field(None, description="Type of message")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    model_used: Optional[str] = Field(None, description="AI model used for generation")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    context_sources: Optional[List[str]] = Field(None, description="Sources used for context")
    tools_called: Optional[List[Dict[str, Any]]] = Field(None, description="Tools called by the AI")
    is_streaming: bool = Field(default=False, description="Whether message is being streamed")
    is_complete: bool = Field(default=True, description="Whether message is complete")
    error_message: Optional[str] = Field(None, description="Error message if any")
    created_at: datetime = Field(..., description="Message creation timestamp")
    updated_at: datetime = Field(..., description="Message update timestamp")
    
    @field_validator("id", "session_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    @field_validator("message_metadata", mode="before")
    @classmethod
    def convert_metadata_to_dict(cls, v):
        """Convert MetaData object to dict if needed."""
        if hasattr(v, '__dict__'):
            return v.__dict__
        return v
    
    @field_validator("context_sources", mode="before")
    @classmethod
    def filter_none_context_sources(cls, v):
        """Filter out None values from context_sources list."""
        if v is None:
            return None
        if isinstance(v, list):
            # Filter out None values and ensure all items are strings
            filtered = [item for item in v if item is not None and isinstance(item, str)]
            return filtered if filtered else None
        return v
    
    class Config:
        from_attributes = True
        protected_namespaces = ()  # Allow fields starting with "model_"
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "role": "assistant",
                "content": "I found that John Smith mentioned his kid plays baseball in an email from last week.",
                "message_type": "text",
                "message_metadata": {},
                "model_used": "gpt-4.1",
                "tokens_used": 150,
                "processing_time_ms": 1200,
                "context_sources": ["gmail", "hubspot"],
                "tools_called": None,
                "is_streaming": False,
                "is_complete": True,
                "error_message": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class ChatSessionResponse(BaseModel):
    """Response schema for chat sessions."""
    
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Session title")
    context: Optional[Dict[str, Any]] = Field(None, description="Session context")
    is_active: bool = Field(..., description="Whether session is active")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session update timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")
    
    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Client Meeting Discussion",
                "context": {
                    "sources": ["gmail", "hubspot", "calendar"],
                    "filters": {
                        "date_range": "last_month",
                        "contacts": ["john@example.com", "jane@example.com"]
                    }
                },
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_message_at": "2024-01-01T00:00:00Z"
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""
    
    session_id: str = Field(..., description="Chat session ID")
    messages: List[ChatMessageResponse] = Field(..., description="List of messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "messages": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174002",
                        "session_id": "123e4567-e89b-12d3-a456-426614174001",
                        "role": "user",
                        "content": "Who mentioned their kid plays baseball?",
                        "message_type": "text",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    },
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174003",
                        "session_id": "123e4567-e89b-12d3-a456-426614174001",
                        "role": "assistant",
                        "content": "I found that John Smith mentioned his kid plays baseball in an email from last week.",
                        "message_type": "text",
                        "model_used": "gpt-4.1",
                        "tokens_used": 150,
                        "context_sources": ["gmail", "hubspot"],
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ]
            }
        }


class StreamResponse(BaseModel):
    """Response schema for streaming chat responses."""
    
    type: str = Field(..., description="Type of stream event (content, finish, error)")
    content: Optional[str] = Field(None, description="Streamed content")
    role: Optional[str] = Field(None, description="Message role")
    message_id: Optional[str] = Field(None, description="Message ID for finish event")
    model_used: Optional[str] = Field(None, description="AI model used")
    tools_called: Optional[List[Dict[str, Any]]] = Field(None, description="Tools called by the AI")
    error: Optional[str] = Field(None, description="Error message for error event")
    finish_reason: Optional[str] = Field(None, description="Reason for finishing")
    
    class Config:
        protected_namespaces = ()  # Allow fields starting with "model_"
        json_schema_extra = {
            "example": {
                "type": "content",
                "content": "I found that John Smith mentioned his kid plays baseball",
                "role": "assistant"
            }
        }


class ChatContextRequest(BaseModel):
    """Request schema for updating chat context."""
    
    context: Dict[str, Any] = Field(..., description="Context data to update")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context": {
                    "sources": ["gmail", "hubspot"],
                    "filters": {
                        "date_range": "last_month",
                        "contacts": ["john@example.com"]
                    }
                }
            }
        }


class ChatContextResponse(BaseModel):
    """Response schema for chat context."""
    
    session_id: str = Field(..., description="Chat session ID")
    context: Dict[str, Any] = Field(..., description="Updated context data")
    updated_at: datetime = Field(..., description="Context update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "context": {
                    "sources": ["gmail", "hubspot"],
                    "filters": {
                        "date_range": "last_month",
                        "contacts": ["john@example.com"]
                    }
                },
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }