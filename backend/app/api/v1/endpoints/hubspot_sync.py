"""
HubSpot sync endpoints for managing CRM synchronization.

This module handles HubSpot sync status, progress tracking, and manual sync triggers.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

import structlog
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ExternalServiceError
from app.models.user import User
from app.services.hubspot_service import HubSpotService
from app.services.rag_service import RAGService
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/sync/status")
async def get_hubspot_sync_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get HubSpot sync status for the current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict: Sync status information
    """
    return {
        "status": current_user.hubspot_sync_status,
        "completed": current_user.hubspot_sync_completed,
        "has_hubspot_access": current_user.has_hubspot_access
    }


@router.post("/sync/start")
async def start_hubspot_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Start HubSpot sync for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Sync start confirmation
    """
    if not current_user.has_hubspot_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have HubSpot access"
        )
    
    # Check if sync is stuck (syncing for more than 30 minutes)
    if current_user.hubspot_sync_status == "syncing":
        # Check if sync has been running for more than 30 minutes
        if (current_user.hubspot_sync_completed_at and 
            datetime.utcnow() - current_user.hubspot_sync_completed_at > timedelta(minutes=30)):
            logger.warning("Detected stuck HubSpot sync, resetting status", user_id=str(current_user.id))
            # Reset stuck sync
            await db.execute(
                update(User)
                .where(User.id == current_user.id)
                .values(hubspot_sync_status="error", hubspot_sync_error="Sync was stuck and reset")
            )
            await db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HubSpot sync is already in progress"
            )
    
    # Set status to syncing immediately to prevent concurrent syncs
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(hubspot_sync_status="syncing", hubspot_sync_error=None)
    )
    await db.commit()
    
    try:
        logger.info("Started HubSpot sync for user", user_id=str(current_user.id))
        
        # Start sync in background
        hubspot_service = HubSpotService()
        
        # Run sync in background with fresh database session
        import asyncio
        asyncio.create_task(_run_hubspot_sync_with_progress(
            user_id=current_user.id,
            access_token=current_user.hubspot_access_token
        ))
        
        logger.info("HubSpot sync started for user", user_id=str(current_user.id))
        
        return {"message": "HubSpot sync started successfully"}
        
    except Exception as e:
        logger.error("Failed to start HubSpot sync", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start HubSpot sync"
        )


@router.post("/sync/reset")
async def reset_hubspot_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Reset HubSpot sync status to allow re-sync.
    
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
            .values(hubspot_sync_status="none", hubspot_sync_error=None)
        )
        await db.commit()
        
        logger.info("HubSpot sync reset for user", user_id=str(current_user.id))
        
        return {"message": "HubSpot sync status reset successfully"}
        
    except Exception as e:
        logger.error("Failed to reset HubSpot sync", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset HubSpot sync"
        )


async def _run_hubspot_sync_with_progress(
    user_id: str,
    access_token: str
) -> None:
    """
    Run HubSpot sync with progress tracking.
    
    Args:
        user_id: User ID
        access_token: HubSpot access token
    """
    # Create fresh database session for background task
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting HubSpot sync with progress tracking", user_id=user_id)
            
            # Initialize services
            hubspot_service = HubSpotService()
            rag_service = RAGService(db)
            
            # Get user's last sync time for incremental sync
            user_result = await db.execute(
                select(User.hubspot_sync_completed_at).where(User.id == user_id)
            )
            last_sync_time = user_result.scalar_one_or_none()
            
            # === HUBSPOT CONTACTS SYNC ===
            logger.info("Starting HubSpot contacts sync", user_id=user_id)
            
            # Get contacts using search API with incremental filtering
            if last_sync_time:
                # Incremental sync - get contacts modified after last sync
                # Convert to milliseconds timestamp for HubSpot API
                last_sync_timestamp = int(last_sync_time.timestamp() * 1000)
                
                # Use search API with filter for lastmodifieddate
                search_data = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "hs_lastmodifieddate",
                                    "operator": "GTE",
                                    "value": str(last_sync_timestamp)
                                }
                            ]
                        }
                    ],
                    "properties": [
                        "email", "firstname", "lastname", "phone", "company",
                        "createdate", "lastmodifieddate", "lifecyclestage",
                        "hs_object_id"
                    ],
                    "limit": 100
                }
                
                logger.info("Using incremental sync", user_id=user_id, last_sync=last_sync_timestamp)
            else:
                # First sync - get all contacts
                search_data = {
                    "properties": [
                        "email", "firstname", "lastname", "phone", "company",
                        "createdate", "lastmodifieddate", "lifecyclestage",
                        "hs_object_id"
                    ],
                    "limit": 100
                }
                logger.info("Using full sync (first time)", user_id=user_id)
            
            # Get all contacts with pagination
            all_contacts = []
            after = None
            
            while True:
                if after:
                    search_data["after"] = after
                
                # Search contacts
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{hubspot_service.base_url}/crm/v3/objects/contacts/search",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        json=search_data
                    )
                    response.raise_for_status()
                    search_results = response.json()
                
                contacts = search_results.get("results", [])
                all_contacts.extend(contacts)
                
                # Check for pagination
                paging = search_results.get("paging", {})
                if "next" in paging and "after" in paging["next"]:
                    after = paging["next"]["after"]
                else:
                    break
            
            total_contacts = len(all_contacts)
            processed_contacts = 0
            
            logger.info("Retrieved HubSpot contacts for sync", 
                user_id=user_id, 
                count=total_contacts)
            
            # Process and ingest contacts
            for contact in all_contacts:
                try:
                    # Parse contact data
                    contact_data = _parse_hubspot_contact(contact)
                    
                    # Ingest into RAG system
                    document = await rag_service.ingest_document(
                        user_id=user_id,
                        source="hubspot",
                        source_id=contact_data["id"],
                        document_type="contact",
                        title=contact_data["name"],
                        content=contact_data["content"],
                        metadata=contact_data["metadata"]
                    )
                    
                    processed_contacts += 1
                    
                    # Log progress every 50 contacts
                    if processed_contacts % 50 == 0:
                        logger.info("HubSpot sync progress", 
                            user_id=user_id, 
                            processed=processed_contacts,
                            total=total_contacts)
                
                except Exception as e:
                    logger.warning("Failed to process contact during sync", 
                        user_id=user_id, 
                        contact_id=contact.get("id"),
                        error=str(e))
                    continue
            
            logger.info("HubSpot contacts sync completed successfully", 
                user_id=user_id, 
                processed=processed_contacts,
                total=total_contacts)
            
            # Mark sync as completed
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    hubspot_sync_status="completed",
                    hubspot_sync_completed_at=datetime.utcnow(),
                    hubspot_sync_error=None
                )
            )
            await db.commit()
            
            logger.info("HubSpot sync completed successfully", 
                user_id=user_id, 
                contacts_processed=processed_contacts, 
                contacts_total=total_contacts)
            
        except Exception as e:
            logger.error("HubSpot sync failed", user_id=user_id, error=str(e))
            
            # Mark sync as failed
            try:
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(
                        hubspot_sync_status="error",
                        hubspot_sync_error=str(e)
                    )
                )
                await db.commit()
            except Exception as update_error:
                logger.error("Failed to update sync error status", user_id=user_id, error=str(update_error))


def _parse_hubspot_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse HubSpot contact data for RAG ingestion.
    
    Args:
        contact: Raw HubSpot contact data
        
    Returns:
        Dict: Parsed contact data with name, content, and metadata
    """
    properties = contact.get("properties", {})
    
    # Build contact name
    first_name = properties.get("firstname", "")
    last_name = properties.get("lastname", "")
    email = properties.get("email", "")
    
    if first_name and last_name:
        name = f"{first_name} {last_name}"
    elif first_name:
        name = first_name
    elif last_name:
        name = last_name
    elif email:
        name = email
    else:
        name = f"Contact {contact.get('id', 'Unknown')}"
    
    # Build content
    content_parts = []
    
    if email:
        content_parts.append(f"Email: {email}")
    
    if properties.get("phone"):
        content_parts.append(f"Phone: {properties['phone']}")
    
    if properties.get("company"):
        content_parts.append(f"Company: {properties['company']}")
    
    if properties.get("lifecyclestage"):
        content_parts.append(f"Lifecycle Stage: {properties['lifecyclestage']}")
    
    content = "\n".join(content_parts) if content_parts else name
    
    return {
        "id": contact["id"],
        "name": name,
        "email": email,
        "content": content,
        "metadata": {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": properties.get("phone", ""),
            "company": properties.get("company", ""),
            "lifecycle_stage": properties.get("lifecyclestage", ""),
            "created_date": properties.get("createdate", ""),
            "last_modified_date": properties.get("lastmodifieddate", ""),
            "contact_id": contact["id"]
        }
    }