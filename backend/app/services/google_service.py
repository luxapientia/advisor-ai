"""
Google service for Gmail and Calendar API integration.

This service handles Google OAuth authentication and provides methods
for interacting with Gmail and Google Calendar APIs.
"""

import secrets
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import structlog
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, OAuthError

logger = structlog.get_logger(__name__)


class GoogleService:
    """
    Google service for OAuth and API interactions.
    
    This service provides methods for Google OAuth authentication,
    Gmail API operations, and Google Calendar API operations.
    """
    
    def __init__(self):
        """Initialize the Google service."""
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # OAuth scopes
        self.scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ]
    
    async def get_authorization_url(self, redirect_uri: str) -> tuple[str, str]:
        """
        Get Google OAuth authorization URL.
        
        Args:
            redirect_uri: OAuth redirect URI
            
        Returns:
            tuple: (authorization_url, state)
        """
        try:
            # Generate state parameter
            state = secrets.token_urlsafe(32)
            
            # OAuth parameters
            params = {
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "scope": " ".join(self.scopes),
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
                "state": state
            }
            
            # Build authorization URL
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            
            logger.info("Generated Google OAuth authorization URL", state=state)
            return auth_url, state
            
        except Exception as e:
            logger.error("Failed to generate Google OAuth authorization URL", error=str(e))
            raise OAuthError("google", "Failed to generate authorization URL")
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: OAuth redirect URI
            
        Returns:
            Dict: OAuth tokens and metadata
        """
        try:
            # Token exchange parameters
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
            
            logger.info("Exchanged Google OAuth code for tokens")
            return tokens
            
        except httpx.HTTPStatusError as e:
            logger.error("Google OAuth token exchange failed", status_code=e.response.status_code, error=str(e))
            raise OAuthError("google", "Failed to exchange code for tokens")
        except Exception as e:
            logger.error("Google OAuth token exchange failed", error=str(e))
            raise OAuthError("google", "Failed to exchange code for tokens")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google.
        
        Args:
            access_token: Google access token
            
        Returns:
            Dict: User information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                user_info = response.json()
            
            logger.info("Retrieved Google user info", email=user_info.get("email"))
            return user_info
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get Google user info", status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("google", "Failed to get user information")
        except Exception as e:
            logger.error("Failed to get Google user info", error=str(e))
            raise ExternalServiceError("google", "Failed to get user information")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh Google access token.
        
        Args:
            refresh_token: Google refresh token
            
        Returns:
            Dict: New tokens and metadata
        """
        try:
            # Token refresh parameters
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            # Refresh token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
            
            logger.info("Refreshed Google access token")
            return tokens
            
        except httpx.HTTPStatusError as e:
            logger.error("Google token refresh failed", status_code=e.response.status_code, error=str(e))
            raise OAuthError("google", "Failed to refresh access token")
        except Exception as e:
            logger.error("Google token refresh failed", error=str(e))
            raise OAuthError("google", "Failed to refresh access token")
    
    def get_gmail_service(self, credentials: Credentials):
        """
        Get Gmail API service instance.
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            Gmail API service
        """
        try:
            service = build("gmail", "v1", credentials=credentials)
            logger.info("Created Gmail API service")
            return service
            
        except Exception as e:
            logger.error("Failed to create Gmail API service", error=str(e))
            raise ExternalServiceError("gmail", "Failed to create Gmail API service")
    
    def get_calendar_service(self, credentials: Credentials):
        """
        Get Google Calendar API service instance.
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            Calendar API service
        """
        try:
            service = build("calendar", "v3", credentials=credentials)
            logger.info("Created Calendar API service")
            return service
            
        except Exception as e:
            logger.error("Failed to create Calendar API service", error=str(e))
            raise ExternalServiceError("calendar", "Failed to create Calendar API service")
    
    async def get_gmail_messages(
        self,
        credentials: Credentials,
        query: str = "",
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get Gmail messages.
        
        Args:
            credentials: Google OAuth credentials
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List: Gmail messages
        """
        try:
            service = self.get_gmail_service(credentials)
            
            # Get message list
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get("messages", [])
            
            # Get full message details
            full_messages = []
            for message in messages:
                msg = service.users().messages().get(
                    userId="me",
                    id=message["id"],
                    format="full"
                ).execute()
                full_messages.append(msg)
            
            logger.info("Retrieved Gmail messages", count=len(full_messages), query=query)
            return full_messages
            
        except Exception as e:
            logger.error("Failed to get Gmail messages", error=str(e))
            raise ExternalServiceError("gmail", "Failed to get Gmail messages")
    
    async def send_gmail_message(
        self,
        credentials: Credentials,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send Gmail message.
        
        Args:
            credentials: Google OAuth credentials
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC email address
            bcc: BCC email address
            
        Returns:
            Dict: Sent message information
        """
        try:
            service = self.get_gmail_service(credentials)
            
            # Create message
            message = {
                "to": to,
                "subject": subject,
                "body": body
            }
            
            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc
            
            # Send message
            sent_message = service.users().messages().send(
                userId="me",
                body=message
            ).execute()
            
            logger.info("Sent Gmail message", message_id=sent_message["id"], to=to)
            return sent_message
            
        except Exception as e:
            logger.error("Failed to send Gmail message", error=str(e))
            raise ExternalServiceError("gmail", "Failed to send Gmail message")
    
    async def get_calendar_events(
        self,
        credentials: Credentials,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get Google Calendar events.
        
        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID
            time_min: Start time filter
            time_max: End time filter
            max_results: Maximum number of results
            
        Returns:
            List: Calendar events
        """
        try:
            service = self.get_calendar_service(credentials)
            
            # Get events
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            logger.info("Retrieved Calendar events", count=len(events), calendar_id=calendar_id)
            return events
            
        except Exception as e:
            logger.error("Failed to get Calendar events", error=str(e))
            raise ExternalServiceError("calendar", "Failed to get Calendar events")
    
    async def create_calendar_event(
        self,
        credentials: Credentials,
        calendar_id: str = "primary",
        summary: str = "",
        description: str = "",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create Google Calendar event.
        
        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID
            summary: Event summary
            description: Event description
            start_time: Event start time
            end_time: Event end time
            attendees: List of attendee email addresses
            
        Returns:
            Dict: Created event information
        """
        try:
            service = self.get_calendar_service(credentials)
            
            # Create event
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "UTC"
                }
            }
            
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]
            
            # Create event
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            logger.info("Created Calendar event", event_id=created_event["id"], summary=summary)
            return created_event
            
        except Exception as e:
            logger.error("Failed to create Calendar event", error=str(e))
            raise ExternalServiceError("calendar", "Failed to create Calendar event")