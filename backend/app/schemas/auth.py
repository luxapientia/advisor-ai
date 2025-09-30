"""
Authentication schemas for request/response validation.

This module defines Pydantic models for authentication-related
API requests and responses, including OAuth and JWT token handling.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings


class GoogleAuthRequest(BaseModel):
    """Request schema for Google OAuth authorization."""
    
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI (optional, uses configured URI)")
    email: Optional[EmailStr] = Field(None, description="User email for pre-filling")
    



    class Config:
        json_schema_extra = {
            "example": {
                "redirect_uri": f"{settings.FRONTEND_URL}/auth/callback",
                "email": "user@example.com"
            }
        }


class GoogleAuthResponse(BaseModel):
    """Response schema for Google OAuth authorization."""
    
    authorization_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="OAuth state parameter for security")
    



    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://accounts.google.com/oauth/authorize?...",
                "state": "random_state_string"
            }
        }


class HubSpotAuthRequest(BaseModel):
    """Request schema for HubSpot OAuth authorization."""
    
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI (optional, uses configured URI)")
    email: Optional[EmailStr] = Field(None, description="User email for pre-filling")
    



    class Config:
        json_schema_extra = {
            "example": {
                "redirect_uri": f"{settings.FRONTEND_URL}/auth/callback",
                "email": "user@example.com"
            }
        }


class HubSpotAuthResponse(BaseModel):
    """Response schema for HubSpot OAuth authorization."""
    
    authorization_url: str = Field(..., description="HubSpot OAuth authorization URL")
    state: str = Field(..., description="OAuth state parameter for security")
    



    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://app.hubspot.com/oauth/authorize?...",
                "state": "random_state_string"
            }
        }


class UserResponse(BaseModel):
    """Response schema for user information."""
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    full_name: Optional[str] = Field(None, description="User full name")
    display_name: str = Field(..., description="User display name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    has_google_access: bool = Field(..., description="Whether user has Google OAuth access")
    has_hubspot_access: bool = Field(..., description="Whether user has HubSpot OAuth access")
    preferences: Optional[dict] = Field(None, description="User preferences")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    


    @field_validator("id", mode="before")
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
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "full_name": "John Doe",
                "display_name": "John Doe",
                "avatar_url": "https://lh3.googleusercontent.com/...",
                "is_active": True,
                "is_verified": True,
                "has_google_access": True,
                "has_hubspot_access": True,
                "preferences": {
                    "theme": "light",
                    "notifications": True
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-01T00:00:00Z"
            }
        }


class TokenResponse(BaseModel):
    """Response schema for JWT token generation."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")
    



    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "display_name": "John Doe",
                    "is_active": True,
                    "has_google_access": True,
                    "has_hubspot_access": True
                }
            }
        }


class OAuthStateRequest(BaseModel):
    """Request schema for OAuth state validation."""
    
    state: str = Field(..., description="OAuth state parameter")
    code: str = Field(..., description="OAuth authorization code")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    



    class Config:
        json_schema_extra = {
            "example": {
                "state": "random_state_string",
                "code": "authorization_code_from_oauth_provider",
                "redirect_uri": "http://localhost:3000/auth/callback"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    
    refresh_token: str = Field(..., description="JWT refresh token")
    



    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }


class LogoutRequest(BaseModel):
    """Request schema for user logout."""
    
    refresh_token: Optional[str] = Field(None, description="JWT refresh token to invalidate")
    



    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }