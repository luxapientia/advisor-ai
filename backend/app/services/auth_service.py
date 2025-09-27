"""
Authentication service for user management and JWT token handling.

This service handles user authentication, OAuth state management,
JWT token generation and validation, and user session management.
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from uuid import UUID

import structlog
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.models.user import User, UserSession
from app.schemas.auth import UserResponse

logger = structlog.get_logger(__name__)


class AuthService:
    """
    Authentication service for managing users and tokens.
    
    This service provides methods for user authentication, OAuth handling,
    JWT token management, and user session operations.
    """
    
    # Class-level shared storage for OAuth states across all instances
    _oauth_states: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the authentication service.
        
        Args:
            db: Database session
        """
        self.db = db
        # Use class-level shared storage instead of instance-level
        # self.oauth_states: Dict[str, Dict[str, Any]] = {}  # In-memory storage for OAuth states
    
    async def create_or_update_google_user(
        self,
        user_info: Dict[str, Any],
        tokens: Dict[str, Any]
    ) -> User:
        """
        Create or update user from Google OAuth information.
        
        Args:
            user_info: User information from Google
            tokens: OAuth tokens from Google
            
        Returns:
            User: Created or updated user
        """
        try:
            email = user_info.get("email")
            if not email:
                raise ValidationError("Email is required from Google OAuth")
            
            # Check if user exists
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                user.google_id = user_info.get("id")
                user.first_name = user_info.get("given_name")
                user.last_name = user_info.get("family_name")
                user.full_name = user_info.get("name")
                user.avatar_url = user_info.get("picture")
                user.google_access_token = tokens.get("access_token")
                user.google_refresh_token = tokens.get("refresh_token")
                
                # Calculate token expiration
                expires_in = tokens.get("expires_in", 3600)
                user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                user.updated_at = datetime.utcnow()
                user.is_verified = True
                
                logger.info("Updated existing Google user", user_id=str(user.id), email=email)
            else:
                # Create new user
                user = User(
                    email=email,
                    google_id=user_info.get("id"),
                    first_name=user_info.get("given_name"),
                    last_name=user_info.get("family_name"),
                    full_name=user_info.get("name"),
                    avatar_url=user_info.get("picture"),
                    google_access_token=tokens.get("access_token"),
                    google_refresh_token=tokens.get("refresh_token"),
                    is_verified=True,
                    is_active=True
                )
                
                # Calculate token expiration
                expires_in = tokens.get("expires_in", 3600)
                user.google_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                self.db.add(user)
                logger.info("Created new Google user", email=email)
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create/update Google user", error=str(e))
            raise AuthenticationError("Failed to create/update user from Google OAuth")
    
    async def create_or_update_hubspot_user(
        self,
        user_info: Dict[str, Any],
        tokens: Dict[str, Any]
    ) -> User:
        """
        Create or update user from HubSpot OAuth information.
        
        Args:
            user_info: User information from HubSpot
            tokens: OAuth tokens from HubSpot
            
        Returns:
            User: Created or updated user
        """
        try:
            email = user_info.get("email")
            if not email:
                raise ValidationError("Email is required from HubSpot OAuth")
            
            # Check if user exists
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                user.hubspot_id = user_info.get("id")
                user.first_name = user_info.get("first_name")
                user.last_name = user_info.get("last_name")
                user.full_name = user_info.get("full_name")
                user.avatar_url = user_info.get("avatar_url")
                user.hubspot_access_token = tokens.get("access_token")
                user.hubspot_refresh_token = tokens.get("refresh_token")
                
                # Calculate token expiration
                expires_in = tokens.get("expires_in", 3600)
                user.hubspot_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                user.updated_at = datetime.utcnow()
                user.is_verified = True
                
                logger.info("Updated existing HubSpot user", user_id=str(user.id), email=email)
            else:
                # Create new user
                user = User(
                    email=email,
                    hubspot_id=user_info.get("id"),
                    first_name=user_info.get("first_name"),
                    last_name=user_info.get("last_name"),
                    full_name=user_info.get("full_name"),
                    avatar_url=user_info.get("avatar_url"),
                    hubspot_access_token=tokens.get("access_token"),
                    hubspot_refresh_token=tokens.get("refresh_token"),
                    is_verified=True,
                    is_active=True
                )
                
                # Calculate token expiration
                expires_in = tokens.get("expires_in", 3600)
                user.hubspot_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                self.db.add(user)
                logger.info("Created new HubSpot user", email=email)
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create/update HubSpot user", error=str(e))
            raise AuthenticationError("Failed to create/update user from HubSpot OAuth")
    
    async def create_access_token(self, user_id: UUID) -> str:
        """
        Create JWT access token for user.
        
        Args:
            user_id: User ID
            
        Returns:
            str: JWT access token
        """
        try:
            # Token payload
            payload = {
                "sub": str(user_id),
                "type": "access",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            }
            
            # Generate token
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            
            logger.info("Created access token", user_id=str(user_id))
            return token
            
        except Exception as e:
            logger.error("Failed to create access token", user_id=str(user_id), error=str(e))
            raise AuthenticationError("Failed to create access token")
    
    async def create_refresh_token(self, user_id: UUID) -> str:
        """
        Create JWT refresh token for user.
        
        Args:
            user_id: User ID
            
        Returns:
            str: JWT refresh token
        """
        try:
            # Token payload
            payload = {
                "sub": str(user_id),
                "type": "refresh",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            }
            
            # Generate token
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            
            logger.info("Created refresh token", user_id=str(user_id))
            return token
            
        except Exception as e:
            logger.error("Failed to create refresh token", user_id=str(user_id), error=str(e))
            raise AuthenticationError("Failed to create refresh token")
    
    async def validate_refresh_token(self, refresh_token: str) -> UUID:
        """
        Validate refresh token and return user ID.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            UUID: User ID
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode token
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
            
            # Validate token type
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            # Get user ID
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")
            
            return UUID(user_id)
            
        except Exception as e:
            logger.error("Failed to validate refresh token", error=str(e))
            raise AuthenticationError("Invalid refresh token")
    
    async def create_user_session(
        self,
        user_id: UUID,
        access_token: str,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Create user session record.
        
        Args:
            user_id: User ID
            access_token: JWT access token
            refresh_token: JWT refresh token
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            UserSession: Created session
        """
        try:
            # Create session
            session = UserSession(
                user_id=user_id,
                session_token=access_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            logger.info("Created user session", user_id=str(user_id), session_id=str(session.id))
            return session
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create user session", user_id=str(user_id), error=str(e))
            raise AuthenticationError("Failed to create user session")
    
    async def update_user_session(
        self,
        old_refresh_token: str,
        new_access_token: str,
        new_refresh_token: str
    ) -> None:
        """
        Update user session with new tokens.
        
        Args:
            old_refresh_token: Old refresh token
            new_access_token: New access token
            new_refresh_token: New refresh token
        """
        try:
            # Update session
            await self.db.execute(
                update(UserSession)
                .where(UserSession.refresh_token == old_refresh_token)
                .values(
                    session_token=new_access_token,
                    refresh_token=new_refresh_token,
                    last_accessed_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                )
            )
            
            await self.db.commit()
            logger.info("Updated user session", old_token=old_refresh_token[:10] + "...")
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update user session", error=str(e))
            raise AuthenticationError("Failed to update user session")
    
    async def invalidate_user_session(self, user_id: UUID) -> None:
        """
        Invalidate all user sessions.
        
        Args:
            user_id: User ID
        """
        try:
            # Mark all sessions as inactive
            await self.db.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(is_active=False)
            )
            
            await self.db.commit()
            logger.info("Invalidated user sessions", user_id=str(user_id))
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to invalidate user sessions", user_id=str(user_id), error=str(e))
            raise AuthenticationError("Failed to invalidate user sessions")
    
    async def store_oauth_state(self, state: str, provider: str) -> None:
        """
        Store OAuth state for validation.
        
        Args:
            state: OAuth state parameter
            provider: OAuth provider name
        """
        try:
            AuthService._oauth_states[state] = {
                "provider": provider,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=10)
            }
            
            logger.info("Stored OAuth state", state=state, provider=provider)
            
        except Exception as e:
            logger.error("Failed to store OAuth state", state=state, provider=provider, error=str(e))
            raise AuthenticationError("Failed to store OAuth state")
    
    async def validate_oauth_state(self, state: str, provider: str) -> bool:
        """
        Validate OAuth state parameter.
        
        Args:
            state: OAuth state parameter
            provider: OAuth provider name
            
        Returns:
            bool: True if state is valid
        """
        try:
            if state not in AuthService._oauth_states:
                logger.warning("OAuth state not found", state=state)
                return False
            
            state_data = AuthService._oauth_states[state]
            
            # Check provider
            if state_data["provider"] != provider:
                logger.warning("OAuth state provider mismatch", state=state, expected=provider, actual=state_data["provider"])
                return False
            
            # Check expiration
            if datetime.utcnow() > state_data["expires_at"]:
                logger.warning("OAuth state expired", state=state)
                del AuthService._oauth_states[state]
                return False
            
            # Remove used state
            del AuthService._oauth_states[state]
            
            logger.info("Validated OAuth state", state=state, provider=provider)
            return True
            
        except Exception as e:
            logger.error("Failed to validate OAuth state", state=state, provider=provider, error=str(e))
            return False
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User if found
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=str(user_id), error=str(e))
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            Optional[User]: User if found
        """
        try:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            return None