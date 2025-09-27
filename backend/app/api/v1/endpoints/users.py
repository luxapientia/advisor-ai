"""
User endpoints for user management and profile operations.

This module handles user profile management, preferences,
and account settings.
"""

from typing import Dict, Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ValidationError, NotFoundError
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.users import UserUpdateRequest, UserPreferencesRequest
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user profile information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User profile information
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update current user profile information.
    
    Args:
        request: User update request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        # Update user fields
        if request.first_name is not None:
            current_user.first_name = request.first_name
        if request.last_name is not None:
            current_user.last_name = request.last_name
        if request.full_name is not None:
            current_user.full_name = request.full_name
        if request.avatar_url is not None:
            current_user.avatar_url = request.avatar_url
        
        # Update timestamp
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info("Updated user profile", user_id=str(current_user.id))
        
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update user profile", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.put("/me/preferences", response_model=UserResponse)
async def update_user_preferences(
    request: UserPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user preferences.
    
    Args:
        request: User preferences request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: Updated user profile
    """
    try:
        # Update preferences
        if current_user.preferences is None:
            current_user.preferences = {}
        
        current_user.preferences.update(request.preferences)
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info("Updated user preferences", user_id=str(current_user.id))
        
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update user preferences", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


@router.get("/me/integrations")
async def get_user_integrations(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's integration status.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict: Integration status information
    """
    return {
        "google": {
            "connected": current_user.has_google_access,
            "email": current_user.email if current_user.has_google_access else None,
            "scopes": ["gmail", "calendar"] if current_user.has_google_access else []
        },
        "hubspot": {
            "connected": current_user.has_hubspot_access,
            "email": current_user.email if current_user.has_hubspot_access else None,
            "scopes": ["contacts", "companies", "deals"] if current_user.has_hubspot_access else []
        }
    }


@router.delete("/me/account")
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete user account and all associated data.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        # Mark user as inactive instead of deleting
        current_user.is_active = False
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info("Deactivated user account", user_id=str(current_user.id))
        
        return {"message": "Account deactivated successfully"}
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to deactivate user account", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account"
        )