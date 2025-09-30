"""
Google service for Gmail and Calendar API integration.

This service handles Google OAuth authentication and provides methods
for interacting with Gmail and Google Calendar APIs.
"""

import secrets
from datetime import datetime
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
            import base64
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            service = self.get_gmail_service(credentials)
            
            # Create MIME message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            sent_message = service.users().messages().send(
                userId="me",
                body={'raw': raw_message}
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
    
    async def get_calendar_availability(
        self,
        credentials: Credentials,
        time_min: str,
        time_max: str,
        calendar_id: str = "primary",
        duration_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get available time slots from calendar.
        
        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID
            time_min: Start time filter
            time_max: End time filter
            duration_minutes: Duration in minutes
            
        Returns:
            List: Available time slots
        """
        try:
            from datetime import datetime, timedelta
            import dateutil.parser
            
            service = self.get_calendar_service(credentials)
            
            # Get events in the time range
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=1000,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            # Parse time range
            start_time = dateutil.parser.parse(time_min)
            end_time = dateutil.parser.parse(time_max)
            duration = timedelta(minutes=duration_minutes)
            
            # Create list of busy periods
            busy_periods = []
            for event in events:
                event_start = event.get("start", {})
                event_end = event.get("end", {})
                
                if event_start.get("dateTime") and event_end.get("dateTime"):
                    busy_start = dateutil.parser.parse(event_start["dateTime"])
                    busy_end = dateutil.parser.parse(event_end["dateTime"])
                    busy_periods.append((busy_start, busy_end))
            
            # Sort busy periods by start time
            busy_periods.sort(key=lambda x: x[0])
            
            # Find available slots
            available_slots = []
            current_time = start_time
            
            for busy_start, busy_end in busy_periods:
                # Check if there's a gap before this busy period
                if current_time + duration <= busy_start:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": (current_time + duration).isoformat(),
                        "duration_minutes": duration_minutes
                    })
                
                # Move current time to after this busy period
                current_time = max(current_time, busy_end)
            
            # Check if there's time available after the last busy period
            if current_time + duration <= end_time:
                available_slots.append({
                    "start": current_time.isoformat(),
                    "end": (current_time + duration).isoformat(),
                    "duration_minutes": duration_minutes
                })
            
            logger.info("Retrieved Calendar availability", count=len(available_slots), calendar_id=calendar_id)
            return available_slots
            
        except Exception as e:
            logger.error("Failed to get Calendar availability", error=str(e))
            raise ExternalServiceError("calendar", "Failed to get Calendar availability")
    
    def _parse_calendar_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Google Calendar event data for RAG ingestion.
        
        Args:
            event: Raw Google Calendar event data
            
        Returns:
            Dict: Parsed event data with summary, content, and metadata
        """
        start = event.get("start", {})
        end = event.get("end", {})
        
        start_time = start.get("dateTime") or start.get("date", "")
        end_time = end.get("dateTime") or end.get("date", "")
        
        attendees = []
        for attendee in event.get("attendees", []):
            attendees.append({
                "email": attendee.get("email", ""),
                "name": attendee.get("displayName", ""),
                "status": attendee.get("responseStatus", "needsAction")
            })
        
        content_parts = []
        if event.get("description"):
            content_parts.append(f"Description: {event['description']}")
        
        if event.get("location"):
            content_parts.append(f"Location: {event['location']}")
        
        if attendees:
            attendee_list = ", ".join([f"{att['name']} ({att['email']})" for att in attendees if att['email']])
            if attendee_list:
                content_parts.append(f"Attendees: {attendee_list}")
        
        content = "\n".join(content_parts) if content_parts else event.get("summary", "")
        
        return {
            "id": event["id"],
            "summary": event.get("summary", ""),
            "description": event.get("description", ""),
            "start": start_time,
            "end": end_time,
            "location": event.get("location", ""),
            "attendees": attendees,
            "status": event.get("status", "confirmed"),
            "content": content,
            "metadata": {
                "start": start_time,
                "end": end_time,
                "attendees": attendees,
                "location": event.get("location", ""),
                "status": event.get("status", "confirmed"),
                "event_id": event["id"],
                "creator": event.get("creator", {}).get("email", ""),
                "organizer": event.get("organizer", {}).get("email", "")
            }
        }
    
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
    
    async def sync_gmail_emails(
        self,
        credentials: Credentials,
        user_id: str,
        rag_service,
        days_back: int = 90,
        max_results: int = 500,
        last_sync_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sync Gmail emails into the RAG system.
        
        Args:
            credentials: Google OAuth credentials
            user_id: User ID for RAG storage
            rag_service: RAG service instance for document ingestion
            days_back: Number of days back to sync emails (for first sync)
            max_results: Maximum number of emails to sync
            last_sync_time: Last sync completion time for incremental sync
            
        Returns:
            Dict: Sync results and statistics
        """
        try:
            logger.info("Starting Gmail email sync", user_id=user_id, days_back=days_back)
            
            # Create incremental query based on last sync
            if last_sync_time:
                # Convert to Gmail date format (YYYY/MM/DD)
                gmail_date = last_sync_time.strftime("%Y/%m/%d")
                query = f"after:{gmail_date}"
                logger.info("Using incremental sync", user_id=user_id, last_sync=gmail_date)
            else:
                # First sync - get last N days
                query = f"newer_than:{days_back}d"
                logger.info("Using full sync (first time)", user_id=user_id)
            
            messages = await self.get_gmail_messages(
                credentials=credentials,
                query=query,
                max_results=max_results
            )
            
            logger.info("Retrieved Gmail messages for sync", 
                user_id=user_id, 
                count=len(messages))

            # Process and ingest emails
            emails_synced = 0
            documents_created = 0

            for message in messages:
                try:
                    # Parse email data
                    email_data = self._parse_gmail_message(message)
                    
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
                    
                    documents_created += 1
                    emails_synced += 1
                    
                    # Log progress every 50 emails
                    if emails_synced % 50 == 0:
                        logger.info("Gmail sync progress", 
                            user_id=user_id, 
                            processed=emails_synced,
                            total=len(messages))
                
                except Exception as e:
                    logger.warning("Failed to process email during sync", 
                        user_id=user_id, 
                        message_id=message.get("id"),
                        error=str(e))
                    continue
            
            result = {
                "success": True,
                "emails_synced": emails_synced,
                "documents_created": documents_created,
                "total_retrieved": len(messages)
            }
            
            logger.info("Gmail email sync completed", 
                user_id=user_id, 
                emails_synced=emails_synced,
                documents_created=documents_created)
            
            return result
            
        except Exception as e:
            logger.error("Gmail email sync failed", user_id=user_id, error=str(e))
            return {
                "success": False,
                "reason": "sync_failed",
                "error": str(e),
                "emails_synced": 0
            }
    
    def _parse_gmail_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Gmail message into structured data.
        
        Args:
            message: Gmail message data
            
        Returns:
            Dict: Parsed email data
        """
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        
        # Extract headers
        subject = ""
        sender = ""
        date = ""
        to = ""
        
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            
            if name == "subject":
                subject = value
            elif name == "from":
                sender = value
            elif name == "date":
                date = value
            elif name == "to":
                to = value
        
        # Extract body content
        content = self._extract_email_body(payload)
        
        # Create metadata
        metadata = {
            "sender": sender,
            "recipient": to,
            "date": date,
            "message_id": message.get("id"),
            "thread_id": message.get("threadId"),
            "labels": message.get("labelIds", []),
            "snippet": message.get("snippet", "")
        }
        
        return {
            "id": message.get("id"),
            "subject": subject or "No Subject",
            "content": content,
            "metadata": metadata
        }
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body content from Gmail payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            str: Email body content
        """
        import base64
        
        body = ""
        
        # Check for multipart message
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                
                if mime_type == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        try:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                            break
                        except Exception:
                            continue
                elif mime_type == "text/html" and not body:
                    data = part.get("body", {}).get("data", "")
                    if data:
                        try:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                        except Exception:
                            continue
        else:
            # Single part message
            mime_type = payload.get("mimeType", "")
            if mime_type in ["text/plain", "text/html"]:
                data = payload.get("body", {}).get("data", "")
                if data:
                    try:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                    except Exception:
                        pass
        
        return body or "No content available"