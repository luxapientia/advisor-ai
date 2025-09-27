"""
Integration schemas for request/response validation.

This module defines Pydantic models for integration-related
API requests and responses, including account management and webhooks.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class IntegrationAccountResponse(BaseModel):
    """Response schema for integration account."""
    
    id: str = Field(..., description="Account ID")
    user_id: str = Field(..., description="User ID")
    service: str = Field(..., description="Integration service")
    account_id: str = Field(..., description="Account ID from service")
    account_email: Optional[str] = Field(None, description="Account email")
    account_name: Optional[str] = Field(None, description="Account name")
    is_active: bool = Field(..., description="Whether account is active")
    is_connected: bool = Field(..., description="Whether account is connected")
    has_valid_token: bool = Field(..., description="Whether account has valid token")
    needs_token_refresh: bool = Field(..., description="Whether token needs refresh")
    last_sync_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    sync_error: Optional[str] = Field(None, description="Sync error message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Account metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    connected_at: datetime = Field(..., description="Connection timestamp")
    disconnected_at: Optional[datetime] = Field(None, description="Disconnection timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "service": "google",
                "account_id": "google_account_123",
                "account_email": "user@example.com",
                "account_name": "John Doe",
                "is_active": True,
                "is_connected": True,
                "has_valid_token": True,
                "needs_token_refresh": False,
                "last_sync_at": "2024-01-01T00:00:00Z",
                "sync_error": None,
                "metadata": {
                    "scopes": ["gmail", "calendar"],
                    "permissions": ["read", "write"]
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "connected_at": "2024-01-01T00:00:00Z",
                "disconnected_at": None
            }
        }


class WebhookCreateRequest(BaseModel):
    """Request schema for webhook creation."""
    
    service: str = Field(..., description="Integration service")
    webhook_id: str = Field(..., description="Webhook ID from service")
    webhook_url: str = Field(..., description="Webhook URL")
    event_types: List[str] = Field(..., description="Event types to receive")
    verification_token: Optional[str] = Field(None, description="Verification token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service": "gmail",
                "webhook_id": "webhook_123",
                "webhook_url": "https://api.example.com/webhooks/gmail",
                "event_types": ["message_created", "message_updated"],
                "verification_token": "verify_token_123"
            }
        }


class WebhookResponse(BaseModel):
    """Response schema for webhook."""
    
    id: str = Field(..., description="Webhook ID")
    account_id: str = Field(..., description="Integration account ID")
    webhook_id: str = Field(..., description="Webhook ID from service")
    webhook_url: str = Field(..., description="Webhook URL")
    event_types: List[str] = Field(..., description="Event types")
    is_active: bool = Field(..., description="Whether webhook is active")
    is_verified: bool = Field(..., description="Whether webhook is verified")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Webhook metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    last_received_at: Optional[datetime] = Field(None, description="Last received timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "webhook_id": "webhook_123",
                "webhook_url": "https://api.example.com/webhooks/gmail",
                "event_types": ["message_created", "message_updated"],
                "is_active": True,
                "is_verified": True,
                "metadata": {
                    "secret": "webhook_secret_123"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_received_at": "2024-01-01T00:00:00Z"
            }
        }


class SyncRequest(BaseModel):
    """Request schema for sync trigger."""
    
    service: str = Field(..., description="Integration service")
    sync_type: str = Field(default="manual", description="Sync type")
    config: Optional[Dict[str, Any]] = Field(None, description="Sync configuration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service": "gmail",
                "sync_type": "full",
                "config": {
                    "date_range": "last_30_days",
                    "include_attachments": False
                }
            }
        }


class SyncLogResponse(BaseModel):
    """Response schema for sync log."""
    
    id: str = Field(..., description="Sync log ID")
    account_id: str = Field(..., description="Integration account ID")
    sync_type: str = Field(..., description="Sync type")
    sync_status: str = Field(..., description="Sync status")
    items_processed: int = Field(..., description="Items processed")
    items_created: int = Field(..., description="Items created")
    items_updated: int = Field(..., description="Items updated")
    items_deleted: int = Field(..., description="Items deleted")
    items_failed: int = Field(..., description="Items failed")
    success_rate: float = Field(..., description="Success rate")
    sync_config: Optional[Dict[str, Any]] = Field(None, description="Sync configuration")
    sync_results: Optional[Dict[str, Any]] = Field(None, description="Sync results")
    error_message: Optional[str] = Field(None, description="Error message")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    memory_usage_mb: Optional[int] = Field(None, description="Memory usage in MB")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "sync_type": "full",
                "sync_status": "completed",
                "items_processed": 100,
                "items_created": 50,
                "items_updated": 30,
                "items_deleted": 5,
                "items_failed": 0,
                "success_rate": 1.0,
                "sync_config": {
                    "date_range": "last_30_days"
                },
                "sync_results": {
                    "gmail_messages": 100,
                    "calendar_events": 50
                },
                "error_message": None,
                "duration_seconds": 300,
                "memory_usage_mb": 150,
                "created_at": "2024-01-01T00:00:00Z",
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:00Z"
            }
        }