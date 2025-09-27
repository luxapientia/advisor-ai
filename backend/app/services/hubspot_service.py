"""
HubSpot service for CRM API integration.

This service handles HubSpot OAuth authentication and provides methods
for interacting with HubSpot CRM APIs including contacts, companies, and deals.
"""

import secrets
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import structlog
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, OAuthError

logger = structlog.get_logger(__name__)


class HubSpotService:
    """
    HubSpot service for OAuth and API interactions.
    
    This service provides methods for HubSpot OAuth authentication,
    contact management, company management, and deal management.
    """
    
    # HubSpot OAuth scopes required for the application
    REQUIRED_SCOPES = [
        "crm.objects.contacts.write",
        "crm.schemas.deals.read",
        "oauth",
        "crm.objects.companies.write",
        "crm.objects.companies.read",
        "crm.objects.deals.read",
        "crm.schemas.contacts.read",
        "crm.objects.deals.write",
        "crm.objects.contacts.read",
        "crm.schemas.companies.read",
    ]
    
    def __init__(self):
        """Initialize the HubSpot service."""
        self.client_id = settings.HUBSPOT_CLIENT_ID
        self.client_secret = settings.HUBSPOT_CLIENT_SECRET
        self.redirect_uri = settings.HUBSPOT_REDIRECT_URI
        self.base_url = "https://api.hubapi.com"
    
    async def get_authorization_url(self, redirect_uri: str) -> tuple[str, str]:
        """
        Get HubSpot OAuth authorization URL.
        
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
                "scope": " ".join(self.REQUIRED_SCOPES),
                "response_type": "code",
                "state": state
            }
            
            # Build authorization URL
            auth_url = f"https://app.hubspot.com/oauth/authorize?{urlencode(params)}"
            
            logger.info("Generated HubSpot OAuth authorization URL", state=state)
            return auth_url, state
            
        except Exception as e:
            logger.error("Failed to generate HubSpot OAuth authorization URL", error=str(e))
            raise OAuthError("hubspot", "Failed to generate authorization URL")
    
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
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
            
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
            
            logger.info("Exchanged HubSpot OAuth code for tokens")
            return tokens
            
        except httpx.HTTPStatusError as e:
            logger.error("HubSpot OAuth token exchange failed", status_code=e.response.status_code, error=str(e))
            raise OAuthError("hubspot", "Failed to exchange code for tokens")
        except Exception as e:
            logger.error("HubSpot OAuth token exchange failed", error=str(e))
            raise OAuthError("hubspot", "Failed to exchange code for tokens")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from HubSpot.
        
        Args:
            access_token: HubSpot access token
            
        Returns:
            Dict: User information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/oauth/v1/access-tokens/{access_token}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                token_info = response.json()
            
            # Extract user information from token response
            user_info = {
                "id": str(token_info.get("user_id")),
                "email": token_info.get("user"),  # Email is in 'user' field
                "hub_id": token_info.get("hub_id"),
                "hub_domain": token_info.get("hub_domain"),
                "scopes": token_info.get("scopes", []),
            }
            
            logger.info("Retrieved HubSpot user info", email=user_info.get("email"))
            return user_info
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get HubSpot user info", status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get user information")
        except Exception as e:
            logger.error("Failed to get HubSpot user info", error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get user information")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh HubSpot access token.
        
        Args:
            refresh_token: HubSpot refresh token
            
        Returns:
            Dict: New tokens and metadata
        """
        try:
            # Token refresh parameters
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
            
            # Refresh token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
            
            logger.info("Refreshed HubSpot access token")
            return tokens
            
        except httpx.HTTPStatusError as e:
            logger.error("HubSpot token refresh failed", status_code=e.response.status_code, error=str(e))
            raise OAuthError("hubspot", "Failed to refresh access token")
        except Exception as e:
            logger.error("HubSpot token refresh failed", error=str(e))
            raise OAuthError("hubspot", "Failed to refresh access token")
    
    async def get_contacts(
        self,
        access_token: str,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get HubSpot contacts.
        
        Args:
            access_token: HubSpot access token
            limit: Maximum number of contacts to return
            after: Pagination cursor
            properties: List of properties to return
            
        Returns:
            Dict: Contacts and pagination information
        """
        try:
            # Default properties
            if properties is None:
                properties = [
                    "email", "firstname", "lastname", "phone", "company",
                    "createdate", "lastmodifieddate", "lifecyclestage"
                ]
            
            # Query parameters
            params = {
                "limit": limit,
                "properties": ",".join(properties)
            }
            
            if after:
                params["after"] = after
            
            # Get contacts
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/crm/v3/objects/contacts",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params
                )
                response.raise_for_status()
                contacts_data = response.json()
            
            logger.info("Retrieved HubSpot contacts", count=len(contacts_data.get("results", [])))
            return contacts_data
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get HubSpot contacts", status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contacts")
        except Exception as e:
            logger.error("Failed to get HubSpot contacts", error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contacts")
    
    async def get_contact_by_id(
        self,
        access_token: str,
        contact_id: str,
        properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get HubSpot contact by ID.
        
        Args:
            access_token: HubSpot access token
            contact_id: Contact ID
            properties: List of properties to return
            
        Returns:
            Dict: Contact information
        """
        try:
            # Default properties
            if properties is None:
                properties = [
                    "email", "firstname", "lastname", "phone", "company",
                    "createdate", "lastmodifieddate", "lifecyclestage"
                ]
            
            # Query parameters
            params = {
                "properties": ",".join(properties)
            }
            
            # Get contact
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params
                )
                response.raise_for_status()
                contact_data = response.json()
            
            logger.info("Retrieved HubSpot contact", contact_id=contact_id)
            return contact_data
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get HubSpot contact", contact_id=contact_id, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contact")
        except Exception as e:
            logger.error("Failed to get HubSpot contact", contact_id=contact_id, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contact")
    
    async def create_contact(
        self,
        access_token: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create HubSpot contact.
        
        Args:
            access_token: HubSpot access token
            email: Contact email address
            first_name: Contact first name
            last_name: Contact last name
            phone: Contact phone number
            company: Contact company
            additional_properties: Additional contact properties
            
        Returns:
            Dict: Created contact information
        """
        try:
            # Contact properties
            properties = {
                "email": email
            }
            
            if first_name:
                properties["firstname"] = first_name
            if last_name:
                properties["lastname"] = last_name
            if phone:
                properties["phone"] = phone
            if company:
                properties["company"] = company
            
            if additional_properties:
                properties.update(additional_properties)
            
            # Create contact
            contact_data = {
                "properties": properties
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/crm/v3/objects/contacts",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=contact_data
                )
                response.raise_for_status()
                created_contact = response.json()
            
            logger.info("Created HubSpot contact", contact_id=created_contact["id"], email=email)
            return created_contact
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to create HubSpot contact", email=email, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to create contact")
        except Exception as e:
            logger.error("Failed to create HubSpot contact", email=email, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to create contact")
    
    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update HubSpot contact.
        
        Args:
            access_token: HubSpot access token
            contact_id: Contact ID
            properties: Contact properties to update
            
        Returns:
            Dict: Updated contact information
        """
        try:
            # Update contact
            contact_data = {
                "properties": properties
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=contact_data
                )
                response.raise_for_status()
                updated_contact = response.json()
            
            logger.info("Updated HubSpot contact", contact_id=contact_id)
            return updated_contact
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to update HubSpot contact", contact_id=contact_id, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to update contact")
        except Exception as e:
            logger.error("Failed to update HubSpot contact", contact_id=contact_id, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to update contact")
    
    async def get_contact_notes(
        self,
        access_token: str,
        contact_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get HubSpot contact notes.
        
        Args:
            access_token: HubSpot access token
            contact_id: Contact ID
            limit: Maximum number of notes to return
            
        Returns:
            List: Contact notes
        """
        try:
            # Query parameters
            params = {
                "limit": limit,
                "properties": "hs_note_body,hs_timestamp,hs_attachment_ids"
            }
            
            # Get notes
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/crm/v3/objects/notes",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params
                )
                response.raise_for_status()
                notes_data = response.json()
            
            # Filter notes for this contact
            contact_notes = []
            for note in notes_data.get("results", []):
                if contact_id in note.get("associations", {}).get("contacts", {}).get("results", []):
                    contact_notes.append(note)
            
            logger.info("Retrieved HubSpot contact notes", contact_id=contact_id, count=len(contact_notes))
            return contact_notes
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get HubSpot contact notes", contact_id=contact_id, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contact notes")
        except Exception as e:
            logger.error("Failed to get HubSpot contact notes", contact_id=contact_id, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to get contact notes")
    
    async def create_contact_note(
        self,
        access_token: str,
        contact_id: str,
        note_body: str
    ) -> Dict[str, Any]:
        """
        Create HubSpot contact note.
        
        Args:
            access_token: HubSpot access token
            contact_id: Contact ID
            note_body: Note content
            
        Returns:
            Dict: Created note information
        """
        try:
            # Create note
            note_data = {
                "properties": {
                    "hs_note_body": note_body
                },
                "associations": [
                    {
                        "to": {
                            "id": contact_id
                        },
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 1  # Contact to Note association
                            }
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/crm/v3/objects/notes",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=note_data
                )
                response.raise_for_status()
                created_note = response.json()
            
            logger.info("Created HubSpot contact note", note_id=created_note["id"], contact_id=contact_id)
            return created_note
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to create HubSpot contact note", contact_id=contact_id, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to create contact note")
        except Exception as e:
            logger.error("Failed to create HubSpot contact note", contact_id=contact_id, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to create contact note")
    
    async def search_contacts(
        self,
        access_token: str,
        query: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search HubSpot contacts.
        
        Args:
            access_token: HubSpot access token
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List: Matching contacts
        """
        try:
            # Search parameters
            search_data = {
                "query": query,
                "limit": limit,
                "properties": ["email", "firstname", "lastname", "phone", "company"]
            }
            
            # Search contacts
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/crm/v3/objects/contacts/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=search_data
                )
                response.raise_for_status()
                search_results = response.json()
            
            contacts = search_results.get("results", [])
            logger.info("Searched HubSpot contacts", query=query, count=len(contacts))
            return contacts
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to search HubSpot contacts", query=query, status_code=e.response.status_code, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to search contacts")
        except Exception as e:
            logger.error("Failed to search HubSpot contacts", query=query, error=str(e))
            raise ExternalServiceError("hubspot", "Failed to search contacts")