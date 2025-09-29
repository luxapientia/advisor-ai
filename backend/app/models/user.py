"""
User model and related database schemas.

This module defines the User model and related tables for user management,
authentication, and profile information.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    """
    User model for storing user information and authentication data.
    
    This model represents a user in the system and includes information
    from both Google OAuth and HubSpot OAuth integrations.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic user information
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # OAuth provider information
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    hubspot_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # OAuth tokens (encrypted)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expires_at = Column(DateTime, nullable=True)
    
    hubspot_access_token = Column(Text, nullable=True)
    hubspot_refresh_token = Column(Text, nullable=True)
    hubspot_token_expires_at = Column(DateTime, nullable=True)
    
    # User preferences and settings
    preferences = Column(JSON, nullable=True, default=dict)
    
    # Service sync statuses - generic design for all services
    google_sync_status = Column(String(20), default="none", nullable=False)  # 'none', 'pending', 'syncing', 'completed', 'error'
    hubspot_sync_status = Column(String(20), default="none", nullable=False)  # 'none', 'pending', 'syncing', 'completed', 'error'
    
    # Sync completion timestamps
    google_sync_completed_at = Column(DateTime, nullable=True)
    hubspot_sync_completed_at = Column(DateTime, nullable=True)
    
    # Sync error messages
    google_sync_error = Column(Text, nullable=True)
    hubspot_sync_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    ongoing_instructions = relationship("OngoingInstruction", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def display_name(self) -> str:
        """Get the user's display name."""
        if self.full_name:
            return self.full_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.email.split("@")[0]
    
    @property
    def has_google_access(self) -> bool:
        """Check if user has valid Google OAuth access."""
        return (
            self.google_access_token is not None and
            self.google_token_expires_at is not None and
            self.google_token_expires_at > datetime.utcnow()
        )
    
    @property
    def has_hubspot_access(self) -> bool:
        """Check if user has valid HubSpot OAuth access."""
        return (
            self.hubspot_access_token is not None and
            self.hubspot_token_expires_at is not None and
            self.hubspot_token_expires_at > datetime.utcnow()
        )
    
    @property
    def google_sync_needed(self) -> bool:
        """Check if Google sync is needed."""
        return (
            self.has_google_access and
            self.google_sync_status in ["none", "error", "completed"]
        )
    
    @property
    def google_sync_in_progress(self) -> bool:
        """Check if Google sync is currently running."""
        return self.google_sync_status == "syncing"
    
    @property
    def google_sync_completed(self) -> bool:
        """Check if Google sync has been completed."""
        return self.google_sync_status == "completed"
    
    @property
    def hubspot_sync_needed(self) -> bool:
        """Check if HubSpot sync is needed."""
        return (
            self.has_hubspot_access and
            self.hubspot_sync_status in ["none", "error"]
        )
    
    @property
    def hubspot_sync_in_progress(self) -> bool:
        """Check if HubSpot sync is currently running."""
        return self.hubspot_sync_status == "syncing"
    
    @property
    def hubspot_sync_completed(self) -> bool:
        """Check if HubSpot sync has been completed."""
        return self.hubspot_sync_status == "completed"
    
    def to_dict(self) -> dict:
        """Convert user to dictionary representation."""
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "has_google_access": self.has_google_access,
            "has_hubspot_access": self.has_hubspot_access,
            "google_sync_status": self.google_sync_status,
            "google_sync_completed_at": self.google_sync_completed_at.isoformat() if self.google_sync_completed_at else None,
            "google_sync_error": self.google_sync_error,
            "hubspot_sync_status": self.hubspot_sync_status,
            "hubspot_sync_completed_at": self.hubspot_sync_completed_at.isoformat() if self.hubspot_sync_completed_at else None,
            "hubspot_sync_error": self.hubspot_sync_error,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class UserSession(Base):
    """
    User session model for tracking active sessions and JWT tokens.
    
    This model helps with session management and token revocation.
    """
    
    __tablename__ = "user_sessions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Session information
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert session to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }