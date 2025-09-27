"""
User schemas for request/response validation.

This module defines Pydantic models for user-related
API requests and responses, including profile management and preferences.
"""

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""
    
    first_name: Optional[str] = Field(None, description="User first name", max_length=100)
    last_name: Optional[str] = Field(None, description="User last name", max_length=100)
    full_name: Optional[str] = Field(None, description="User full name", max_length=200)
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }


class UserPreferencesRequest(BaseModel):
    """Request schema for updating user preferences."""
    
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferences": {
                    "theme": "light",
                    "notifications": {
                        "email": True,
                        "push": False
                    },
                    "chat": {
                        "streaming": True,
                        "context_length": 5
                    },
                    "integrations": {
                        "auto_sync": True,
                        "sync_interval": 3600
                    }
                }
            }
        }


class UserIntegrationStatus(BaseModel):
    """Response schema for user integration status."""
    
    service: str = Field(..., description="Integration service name")
    connected: bool = Field(..., description="Whether integration is connected")
    email: Optional[str] = Field(None, description="Connected email address")
    scopes: list[str] = Field(..., description="Connected scopes")
    last_sync: Optional[str] = Field(None, description="Last sync timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service": "google",
                "connected": True,
                "email": "user@example.com",
                "scopes": ["gmail", "calendar"],
                "last_sync": "2024-01-01T00:00:00Z"
            }
        }