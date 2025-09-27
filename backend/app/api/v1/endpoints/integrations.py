"""
Integration endpoints for third-party service management.

This module handles integration account management, webhook configuration,
and data synchronization for Gmail, Google Calendar, and HubSpot.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ValidationError, ExternalServiceError
from app.models.user import User
from app.models.integration import IntegrationAccount, Webhook, SyncLog
from app.schemas.integrations import (
    IntegrationAccountResponse,
    WebhookResponse,
    SyncLogResponse,
    WebhookCreateRequest,
    SyncRequest
)
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/accounts", response_model=List[IntegrationAccountResponse])
async def get_integration_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[IntegrationAccountResponse]:
    """
    Get user's integration accounts.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[IntegrationAccountResponse]: Integration accounts
    """
    try:
        result = await db.execute(
            select(IntegrationAccount).where(IntegrationAccount.user_id == current_user.id)
        )
        accounts = result.scalars().all()
        
        return [IntegrationAccountResponse.from_orm(account) for account in accounts]
        
    except Exception as e:
        logger.error("Failed to get integration accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration accounts"
        )


@router.get("/accounts/{service}", response_model=IntegrationAccountResponse)
async def get_integration_account(
    service: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IntegrationAccountResponse:
    """
    Get specific integration account.
    
    Args:
        service: Integration service name
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        IntegrationAccountResponse: Integration account
    """
    try:
        result = await db.execute(
            select(IntegrationAccount).where(
                IntegrationAccount.user_id == current_user.id,
                IntegrationAccount.service == service
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration account not found"
            )
        
        return IntegrationAccountResponse.from_orm(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get integration account", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration account"
        )


@router.delete("/accounts/{service}")
async def disconnect_integration(
    service: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Disconnect integration account.
    
    Args:
        service: Integration service name
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Disconnection confirmation
    """
    try:
        if service == "hubspot":
            # For HubSpot, clear tokens from User model
            current_user.hubspot_access_token = None
            current_user.hubspot_refresh_token = None
            current_user.hubspot_token_expires_at = None
            current_user.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info("Disconnected HubSpot integration", user_id=str(current_user.id))
            return {"message": "HubSpot integration disconnected successfully"}
        
        else:
            # For other services, use IntegrationAccount model
            result = await db.execute(
                select(IntegrationAccount).where(
                    IntegrationAccount.user_id == current_user.id,
                    IntegrationAccount.service == service
                )
            )
            account = result.scalar_one_or_none()
            
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Integration account not found"
                )
            
            # Mark as disconnected
            account.is_connected = False
            account.disconnected_at = datetime.utcnow()
            account.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info("Disconnected integration", user_id=str(current_user.id), service=service)
            return {"message": f"{service} integration disconnected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to disconnect integration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect integration"
        )


@router.get("/webhooks", response_model=List[WebhookResponse])
async def get_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[WebhookResponse]:
    """
    Get user's webhooks.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[WebhookResponse]: Webhooks
    """
    try:
        result = await db.execute(
            select(Webhook)
            .join(IntegrationAccount)
            .where(IntegrationAccount.user_id == current_user.id)
        )
        webhooks = result.scalars().all()
        
        return [WebhookResponse.from_orm(webhook) for webhook in webhooks]
        
    except Exception as e:
        logger.error("Failed to get webhooks", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhooks"
        )


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    request: WebhookCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """
    Create a new webhook.
    
    Args:
        request: Webhook creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        WebhookResponse: Created webhook
    """
    try:
        # Get integration account
        result = await db.execute(
            select(IntegrationAccount).where(
                IntegrationAccount.user_id == current_user.id,
                IntegrationAccount.service == request.service
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration account not found"
            )
        
        # Create webhook
        webhook = Webhook(
            account_id=account.id,
            webhook_id=request.webhook_id,
            webhook_url=request.webhook_url,
            event_types=request.event_types,
            verification_token=request.verification_token
        )
        
        db.add(webhook)
        await db.commit()
        await db.refresh(webhook)
        
        logger.info("Created webhook", user_id=str(current_user.id), webhook_id=request.webhook_id)
        
        return WebhookResponse.from_orm(webhook)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook"
        )


@router.get("/sync/logs", response_model=List[SyncLogResponse])
async def get_sync_logs(
    service: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[SyncLogResponse]:
    """
    Get user's sync logs.
    
    Args:
        service: Filter by service
        limit: Maximum number of logs
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[SyncLogResponse]: Sync logs
    """
    try:
        # Build query
        query = select(SyncLog).join(IntegrationAccount).where(
            IntegrationAccount.user_id == current_user.id
        )
        
        if service:
            query = query.where(IntegrationAccount.service == service)
        
        query = query.order_by(SyncLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        sync_logs = result.scalars().all()
        
        return [SyncLogResponse.from_orm(log) for log in sync_logs]
        
    except Exception as e:
        logger.error("Failed to get sync logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync logs"
        )


@router.post("/sync/trigger")
async def trigger_sync(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Trigger manual data synchronization.
    
    Args:
        request: Sync request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Sync confirmation
    """
    try:
        # Get integration account
        result = await db.execute(
            select(IntegrationAccount).where(
                IntegrationAccount.user_id == current_user.id,
                IntegrationAccount.service == request.service
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration account not found"
            )
        
        # Create sync log
        sync_log = SyncLog(
            account_id=account.id,
            sync_type=request.sync_type,
            sync_status="pending",
            sync_config=request.config or {}
        )
        
        db.add(sync_log)
        await db.commit()
        await db.refresh(sync_log)
        
        # TODO: Trigger actual sync process (background task)
        
        logger.info("Triggered sync", user_id=str(current_user.id), service=request.service)
        
        return {"message": f"Sync triggered for {request.service}"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to trigger sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger sync"
        )