"""
Authentication endpoints for OAuth and JWT token management.

This module handles Google OAuth, HubSpot OAuth, and JWT token
generation and validation for user authentication.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, OAuthError
from app.core.logging import log_auth_event
from app.models.user import User, UserSession
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService
from app.services.hubspot_service import HubSpotService
from app.services.rag_service import RAGService
from app.schemas.auth import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    HubSpotAuthRequest,
    HubSpotAuthResponse,
    TokenResponse,
    UserResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    Automatically refreshes expired Google access tokens.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        # Auto-refresh Google OAuth token if expired
        if (user.google_access_token and 
            user.google_refresh_token and 
            user.google_token_expires_at and 
            user.google_token_expires_at <= datetime.utcnow()):
            
            try:
                google_service = GoogleService()
                tokens = await google_service.refresh_access_token(user.google_refresh_token)
                
                # Update user with new tokens
                user.google_access_token = tokens["access_token"]
                user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
                
                logger.info("Auto-refreshed Google OAuth token", user_id=str(user.id))
                
            except Exception as e:
                logger.warning("Failed to auto-refresh Google OAuth token", user_id=str(user.id), error=str(e))
                # Don't raise exception - user can still use the app, just without Google features
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        return user
        
    except JWTError as e:
        logger.error("JWT token validation failed", error=str(e))
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        raise AuthenticationError("Authentication failed")


@router.post("/google/authorize", response_model=GoogleAuthResponse)
async def google_authorize(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> GoogleAuthResponse:
    """
    Initiate Google OAuth authorization flow.
    
    Args:
        request: Google OAuth request data
        db: Database session
        
    Returns:
        GoogleAuthResponse: Authorization URL and state
    """
    try:
        # Debug logging
        logger.info("Google OAuth request received", 
                   request_data=request.dict(),
                   request_type=type(request).__name__)
        
        auth_service = AuthService(db)
        google_service = GoogleService()
        
        # Generate authorization URL
        auth_url, state = await google_service.get_authorization_url(
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        # Store state for validation
        await auth_service.store_oauth_state(state, "google")
        
        logger.info("Google OAuth authorization initiated", state=state)
        
        return GoogleAuthResponse(
            authorization_url=auth_url,
            state=state
        )
        
    except Exception as e:
        logger.error("Google OAuth authorization failed", 
                    error=str(e), 
                    exc_info=True,
                    request_data=request.dict() if hasattr(request, 'dict') else str(request))
        raise OAuthError("google", "Failed to initiate authorization")


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Handle Google OAuth callback and create user session.
    
    Args:
        request: Google OAuth callback data
        db: Database session
        
    Returns:
        TokenResponse: JWT tokens and user information
    """
    try:
        auth_service = AuthService(db)
        google_service = GoogleService()
        
        # Validate state parameter
        if not await auth_service.validate_oauth_state(request.state, "google"):
            raise OAuthError("google", "Invalid state parameter")
        
        # Exchange authorization code for tokens
        tokens = await google_service.exchange_code_for_tokens(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        # Get user information from Google
        user_info = await google_service.get_user_info(tokens["access_token"])
        
        # Create or update user
        user = await auth_service.create_or_update_google_user(
            user_info=user_info,
            tokens=tokens
        )
        
        # Generate JWT tokens
        access_token = await auth_service.create_access_token(user.id)
        refresh_token = await auth_service.create_refresh_token(user.id)
        
        # Create user session
        await auth_service.create_user_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Note: Gmail sync is now handled on the chat page to avoid blocking login
        
        log_auth_event(
            event_type="login",
            user_id=str(user.id),
            email=user.email,
            provider="google",
            success=True
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        logger.error("Google OAuth callback failed", error=str(e))
        log_auth_event(
            event_type="login",
            email=request.email if hasattr(request, 'email') else None,
            provider="google",
            success=False,
            error=str(e)
        )
        raise OAuthError("google", "OAuth callback failed")


@router.post("/hubspot/authorize", response_model=HubSpotAuthResponse)
async def hubspot_authorize(
    request: HubSpotAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> HubSpotAuthResponse:
    """
    Initiate HubSpot OAuth authorization flow.
    
    Args:
        request: HubSpot OAuth request data
        db: Database session
        
    Returns:
        HubSpotAuthResponse: Authorization URL and state
    """
    try:
        auth_service = AuthService(db)
        hubspot_service = HubSpotService()
        
        # Generate authorization URL
        auth_url, state = await hubspot_service.get_authorization_url(
            redirect_uri=settings.HUBSPOT_REDIRECT_URI
        )
        
        # Store state for validation
        await auth_service.store_oauth_state(state, "hubspot")
        
        logger.info("HubSpot OAuth authorization initiated", state=state)
        
        return HubSpotAuthResponse(
            authorization_url=auth_url,
            state=state
        )
        
    except Exception as e:
        logger.error("HubSpot OAuth authorization failed", error=str(e))
        raise OAuthError("hubspot", "Failed to initiate authorization")


@router.post("/hubspot/callback", response_model=TokenResponse)
async def hubspot_callback(
    request: HubSpotAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Handle HubSpot OAuth callback and create user session.
    
    Args:
        request: HubSpot OAuth callback data
        db: Database session
        
    Returns:
        TokenResponse: JWT tokens and user information
    """
    try:
        auth_service = AuthService(db)
        hubspot_service = HubSpotService()
        
        # Validate state parameter
        if not await auth_service.validate_oauth_state(request.state, "hubspot"):
            raise OAuthError("hubspot", "Invalid state parameter")
        
        # Exchange authorization code for tokens
        tokens = await hubspot_service.exchange_code_for_tokens(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        # Get user information from HubSpot
        user_info = await hubspot_service.get_user_info(tokens["access_token"])
        
        # Create or update user
        user = await auth_service.create_or_update_hubspot_user(
            user_info=user_info,
            tokens=tokens
        )
        
        # Generate JWT tokens
        access_token = await auth_service.create_access_token(user.id)
        refresh_token = await auth_service.create_refresh_token(user.id)
        
        # Create user session
        await auth_service.create_user_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Trigger Gmail sync in background (if user has Google access)
        try:
            if user.has_google_access:
                google_service = GoogleService()
                rag_service = RAGService(db)
                
                # Create Google credentials from user tokens
                from google.oauth2.credentials import Credentials
                credentials = Credentials(
                    token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=None,
                    client_secret=None,
                    expiry=user.google_token_expires_at
                )
                
                # Run sync in background (don't await to avoid blocking login)
                asyncio.create_task(google_service.sync_gmail_emails(
                    credentials=credentials,
                    user_id=str(user.id),
                    rag_service=rag_service,
                    last_sync_time=user.google_sync_completed_at
                ))
                logger.info("Gmail sync triggered for user", user_id=str(user.id))
        except Exception as e:
            logger.warning("Failed to trigger Gmail sync", user_id=str(user.id), error=str(e))
        
        # Trigger HubSpot sync in background (if user has HubSpot access)
        try:
            if user.has_hubspot_access:
                # Import the HubSpot sync function
                from app.api.v1.endpoints.hubspot_sync import _run_hubspot_sync_with_progress
                
                # Run HubSpot sync in background (don't await to avoid blocking login)
                asyncio.create_task(_run_hubspot_sync_with_progress(
                    user_id=str(user.id),
                    access_token=user.hubspot_access_token
                ))
                logger.info("HubSpot sync triggered for user", user_id=str(user.id))
        except Exception as e:
            logger.warning("Failed to trigger HubSpot sync", user_id=str(user.id), error=str(e))
        
        log_auth_event(
            event_type="login",
            user_id=str(user.id),
            email=user.email,
            provider="hubspot",
            success=True
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        logger.error("HubSpot OAuth callback failed", error=str(e))
        log_auth_event(
            event_type="login",
            email=request.email if hasattr(request, 'email') else None,
            provider="hubspot",
            success=False,
            error=str(e)
        )
        raise OAuthError("hubspot", "OAuth callback failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh JWT access token using refresh token.
    
    Args:
        request: HTTP request
        db: Database session
        
    Returns:
        TokenResponse: New JWT tokens
    """
    try:
        auth_service = AuthService(db)
        
        # Get refresh token from request
        refresh_token = request.headers.get("refresh-token")
        if not refresh_token:
            raise AuthenticationError("Refresh token not provided")
        
        # Validate refresh token
        user_id = await auth_service.validate_refresh_token(refresh_token)
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Generate new tokens
        access_token = await auth_service.create_access_token(user.id)
        new_refresh_token = await auth_service.create_refresh_token(user.id)
        
        # Update user session
        await auth_service.update_user_session(
            old_refresh_token=refresh_token,
            new_access_token=access_token,
            new_refresh_token=new_refresh_token
        )
        
        log_auth_event(
            event_type="token_refresh",
            user_id=str(user.id),
            email=user.email,
            success=True
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        log_auth_event(
            event_type="token_refresh",
            success=False,
            error=str(e)
        )
        raise AuthenticationError("Token refresh failed")


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Logout user and invalidate session.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Logout confirmation
    """
    try:
        auth_service = AuthService(db)
        
        # Invalidate user session
        await auth_service.invalidate_user_session(current_user.id)
        
        log_auth_event(
            event_type="logout",
            user_id=str(current_user.id),
            email=current_user.email,
            success=True
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        log_auth_event(
            event_type="logout",
            user_id=str(current_user.id),
            email=current_user.email,
            success=False,
            error=str(e)
        )
        raise AuthenticationError("Logout failed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.from_orm(current_user)


@router.get("/google/callback")
async def google_callback_redirect(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback and redirect to frontend.
    
    Args:
        code: Authorization code from Google
        state: State parameter for validation
        db: Database session
        
    Returns:
        RedirectResponse: Redirect to frontend with tokens
    """
    from fastapi.responses import RedirectResponse
    import urllib.parse
    
    try:
        auth_service = AuthService(db)
        google_service = GoogleService()
        
        # Validate state parameter
        if not await auth_service.validate_oauth_state(state, "google"):
            raise OAuthError("google", "Invalid state parameter")
        
        # Exchange authorization code for tokens
        tokens = await google_service.exchange_code_for_tokens(
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        # Get user information from Google
        user_info = await google_service.get_user_info(tokens["access_token"])
        
        # Create or update user
        user = await auth_service.create_or_update_google_user(
            user_info=user_info,
            tokens=tokens
        )
        
        # Generate JWT tokens
        access_token = await auth_service.create_access_token(user.id)
        refresh_token = await auth_service.create_refresh_token(user.id)
        
        # Create user session
        await auth_service.create_user_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Note: Gmail sync is now handled on the chat page to avoid blocking login
        
        # Redirect to frontend with tokens
        frontend_url = f"{settings.FRONTEND_URL}/login"
        params = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": urllib.parse.quote(str(user.id))
        }
        
        redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error("Google OAuth callback failed", error=str(e))
        # Redirect to frontend with error
        frontend_url = f"{settings.FRONTEND_URL}/login"
        params = {"error": "authentication_failed"}
        redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url=redirect_url)


@router.get("/hubspot/callback")
async def hubspot_callback_redirect(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle HubSpot OAuth callback and redirect to frontend.
    
    Args:
        code: Authorization code from HubSpot
        state: State parameter for validation
        db: Database session
        
    Returns:
        RedirectResponse: Redirect to frontend with tokens
    """
    from fastapi.responses import RedirectResponse
    import urllib.parse
    
    try:
        auth_service = AuthService(db)
        hubspot_service = HubSpotService()
        
        # Validate state parameter
        if not await auth_service.validate_oauth_state(state, "hubspot"):
            raise OAuthError("hubspot", "Invalid state parameter")
        
        # Exchange authorization code for tokens
        tokens = await hubspot_service.exchange_code_for_tokens(
            code=code,
            redirect_uri=settings.HUBSPOT_REDIRECT_URI
        )
        
        # Get user information from HubSpot
        user_info = await hubspot_service.get_user_info(tokens["access_token"])
        
        # Create or update user
        user = await auth_service.create_or_update_hubspot_user(
            user_info=user_info,
            tokens=tokens
        )
        
        # Generate JWT tokens
        access_token = await auth_service.create_access_token(user.id)
        refresh_token = await auth_service.create_refresh_token(user.id)
        
        # Create user session
        await auth_service.create_user_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Trigger Gmail sync in background (if user has Google access)
        try:
            if user.has_google_access:
                google_service = GoogleService()
                rag_service = RAGService(db)
                
                # Create Google credentials from user tokens
                from google.oauth2.credentials import Credentials
                credentials = Credentials(
                    token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=None,
                    client_secret=None,
                    expiry=user.google_token_expires_at
                )
                
                # Run sync in background (don't await to avoid blocking login)
                asyncio.create_task(google_service.sync_gmail_emails(
                    credentials=credentials,
                    user_id=str(user.id),
                    rag_service=rag_service,
                    last_sync_time=user.google_sync_completed_at
                ))
                logger.info("Gmail sync triggered for user", user_id=str(user.id))
        except Exception as e:
            logger.warning("Failed to trigger Gmail sync", user_id=str(user.id), error=str(e))
        
        # Trigger HubSpot sync in background (if user has HubSpot access)
        try:
            if user.has_hubspot_access:
                # Import the HubSpot sync function
                from app.api.v1.endpoints.hubspot_sync import _run_hubspot_sync_with_progress
                
                # Run HubSpot sync in background (don't await to avoid blocking login)
                asyncio.create_task(_run_hubspot_sync_with_progress(
                    user_id=str(user.id),
                    access_token=user.hubspot_access_token
                ))
                logger.info("HubSpot sync triggered for user", user_id=str(user.id))
        except Exception as e:
            logger.warning("Failed to trigger HubSpot sync", user_id=str(user.id), error=str(e))
        
        # Redirect to frontend with tokens
        frontend_url = f"{settings.FRONTEND_URL}/login"
        params = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": urllib.parse.quote(str(user.id))
        }
        
        redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error("HubSpot OAuth callback failed", error=str(e))
        # Redirect to frontend with error
        frontend_url = f"{settings.FRONTEND_URL}/login"
        params = {"error": "authentication_failed"}
        redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url=redirect_url)