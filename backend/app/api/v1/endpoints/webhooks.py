"""
Webhook endpoints for receiving and processing third-party service events.

This module handles incoming webhooks from Gmail, Google Calendar, and HubSpot,
and triggers proactive agent actions based on ongoing instructions.
"""

import json
from typing import Dict, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ValidationError, ExternalServiceError
from app.models.integration import Webhook, WebhookEvent
from app.services.proactive_agent import ProactiveAgent
from app.schemas.webhooks import WebhookEventResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle Gmail webhook events.
    
    Args:
        request: HTTP request
        db: Database session
        
    Returns:
        Dict: Webhook acknowledgment
    """
    try:
        # Get webhook data
        body = await request.body()
        headers = dict(request.headers)
        
        # Parse webhook data
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            webhook_data = {"raw_data": body.decode('utf-8')}
        
        # Get webhook configuration
        webhook = await _get_webhook_by_url(request.url.path, db)
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Create webhook event
        event = WebhookEvent(
            webhook_id=webhook.id,
            event_id=f"gmail_{webhook_data.get('messageId', 'unknown')}",
            event_type="message_created",
            event_data=webhook_data,
            headers=headers,
            source_ip=request.client.host if request.client else None,
            user_agent=headers.get("user-agent")
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        # Process webhook event with proactive agent
        proactive_agent = ProactiveAgent(db)
        await proactive_agent.process_webhook_event(event)
        
        logger.info("Gmail webhook processed successfully", event_id=str(event.id))
        
        return {"status": "success", "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Gmail webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle Google Calendar webhook events.
    
    Args:
        request: HTTP request
        db: Database session
        
    Returns:
        Dict: Webhook acknowledgment
    """
    try:
        # Get webhook data
        body = await request.body()
        headers = dict(request.headers)
        
        # Parse webhook data
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            webhook_data = {"raw_data": body.decode('utf-8')}
        
        # Get webhook configuration
        webhook = await _get_webhook_by_url(request.url.path, db)
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Create webhook event
        event = WebhookEvent(
            webhook_id=webhook.id,
            event_id=f"calendar_{webhook_data.get('eventId', 'unknown')}",
            event_type="event_created",
            event_data=webhook_data,
            headers=headers,
            source_ip=request.client.host if request.client else None,
            user_agent=headers.get("user-agent")
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        # Process webhook event with proactive agent
        proactive_agent = ProactiveAgent(db)
        await proactive_agent.process_webhook_event(event)
        
        logger.info("Calendar webhook processed successfully", event_id=str(event.id))
        
        return {"status": "success", "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Calendar webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/hubspot")
async def hubspot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle HubSpot webhook events.
    
    Args:
        request: HTTP request
        db: Database session
        
    Returns:
        Dict: Webhook acknowledgment
    """
    try:
        # Get webhook data
        body = await request.body()
        headers = dict(request.headers)
        
        # Parse webhook data
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            webhook_data = {"raw_data": body.decode('utf-8')}
        
        # Get webhook configuration
        webhook = await _get_webhook_by_url(request.url.path, db)
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Create webhook event
        event = WebhookEvent(
            webhook_id=webhook.id,
            event_id=f"hubspot_{webhook_data.get('eventId', 'unknown')}",
            event_type="contact_updated",
            event_data=webhook_data,
            headers=headers,
            source_ip=request.client.host if request.client else None,
            user_agent=headers.get("user-agent")
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        # Process webhook event with proactive agent
        proactive_agent = ProactiveAgent(db)
        await proactive_agent.process_webhook_event(event)
        
        logger.info("HubSpot webhook processed successfully", event_id=str(event.id))
        
        return {"status": "success", "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("HubSpot webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.get("/events", response_model=list[WebhookEventResponse])
async def get_webhook_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> list[WebhookEventResponse]:
    """
    Get recent webhook events.
    
    Args:
        limit: Maximum number of events to return
        db: Database session
        
    Returns:
        list[WebhookEventResponse]: Webhook events
    """
    try:
        from sqlalchemy import select, desc
        
        result = await db.execute(
            select(WebhookEvent)
            .order_by(desc(WebhookEvent.created_at))
            .limit(limit)
        )
        events = result.scalars().all()
        
        return [WebhookEventResponse.from_orm(event) for event in events]
        
    except Exception as e:
        logger.error("Failed to get webhook events", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook events"
        )


async def _get_webhook_by_url(url_path: str, db: AsyncSession) -> Webhook:
    """
    Get webhook configuration by URL path.
    
    Args:
        url_path: URL path
        db: Database session
        
    Returns:
        Webhook: Webhook configuration
    """
    try:
        from sqlalchemy import select
        
        # Extract webhook ID from URL path
        # This is a simplified implementation
        # In a real system, you might use a more sophisticated routing mechanism
        
        if "/gmail" in url_path:
            service = "gmail"
        elif "/calendar" in url_path:
            service = "calendar"
        elif "/hubspot" in url_path:
            service = "hubspot"
        else:
            return None
        
        result = await db.execute(
            select(Webhook)
            .join(Webhook.account)
            .where(Webhook.account.service == service)
            .where(Webhook.is_active == True)
        )
        return result.scalar_one_or_none()
        
    except Exception as e:
        logger.error("Failed to get webhook by URL", error=str(e))
        return None