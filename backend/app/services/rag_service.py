"""
RAG (Retrieval-Augmented Generation) service for vector search and context retrieval.

This service handles document ingestion, embedding generation, vector storage,
and similarity search for the RAG pipeline.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.exceptions import AIError, DatabaseError
from app.core.logging import log_ai_interaction
from app.models.rag import Document, DocumentChunk, QueryCache, EmbeddingJob
from app.models.user import User
from app.services.ai_service import AIService

logger = structlog.get_logger(__name__)


class RAGService:
    """
    RAG service for vector search and context retrieval.
    
    This service provides methods for document ingestion, embedding generation,
    vector storage, similarity search, and query caching.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the RAG service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.ai_service = AIService()
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
    
    async def ingest_document(
        self,
        user_id: str,
        source: str,
        source_id: str,
        document_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Ingest a document into the RAG system.
        
        Args:
            user_id: User ID
            source: Document source (gmail, hubspot, calendar)
            source_id: Original document ID from source
            document_type: Type of document (email, contact, note, event)
            title: Document title
            content: Document content
            metadata: Additional metadata
            
        Returns:
            Document: Created document
        """
        try:
            # Check if document already exists
            result = await self.db.execute(
                select(Document).where(
                    and_(
                        Document.user_id == user_id,
                        Document.source == source,
                        Document.source_id == source_id
                    )
                )
            )
            existing_docs = result.scalars().all()
            existing_doc = existing_docs[0] if existing_docs else None
            
            # If there are duplicates, log and clean them up
            if len(existing_docs) > 1:
                logger.warning(f"Found {len(existing_docs)} duplicate documents, cleaning up", 
                    user_id=str(user_id), source=source, source_id=source_id)
                
                # Keep the first document, delete the rest
                for duplicate_doc in existing_docs[1:]:
                    await self.db.delete(duplicate_doc)
                    logger.info(f"Deleted duplicate document", document_id=str(duplicate_doc.id))
                
                await self.db.commit()
            
            if existing_doc:
                # Check if content has actually changed
                content_changed = (
                    existing_doc.title != title or 
                    existing_doc.content != content or 
                    existing_doc.metadata != (metadata or {})
                )
                
                # Update existing document
                existing_doc.title = title
                existing_doc.content = content
                existing_doc.metadata = metadata or {}
                existing_doc.updated_at = datetime.utcnow()
                
                # Only reprocess if content changed
                if content_changed:
                    existing_doc.is_processed = False
                    
                    # Delete existing chunks
                    await self.db.execute(
                        delete(DocumentChunk).where(DocumentChunk.document_id == existing_doc.id)
                    )
                    
                    logger.info("Updated existing document with content changes", 
                        document_id=str(existing_doc.id), source=source)
                else:
                    logger.info("Document unchanged, skipping reprocessing", 
                        document_id=str(existing_doc.id), source=source)
                
                document = existing_doc
            else:
                # Create new document
                document = Document(
                    user_id=user_id,
                    source=source,
                    source_id=source_id,
                    document_type=document_type,
                    title=title,
                    content=content,
                    metadata=metadata or {}
                )
                
                self.db.add(document)
                logger.info("Created new document", source=source, document_type=document_type)
            
            await self.db.commit()
            await self.db.refresh(document)
            
            # Process document for embeddings only if needed
            if not document.is_processed:
                await self._process_document_for_embeddings(document)
            
            return document
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to ingest document", error=str(e))
            raise DatabaseError("Failed to ingest document")
    
    async def _process_document_for_embeddings(self, document: Document) -> None:
        """
        Process document and generate embeddings.
        
        Args:
            document: Document to process
        """
        try:
            # Chunk the document content
            chunks = self.ai_service.chunk_text(document.content)
            
            # Generate embeddings for chunks
            embeddings = await self.ai_service.generate_embeddings_batch(chunks)
            
            # Create document chunks
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_obj = DocumentChunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk,
                    content_length=len(chunk),
                    embedding=embedding,
                    metadata={
                        "source": document.source,
                        "document_type": document.document_type,
                        "title": document.title
                    }
                )
                self.db.add(chunk_obj)
            
            # Mark document as processed
            document.is_processed = True
            
            await self.db.commit()
            
            logger.info("Processed document for embeddings", document_id=str(document.id), chunks=len(chunks))
            
        except Exception as e:
            await self.db.rollback()
            document.is_processed = False
            document.processing_error = str(e)
            await self.db.commit()
            
            logger.error("Failed to process document for embeddings", document_id=str(document.id), error=str(e))
            raise AIError("Failed to process document for embeddings")
    
    async def search_similar_chunks(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 10,
        sources: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using vector similarity.
        
        Args:
            user_id: User ID
            query_embedding: Query embedding vector
            limit: Maximum number of results
            sources: Filter by document sources
            document_types: Filter by document types
            
        Returns:
            List: Similar chunks with metadata
        """
        try:
            # Build query
            query = select(DocumentChunk).join(Document).where(
                Document.user_id == user_id
            )
            
            # Add filters
            if sources:
                query = query.where(Document.source.in_(sources))
            if document_types:
                query = query.where(Document.document_type.in_(document_types))
            
            # Add similarity search  
            query = query.add_columns(
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            ).order_by("distance").limit(limit)
            
            # Execute query
            result = await self.db.execute(query)
            chunks_with_distance = result.fetchall()
            
            # Prepare results
            results = []
            for row in chunks_with_distance:
                chunk = row[0]  # DocumentChunk object
                distance = row[1]  # Distance value
                
                # Calculate similarity score (cosine similarity = 1 - cosine_distance)
                similarity_score = 1 - float(distance)
                
                if similarity_score >= self.similarity_threshold:
                    results.append({
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "content": chunk.content,
                        "similarity_score": float(similarity_score),
                        "metadata": chunk.metadata,
                        "source": chunk.metadata.get("source"),
                        "document_type": chunk.metadata.get("document_type"),
                        "title": chunk.metadata.get("title")
                    })
            
            logger.info("Searched similar chunks", user_id=user_id, results=len(results))
            return results
            
        except Exception as e:
            logger.error("Failed to search similar chunks", user_id=user_id, error=str(e))
            raise DatabaseError("Failed to search similar chunks")
    
    async def retrieve_context_for_query(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        sources: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query using RAG.
        
        Args:
            user_id: User ID
            query: Query text
            limit: Maximum number of context items
            sources: Filter by document sources
            document_types: Filter by document types
            
        Returns:
            List: Relevant context items
        """
        try:
            # Check cache first
            query_hash = self.ai_service.get_query_hash(query)
            cached_result = await self._get_cached_query(user_id, query_hash)
            
            if cached_result:
                logger.info("Retrieved context from cache", user_id=user_id, query_hash=query_hash)
                return cached_result["retrieved_chunks"]
            
            # Generate query embedding
            query_embedding = await self.ai_service.generate_embedding(query)
            
            # Search for similar chunks
            similar_chunks = await self.search_similar_chunks(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit * 2,  # Get more to filter by relevance
                sources=sources,
                document_types=document_types
            )
            
            # Filter and rank results
            context_items = []
            total_length = 0
            
            for chunk in similar_chunks:
                if total_length + len(chunk["content"]) > self.max_context_length:
                    break
                
                context_items.append({
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "document_type": chunk["document_type"],
                    "title": chunk["title"],
                    "relevance_score": int(chunk["similarity_score"] * 100),
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"]
                })
                
                total_length += len(chunk["content"])
            
            # Cache the result
            await self._cache_query_result(
                user_id=user_id,
                query_hash=query_hash,
                query_text=query,
                query_embedding=query_embedding,
                retrieved_chunks=context_items
            )
            
            logger.info("Retrieved context for query", user_id=user_id, items=len(context_items))
            return context_items
            
        except Exception as e:
            logger.error("Failed to retrieve context for query", user_id=user_id, error=str(e))
            raise AIError("Failed to retrieve context for query")
    
    async def _get_cached_query(self, user_id: str, query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached query result.
        
        Args:
            user_id: User ID
            query_hash: Query hash
            
        Returns:
            Optional[Dict]: Cached result if found and not expired
        """
        try:
            result = await self.db.execute(
                select(QueryCache).where(
                    and_(
                        QueryCache.user_id == user_id,
                        QueryCache.query_hash == query_hash,
                        or_(
                            QueryCache.expires_at.is_(None),
                            QueryCache.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            cached_query = result.scalar_one_or_none()
            
            if cached_query:
                # Update hit count and last accessed
                cached_query.hit_count += 1
                cached_query.last_accessed_at = datetime.utcnow()
                await self.db.commit()
                
                return {
                    "retrieved_chunks": cached_query.retrieved_chunks,
                    "context_summary": cached_query.context_summary
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached query", user_id=user_id, query_hash=query_hash, error=str(e))
            return None
    
    async def _cache_query_result(
        self,
        user_id: str,
        query_hash: str,
        query_text: str,
        query_embedding: List[float],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Cache query result.
        
        Args:
            user_id: User ID
            query_hash: Query hash
            query_text: Query text
            query_embedding: Query embedding
            retrieved_chunks: Retrieved chunks
        """
        try:
            # Generate context summary
            context_summary = await self.ai_service.summarize_text(
                "\n".join([chunk["content"] for chunk in retrieved_chunks])
            )
            
            # Create cache entry
            cache_entry = QueryCache(
                user_id=user_id,
                query_hash=query_hash,
                query_text=query_text,
                query_embedding=query_embedding,
                retrieved_chunks=retrieved_chunks,
                context_summary=context_summary,
                expires_at=datetime.utcnow() + timedelta(hours=24)  # Cache for 24 hours
            )
            
            self.db.add(cache_entry)
            await self.db.commit()
            
            logger.info("Cached query result", user_id=user_id, query_hash=query_hash)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to cache query result", user_id=user_id, query_hash=query_hash, error=str(e))
    
    async def get_document_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get document statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Document statistics
        """
        try:
            # Get document counts by source
            source_counts = await self.db.execute(
                select(
                    Document.source,
                    func.count(Document.id).label("count")
                ).where(Document.user_id == user_id)
                .group_by(Document.source)
            )
            
            # Get chunk counts
            chunk_count = await self.db.execute(
                select(func.count(DocumentChunk.id))
                .join(Document)
                .where(Document.user_id == user_id)
            )
            
            # Get processing status
            processing_status = await self.db.execute(
                select(
                    Document.is_processed,
                    func.count(Document.id).label("count")
                ).where(Document.user_id == user_id)
                .group_by(Document.is_processed)
            )
            
            return {
                "total_documents": sum(row.count for row in source_counts),
                "source_breakdown": {row.source: row.count for row in source_counts},
                "total_chunks": chunk_count.scalar(),
                "processing_status": {row.is_processed: row.count for row in processing_status}
            }
            
        except Exception as e:
            logger.error("Failed to get document statistics", user_id=user_id, error=str(e))
            return {}
    
    async def delete_document(self, user_id: str, document_id: str) -> bool:
        """
        Delete a document and its chunks.
        
        Args:
            user_id: User ID
            document_id: Document ID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Delete document (chunks will be deleted by cascade)
            result = await self.db.execute(
                delete(Document).where(
                    and_(
                        Document.id == document_id,
                        Document.user_id == user_id
                    )
                )
            )
            
            if result.rowcount > 0:
                await self.db.commit()
                logger.info("Deleted document", user_id=user_id, document_id=document_id)
                return True
            else:
                logger.warning("Document not found for deletion", user_id=user_id, document_id=document_id)
                return False
                
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to delete document", user_id=user_id, document_id=document_id, error=str(e))
            return False
    
    async def clear_user_data(self, user_id: str) -> bool:
        """
        Clear all RAG data for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if cleared successfully
        """
        try:
            # Delete all user data
            await self.db.execute(delete(QueryCache).where(QueryCache.user_id == user_id))
            await self.db.execute(delete(DocumentChunk).join(Document).where(Document.user_id == user_id))
            await self.db.execute(delete(Document).where(Document.user_id == user_id))
            
            await self.db.commit()
            logger.info("Cleared user RAG data", user_id=user_id)
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to clear user RAG data", user_id=user_id, error=str(e))
            return False