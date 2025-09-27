"""
RAG endpoints for document ingestion and context retrieval.

This module handles document ingestion, embedding generation,
vector search, and context retrieval for the RAG pipeline.
"""

from typing import Dict, Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ValidationError, AIError
from app.models.user import User
from app.services.rag_service import RAGService
from app.schemas.rag import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    ContextRetrievalRequest,
    ContextRetrievalResponse,
    DocumentStatsResponse
)
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    request: DocumentIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DocumentIngestResponse:
    """
    Ingest a document into the RAG system.
    
    Args:
        request: Document ingestion request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentIngestResponse: Ingestion result
    """
    try:
        rag_service = RAGService(db)
        
        # Ingest document
        document = await rag_service.ingest_document(
            user_id=str(current_user.id),
            source=request.source,
            source_id=request.source_id,
            document_type=request.document_type,
            title=request.title,
            content=request.content,
            metadata=request.metadata
        )
        
        logger.info("Ingested document", user_id=str(current_user.id), document_id=str(document.id))
        
        return DocumentIngestResponse(
            document_id=str(document.id),
            source=document.source,
            document_type=document.document_type,
            title=document.title,
            is_processed=document.is_processed,
            processing_error=document.processing_error
        )
        
    except Exception as e:
        logger.error("Failed to ingest document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document"
        )


@router.post("/query", response_model=ContextRetrievalResponse)
async def retrieve_context(
    request: ContextRetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ContextRetrievalResponse:
    """
    Retrieve context for a query using RAG.
    
    Args:
        request: Context retrieval request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ContextRetrievalResponse: Retrieved context
    """
    try:
        rag_service = RAGService(db)
        
        # Retrieve context
        context_items = await rag_service.retrieve_context_for_query(
            user_id=str(current_user.id),
            query=request.query,
            limit=request.limit,
            sources=request.sources,
            document_types=request.document_types
        )
        
        logger.info("Retrieved context for query", user_id=str(current_user.id), items=len(context_items))
        
        return ContextRetrievalResponse(
            query=request.query,
            context_items=context_items,
            total_items=len(context_items)
        )
        
    except Exception as e:
        logger.error("Failed to retrieve context", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve context"
        )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DocumentStatsResponse:
    """
    Get document statistics for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentStatsResponse: Document statistics
    """
    try:
        rag_service = RAGService(db)
        
        # Get statistics
        stats = await rag_service.get_document_statistics(str(current_user.id))
        
        return DocumentStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Failed to get document stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document statistics"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a document from the RAG system.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        rag_service = RAGService(db)
        
        # Delete document
        success = await rag_service.delete_document(str(current_user.id), document_id)
        
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.delete("/clear")
async def clear_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Clear all RAG data for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Clear confirmation
    """
    try:
        rag_service = RAGService(db)
        
        # Clear user data
        success = await rag_service.clear_user_data(str(current_user.id))
        
        if success:
            return {"message": "User RAG data cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear user data"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear user data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear user data"
        )