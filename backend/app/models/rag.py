"""
RAG (Retrieval-Augmented Generation) models for vector storage and retrieval.

This module defines models for storing embeddings, documents, and metadata
for the RAG pipeline that powers the AI assistant's knowledge base.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base
from app.core.config import settings


class Document(Base):
    """
    Document model for storing source documents and their metadata.
    
    This model represents documents from various sources (Gmail, HubSpot, etc.)
    that are processed and stored for RAG retrieval.
    """
    
    __tablename__ = "documents"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Document information
    source = Column(String(50), nullable=False, index=True)  # 'gmail', 'hubspot', 'calendar'
    source_id = Column(String(255), nullable=False, index=True)  # Original ID from source
    document_type = Column(String(50), nullable=False)  # 'email', 'contact', 'note', 'event'
    
    # Content
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Metadata
    document_metadata = Column(JSON, nullable=True, default=dict)
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    source_created_at = Column(DateTime, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_documents_user_source", "user_id", "source"),
        Index("idx_documents_source_id", "source", "source_id"),
        Index("idx_documents_processed", "is_processed"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, source={self.source}, type={self.document_type})>"
    
    def to_dict(self) -> dict:
        """Convert document to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "source": self.source,
            "source_id": self.source_id,
            "document_type": self.document_type,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "metadata": self.metadata,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source_created_at": self.source_created_at.isoformat() if self.source_created_at else None,
            "source_updated_at": self.source_updated_at.isoformat() if self.source_updated_at else None,
        }


class DocumentChunk(Base):
    """
    Document chunk model for storing text chunks and their embeddings.
    
    This model represents individual chunks of documents that are embedded
    and stored in the vector database for similarity search.
    """
    
    __tablename__ = "document_chunks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to document
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)  # Order within document
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    
    # Vector embedding
    embedding = Column(Vector(settings.VECTOR_DIMENSION), nullable=False)
    
    # Chunk metadata
    chunk_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index("idx_chunks_document_index", "document_id", "chunk_index"),
        Index("idx_chunks_embedding", "embedding", postgresql_using="ivfflat", postgresql_with={"lists": 100}),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"
    
    def to_dict(self) -> dict:
        """Convert chunk to dictionary representation."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "content": self.content,
            "content_length": self.content_length,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QueryCache(Base):
    """
    Query cache model for storing frequently accessed query results.
    
    This model helps improve performance by caching common queries
    and their corresponding context retrieval results.
    """
    
    __tablename__ = "query_cache"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Query information
    query_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash of query
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(settings.VECTOR_DIMENSION), nullable=False)
    
    # Results
    retrieved_chunks = Column(JSON, nullable=False)  # Chunk IDs and scores
    context_summary = Column(Text, nullable=True)
    
    # Cache metadata
    hit_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("idx_query_cache_user_hash", "user_id", "query_hash"),
        Index("idx_query_cache_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<QueryCache(id={self.id}, user_id={self.user_id}, hits={self.hit_count})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert cache entry to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "retrieved_chunks": self.retrieved_chunks,
            "context_summary": self.context_summary,
            "hit_count": self.hit_count,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class EmbeddingJob(Base):
    """
    Embedding job model for tracking document processing jobs.
    
    This model helps manage the asynchronous processing of documents
    and their conversion to embeddings for the RAG pipeline.
    """
    
    __tablename__ = "embedding_jobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Job information
    job_type = Column(String(50), nullable=False)  # 'document_embedding', 'query_embedding', etc.
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    
    # Job data
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("idx_embedding_jobs_user_status", "user_id", "status"),
        Index("idx_embedding_jobs_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<EmbeddingJob(id={self.id}, type={self.job_type}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if the job is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if the job failed."""
        return self.status == "failed"
    
    @property
    def is_processing(self) -> bool:
        """Check if the job is currently processing."""
        return self.status == "processing"
    
    def to_dict(self) -> dict:
        """Convert job to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "job_type": self.job_type,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "progress_percentage": self.progress_percentage,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }