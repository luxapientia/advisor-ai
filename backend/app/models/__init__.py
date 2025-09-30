"""
Database models package.

This module imports all database models so they can be discovered by Alembic.
"""

# Import all models so they're registered with Base.metadata
from .user import User, UserSession
from .chat import ChatSession, ChatMessage
from .integration import IntegrationAccount, Webhook, SyncLog
from .rag import Document, DocumentChunk
from .task import Task

# Make models available for import
__all__ = [
    "User",
    "UserSession",
    "ChatSession", 
    "ChatMessage",
    "IntegrationAccount",
    "Webhook", 
    "SyncLog",
    "Document",
    "DocumentChunk",
    "Task",
]