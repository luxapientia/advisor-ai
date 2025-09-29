"""
Gmail sync endpoints for managing email synchronization.

This module handles Gmail sync status, progress tracking, and manual sync triggers.
"""

from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ExternalServiceError
from app.models.user import User
from app.services.google_service import GoogleService
from app.services.rag_service import RAGService
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/sync/status")
async def get_gmail_sync_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get Gmail sync status for the current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict: Sync status information
    """
    return {
        "status": current_user.google_sync_status,
        "needed": current_user.google_sync_needed,
        "completed": current_user.google_sync_completed,
        "has_google_access": current_user.has_google_access
    }


@router.post("/sync/start")
async def start_gmail_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Start Gmail sync for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Sync start confirmation
    """
    if not current_user.has_google_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have Google access"
        )
    
    if current_user.google_sync_status == "syncing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sync is already in progress"
        )
    
    if current_user.google_sync_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sync is already completed"
        )
    
    # Set status to syncing immediately to prevent concurrent syncs
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(google_sync_status="syncing", google_sync_error=None)
    )
    await db.commit()
    
    try:
        logger.info("Started Google sync for user", user_id=str(current_user.id))
        
        # Start sync in background
        google_service = GoogleService()
        rag_service = RAGService(db)
        
        # Create Google credentials from user tokens
        from google.oauth2.credentials import Credentials
        credentials = Credentials(
            token=current_user.google_access_token,
            refresh_token=current_user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,
            client_secret=None,
            expiry=current_user.google_token_expires_at
        )
        
        # Run sync in background
        import asyncio
        asyncio.create_task(_run_gmail_sync_with_progress(
            db=db,
            user_id=current_user.id,
            google_service=google_service,
            rag_service=rag_service,
            credentials=credentials
        ))
        
        logger.info("Gmail sync started for user", user_id=str(current_user.id))
        
        return {"message": "Gmail sync started successfully"}
        
    except Exception as e:
        logger.error("Failed to start Gmail sync", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Gmail sync"
        )


@router.post("/sync/reset")
async def reset_gmail_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Reset Gmail sync status to allow re-sync.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Reset confirmation
    """
    try:
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(google_sync_status="none", google_sync_error=None)
        )
        await db.commit()
        
        logger.info("Gmail sync reset for user", user_id=str(current_user.id))
        
        return {"message": "Gmail sync status reset successfully"}
        
    except Exception as e:
        logger.error("Failed to reset Gmail sync", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset Gmail sync"
        )


async def _run_gmail_sync_with_progress(
    db: AsyncSession,
    user_id: str,
    google_service: GoogleService,
    rag_service: RAGService,
    credentials
) -> None:
    """
    Run Gmail sync with progress tracking.
    
    Args:
        db: Database session
        user_id: User ID
        google_service: Google service instance
        rag_service: RAG service instance
        credentials: Google OAuth credentials
    """
    try:
        logger.info("Starting Gmail sync with progress tracking", user_id=user_id)
        
        # Get user's last sync time for incremental sync
        user_result = await db.execute(
            select(User.google_sync_completed_at).where(User.id == user_id)
        )
        last_sync_time = user_result.scalar_one_or_none()
        
        # Create incremental query based on last sync
        if last_sync_time:
            # Convert to Gmail date format (YYYY/MM/DD)
            from datetime import datetime
            gmail_date = last_sync_time.strftime("%Y/%m/%d")
            query = f"after:{gmail_date}"
            logger.info("Using incremental sync", user_id=user_id, last_sync=gmail_date)
        else:
            # First sync - get last 90 days
            query = "newer_than:90d"
            logger.info("Using full sync (first time)", user_id=user_id)
        
        max_results = 500
        
        messages = await google_service.get_gmail_messages(
            credentials=credentials,
            query=query,
            max_results=max_results
        )
        
        total_messages = len(messages)
        processed_messages = 0
        
        logger.info("Retrieved Gmail messages for sync", 
                   user_id=user_id, 
                   count=total_messages)
        
        # Process and ingest emails
        for message in messages:
            try:
                # Parse email data
                email_data = google_service._parse_gmail_message(message)
                
                # Ingest into RAG system
                document = await rag_service.ingest_document(
                    user_id=user_id,
                    source="gmail",
                    source_id=email_data["id"],
                    document_type="email",
                    title=email_data["subject"],
                    content=email_data["content"],
                    metadata=email_data["metadata"]
                )
                
                processed_messages += 1
                
                # Log progress every 50 emails
                if processed_messages % 50 == 0:
                    logger.info("Gmail sync progress", 
                               user_id=user_id, 
                               processed=processed_messages,
                               total=total_messages)
            
            except Exception as e:
                logger.warning("Failed to process email during sync", 
                              user_id=user_id, 
                              message_id=message.get("id"),
                              error=str(e))
                continue
        
        # Mark sync as completed
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                google_sync_status="completed",
                google_sync_completed_at=datetime.utcnow(),
                google_sync_error=None
            )
        )
        await db.commit()
        
        logger.info("Gmail sync completed successfully", 
                   user_id=user_id, 
                   processed=processed_messages,
                   total=total_messages)
        
    except Exception as e:
        logger.error("Gmail sync failed", user_id=user_id, error=str(e))
        
        # Mark sync as failed
        try:
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    google_sync_status="error",
                    google_sync_error=str(e)
                )
            )
            await db.commit()
        except Exception as update_error:
            logger.error("Failed to update sync error status", user_id=user_id, error=str(update_error))