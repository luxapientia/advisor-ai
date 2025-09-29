"""
Gmail sync endpoints for managing email synchronization.

This module handles Gmail sync status, progress tracking, and manual sync triggers.
"""

from datetime import datetime, timedelta
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
    Get Google sync status for the current user.
    
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
    Start Google sync for the current user.
    
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
    
    # if current_user.google_sync_status == "completed":
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Google sync is already completed"
    #     )
    
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
        
        # Run sync in background with fresh database session
        import asyncio
        asyncio.create_task(_run_google_sync_with_progress(
            user_id=current_user.id,
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


async def _run_google_sync_with_progress(
    user_id: str,
    credentials
) -> None:
    """
    Run Google sync (Gmail + Calendar) with progress tracking.
    
    Args:
        user_id: User ID
        credentials: Google OAuth credentials
    """
    # Create fresh database session for background task
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting Google sync (Gmail + Calendar) with progress tracking", user_id=user_id)
            
            # Initialize services
            google_service = GoogleService()
            rag_service = RAGService(db)
            
            # Get user's last sync time for incremental sync
            user_result = await db.execute(
                select(User.google_sync_completed_at).where(User.id == user_id)
            )
            last_sync_time = user_result.scalar_one_or_none()
            
            # === GMAIL SYNC ===
            logger.info("Starting Gmail sync", user_id=user_id)
            
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
            
            logger.info("Gmail sync completed successfully", 
                user_id=user_id, 
                processed=processed_messages,
                total=total_messages)
            
            # === CALENDAR SYNC ===
            logger.info("Starting Calendar sync", user_id=user_id)
            
            # Calculate time range for calendar sync
            from datetime import datetime, timedelta
            if last_sync_time:
                # Incremental sync - get events from last sync to now + 30 days
                time_min = last_sync_time.isoformat()
                time_max = (datetime.utcnow() + timedelta(days=30)).isoformat()
            else:
                # First sync - get events from 90 days ago to 30 days in future
                time_min = (datetime.utcnow() - timedelta(days=90)).isoformat()
                time_max = (datetime.utcnow() + timedelta(days=30)).isoformat()
            
            events = await google_service.get_calendar_events(
                credentials=credentials,
                calendar_id="primary",
                time_min=time_min,
                time_max=time_max,
                max_results=1000
            )
            
            total_events = len(events)
            processed_events = 0
            
            logger.info("Retrieved Calendar events for sync", 
                user_id=user_id, 
                count=total_events)
            
            # Process and ingest calendar events
            for event in events:
                try:
                    # Parse calendar event data
                    event_data = google_service._parse_calendar_event(event)
                    
                    # Ingest into RAG system
                    document = await rag_service.ingest_document(
                        user_id=user_id,
                        source="calendar",
                        source_id=event["id"],
                        document_type="event",
                        title=event_data["summary"],
                        content=event_data["content"],
                        metadata=event_data["metadata"]
                    )
                    
                    processed_events += 1
                    
                    # Log progress every 50 events
                    if processed_events % 50 == 0:
                        logger.info("Calendar sync progress", 
                            user_id=user_id, 
                            processed=processed_events,
                            total=total_events)
                
                except Exception as e:
                    logger.warning("Failed to process calendar event during sync", 
                        user_id=user_id, 
                        event_id=event.get("id"),
                        error=str(e))
                    continue
            
            logger.info("Calendar sync completed successfully", 
                user_id=user_id, 
                processed=processed_events,
                total=total_events)
            
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
            
            logger.info("Google sync (Gmail + Calendar) completed successfully", 
                user_id=user_id, 
                gmail_processed=processed_messages, 
                gmail_total=total_messages,
                calendar_processed=processed_events,
                calendar_total=total_events)
            
        except Exception as e:
            logger.error("Google sync failed", user_id=user_id, error=str(e))
            
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