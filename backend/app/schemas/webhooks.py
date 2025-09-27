"""
Webhook schemas for request/response validation.

This module defines Pydantic models for webhook-related
API requests and responses, including event processing.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class WebhookEventResponse(BaseModel):
    """Response schema for webhook event."""
    
    id: str = Field(..., description="Event ID")
    webhook_id: str = Field(..., description="Webhook ID")
    event_id: str = Field(..., description="Event ID from service")
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    status: str = Field(..., description="Processing status")
    processing_error: Optional[str] = Field(None, description="Processing error")
    retry_count: int = Field(..., description="Retry count")
    headers: Optional[Dict[str, Any]] = Field(None, description="Request headers")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "webhook_id": "123e4567-e89b-12d3-a456-426614174001",
                "event_id": "gmail_msg_123456789",
                "event_type": "message_created",
                "event_data": {
                    "messageId": "msg_123456789",
                    "threadId": "thread_123",
                    "labelIds": ["INBOX"]
                },
                "status": "completed",
                "processing_error": None,
                "retry_count": 0,
                "headers": {
                    "content-type": "application/json",
                    "user-agent": "Gmail-Webhook/1.0"
                },
                "source_ip": "192.168.1.1",
                "user_agent": "Gmail-Webhook/1.0",
                "created_at": "2024-01-01T00:00:00Z",
                "processed_at": "2024-01-01T00:00:01Z"
            }
        }


class WebhookVerificationRequest(BaseModel):
    """Request schema for webhook verification."""
    
    challenge: str = Field(..., description="Verification challenge")
    token: Optional[str] = Field(None, description="Verification token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "challenge": "verification_challenge_string",
                "token": "verification_token"
            }
        }


class WebhookVerificationResponse(BaseModel):
    """Response schema for webhook verification."""
    
    challenge: str = Field(..., description="Echoed challenge")
    verified: bool = Field(..., description="Verification status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "challenge": "verification_challenge_string",
                "verified": True
            }
        }