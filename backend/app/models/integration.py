"""
Integration models for third-party service data and webhook management.

This module defines models for storing data from Gmail, Google Calendar,
and HubSpot, as well as managing webhooks and sync status.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class IntegrationAccount(Base):
    """
    Integration account model for storing third-party service account information.
    
    This model represents connected accounts from Gmail, Google Calendar, and HubSpot,
    including OAuth tokens and account metadata.
    """
    
    __tablename__ = "integration_accounts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Integration information
    service = Column(String(50), nullable=False, index=True)  # 'gmail', 'calendar', 'hubspot'
    account_id = Column(String(255), nullable=False, index=True)  # Account ID from the service
    account_email = Column(String(255), nullable=True, index=True)
    account_name = Column(String(255), nullable=True)
    
    # OAuth tokens (encrypted)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_connected = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    
    # Account metadata
    account_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    disconnected_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    webhooks = relationship("Webhook", back_populates="account", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="account", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_integration_accounts_user_service", "user_id", "service"),
        Index("idx_integration_accounts_active", "is_active"),
        Index("idx_integration_accounts_connected", "is_connected"),
    )
    
    def __repr__(self) -> str:
        return f"<IntegrationAccount(id={self.id}, service={self.service}, account_id={self.account_id})>"
    
    @property
    def has_valid_token(self) -> bool:
        """Check if the account has a valid access token."""
        if not self.access_token:
            return False
        if self.token_expires_at is None:
            return True  # Token doesn't expire
        return datetime.utcnow() < self.token_expires_at
    
    @property
    def needs_token_refresh(self) -> bool:
        """Check if the token needs to be refreshed."""
        if not self.token_expires_at:
            return False
        # Refresh if token expires within 5 minutes
        return datetime.utcnow() > (self.token_expires_at - datetime.timedelta(minutes=5))
    
    def to_dict(self) -> dict:
        """Convert account to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "service": self.service,
            "account_id": self.account_id,
            "account_email": self.account_email,
            "account_name": self.account_name,
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "has_valid_token": self.has_valid_token,
            "needs_token_refresh": self.needs_token_refresh,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "sync_error": self.sync_error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
        }


class Webhook(Base):
    """
    Webhook model for managing third-party service webhooks.
    
    This model represents webhooks from Gmail, Google Calendar, and HubSpot
    that notify the system of changes and events.
    """
    
    __tablename__ = "webhooks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to integration account
    account_id = Column(UUID(as_uuid=True), ForeignKey("integration_accounts.id"), nullable=False, index=True)
    
    # Webhook information
    webhook_id = Column(String(255), nullable=False, index=True)  # Webhook ID from the service
    webhook_url = Column(Text, nullable=False)
    event_types = Column(JSON, nullable=False, default=list)  # Types of events to receive
    
    # Webhook status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    
    # Webhook metadata
    webhook_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_received_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("IntegrationAccount", back_populates="webhooks")
    webhook_events = relationship("WebhookEvent", back_populates="webhook", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_webhooks_account_active", "account_id", "is_active"),
        Index("idx_webhooks_verified", "is_verified"),
    )
    
    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, account_id={self.account_id}, webhook_id={self.webhook_id})>"
    
    def to_dict(self) -> dict:
        """Convert webhook to dictionary representation."""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "webhook_id": self.webhook_id,
            "webhook_url": self.webhook_url,
            "event_types": self.event_types,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_received_at": self.last_received_at.isoformat() if self.last_received_at else None,
        }


class WebhookEvent(Base):
    """
    Webhook event model for storing received webhook events.
    
    This model represents individual webhook events received from third-party
    services, including their payload and processing status.
    """
    
    __tablename__ = "webhook_events"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to webhook
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False, index=True)
    
    # Event information
    event_id = Column(String(255), nullable=False, index=True)  # Event ID from the service
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False, default=dict)
    
    # Processing status
    status = Column(String(20), nullable=False, default="pending", index=True)  # 'pending', 'processing', 'completed', 'failed'
    processing_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Event metadata
    headers = Column(JSON, nullable=True, default=dict)
    source_ip = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="webhook_events")
    
    # Indexes
    __table_args__ = (
        Index("idx_webhook_events_webhook_status", "webhook_id", "status"),
        Index("idx_webhook_events_type", "event_type"),
        Index("idx_webhook_events_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, webhook_id={self.webhook_id}, type={self.event_type})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if the event is pending processing."""
        return self.status == "pending"
    
    @property
    def is_processing(self) -> bool:
        """Check if the event is being processed."""
        return self.status == "processing"
    
    @property
    def is_completed(self) -> bool:
        """Check if the event processing is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if the event processing failed."""
        return self.status == "failed"
    
    def to_dict(self) -> dict:
        """Convert event to dictionary representation."""
        return {
            "id": str(self.id),
            "webhook_id": str(self.webhook_id),
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "status": self.status,
            "processing_error": self.processing_error,
            "retry_count": self.retry_count,
            "headers": self.headers,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class SyncLog(Base):
    """
    Sync log model for tracking data synchronization with third-party services.
    
    This model provides detailed logging of data synchronization operations
    between the application and external services.
    """
    
    __tablename__ = "sync_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to integration account
    account_id = Column(UUID(as_uuid=True), ForeignKey("integration_accounts.id"), nullable=False, index=True)
    
    # Sync information
    sync_type = Column(String(50), nullable=False, index=True)  # 'full', 'incremental', 'manual'
    sync_status = Column(String(20), nullable=False, default="pending", index=True)  # 'pending', 'running', 'completed', 'failed'
    
    # Sync data
    items_processed = Column(Integer, default=0, nullable=False)
    items_created = Column(Integer, default=0, nullable=False)
    items_updated = Column(Integer, default=0, nullable=False)
    items_deleted = Column(Integer, default=0, nullable=False)
    items_failed = Column(Integer, default=0, nullable=False)
    
    # Sync metadata
    sync_config = Column(JSON, nullable=True, default=dict)
    sync_results = Column(JSON, nullable=True, default=dict)
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    duration_seconds = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("IntegrationAccount", back_populates="sync_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_sync_logs_account_status", "account_id", "sync_status"),
        Index("idx_sync_logs_type", "sync_type"),
        Index("idx_sync_logs_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, account_id={self.account_id}, type={self.sync_type})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if the sync is pending."""
        return self.sync_status == "pending"
    
    @property
    def is_running(self) -> bool:
        """Check if the sync is running."""
        return self.sync_status == "running"
    
    @property
    def is_completed(self) -> bool:
        """Check if the sync is completed."""
        return self.sync_status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if the sync failed."""
        return self.sync_status == "failed"
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the sync."""
        if self.items_processed == 0:
            return 0.0
        successful_items = self.items_created + self.items_updated + self.items_deleted
        return successful_items / self.items_processed
    
    def to_dict(self) -> dict:
        """Convert sync log to dictionary representation."""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "sync_type": self.sync_type,
            "sync_status": self.sync_status,
            "items_processed": self.items_processed,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_deleted": self.items_deleted,
            "items_failed": self.items_failed,
            "success_rate": self.success_rate,
            "sync_config": self.sync_config,
            "sync_results": self.sync_results,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }