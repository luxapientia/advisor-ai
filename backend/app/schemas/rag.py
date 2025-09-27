"""
RAG schemas for request/response validation.

This module defines Pydantic models for RAG-related
API requests and responses, including document ingestion and context retrieval.
"""

from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """Request schema for document ingestion."""
    
    source: str = Field(..., description="Document source (gmail, hubspot, calendar)")
    source_id: str = Field(..., description="Original document ID from source")
    document_type: str = Field(..., description="Type of document (email, contact, note, event)")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "gmail",
                "source_id": "msg_123456789",
                "document_type": "email",
                "title": "Meeting Follow-up",
                "content": "Hi John, thanks for the meeting today. Let's schedule a follow-up next week.",
                "metadata": {
                    "sender": "advisor@example.com",
                    "recipient": "john@example.com",
                    "date": "2024-01-01T00:00:00Z",
                    "thread_id": "thread_123"
                }
            }
        }


class DocumentIngestResponse(BaseModel):
    """Response schema for document ingestion."""
    
    document_id: str = Field(..., description="Created document ID")
    source: str = Field(..., description="Document source")
    document_type: str = Field(..., description="Document type")
    title: str = Field(..., description="Document title")
    is_processed: bool = Field(..., description="Whether document is processed")
    processing_error: Optional[str] = Field(None, description="Processing error if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "gmail",
                "document_type": "email",
                "title": "Meeting Follow-up",
                "is_processed": True,
                "processing_error": None
            }
        }


class ContextRetrievalRequest(BaseModel):
    """Request schema for context retrieval."""
    
    query: str = Field(..., description="Query text", min_length=1, max_length=1000)
    limit: int = Field(default=5, description="Maximum number of context items", ge=1, le=20)
    sources: Optional[List[str]] = Field(None, description="Filter by document sources")
    document_types: Optional[List[str]] = Field(None, description="Filter by document types")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Who mentioned their kid plays baseball?",
                "limit": 5,
                "sources": ["gmail", "hubspot"],
                "document_types": ["email", "note"]
            }
        }


class ContextRetrievalResponse(BaseModel):
    """Response schema for context retrieval."""
    
    query: str = Field(..., description="Original query")
    context_items: List[Dict[str, Any]] = Field(..., description="Retrieved context items")
    total_items: int = Field(..., description="Total number of context items")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Who mentioned their kid plays baseball?",
                "context_items": [
                    {
                        "content": "John mentioned his son plays baseball and is looking for a new team.",
                        "source": "gmail",
                        "document_type": "email",
                        "title": "Client Update",
                        "relevance_score": 95,
                        "chunk_id": "chunk_123",
                        "document_id": "doc_123"
                    }
                ],
                "total_items": 1
            }
        }


class DocumentStatsResponse(BaseModel):
    """Response schema for document statistics."""
    
    total_documents: int = Field(..., description="Total number of documents")
    source_breakdown: Dict[str, int] = Field(..., description="Documents by source")
    total_chunks: int = Field(..., description="Total number of chunks")
    processing_status: Dict[bool, int] = Field(..., description="Processing status breakdown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "source_breakdown": {
                    "gmail": 100,
                    "hubspot": 50
                },
                "total_chunks": 450,
                "processing_status": {
                    True: 140,
                    False: 10
                }
            }
        }


class EmbeddingJobRequest(BaseModel):
    """Request schema for embedding job creation."""
    
    job_type: str = Field(..., description="Type of embedding job")
    input_data: Dict[str, Any] = Field(..., description="Input data for the job")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_type": "document_embedding",
                "input_data": {
                    "document_ids": ["doc_123", "doc_456"],
                    "batch_size": 10
                }
            }
        }


class EmbeddingJobResponse(BaseModel):
    """Response schema for embedding job."""
    
    job_id: str = Field(..., description="Job ID")
    job_type: str = Field(..., description="Job type")
    status: str = Field(..., description="Job status")
    progress_percentage: int = Field(..., description="Progress percentage")
    total_items: Optional[int] = Field(None, description="Total items to process")
    processed_items: int = Field(..., description="Processed items")
    error_message: Optional[str] = Field(None, description="Error message if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "job_type": "document_embedding",
                "status": "processing",
                "progress_percentage": 75,
                "total_items": 100,
                "processed_items": 75,
                "error_message": None
            }
        }


class VectorSearchRequest(BaseModel):
    """Request schema for vector search."""
    
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=50)
    sources: Optional[List[str]] = Field(None, description="Filter by sources")
    document_types: Optional[List[str]] = Field(None, description="Filter by document types")
    similarity_threshold: Optional[float] = Field(None, description="Minimum similarity threshold", ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "baseball kid team",
                "limit": 10,
                "sources": ["gmail", "hubspot"],
                "document_types": ["email", "note"],
                "similarity_threshold": 0.7
            }
        }


class VectorSearchResponse(BaseModel):
    """Response schema for vector search."""
    
    query: str = Field(..., description="Original query")
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "baseball kid team",
                "results": [
                    {
                        "chunk_id": "chunk_123",
                        "document_id": "doc_123",
                        "content": "John mentioned his son plays baseball and is looking for a new team.",
                        "similarity_score": 0.95,
                        "metadata": {
                            "source": "gmail",
                            "document_type": "email",
                            "title": "Client Update"
                        }
                    }
                ],
                "total_results": 1
            }
        }