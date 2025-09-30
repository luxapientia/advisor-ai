"""
Tool service for AI assistant tool calling and action execution.

This service handles tool definitions, validation, and execution
for Gmail, Google Calendar, and HubSpot integrations.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, ExternalServiceError
from app.models.user import User
from app.services.google_service import GoogleService
from app.services.hubspot_service import HubSpotService

logger = structlog.get_logger(__name__)


class ToolService:
    """
    Tool service for AI assistant tool calling.
    
    This service provides tool definitions, validation, and execution
    for various integrations and actions.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the tool service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.google_service = GoogleService()
        self.hubspot_service = HubSpotService()
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        Define available tools for the AI assistant.
        
        Returns:
            List[Dict]: Tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "gmail_send",
                    "description": "Send an email via Gmail",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body content"
                            },
                            "cc": {
                                "type": "string",
                                "description": "CC email address (optional)"
                            },
                            "bcc": {
                                "type": "string",
                                "description": "BCC email address (optional)"
                            }
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_search",
                    "description": "Search Gmail messages",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Gmail search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_get_events",
                    "description": "Get Google Calendar events",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: primary)",
                                "default": "primary"
                            },
                            "time_min": {
                                "type": "string",
                                "description": "Start time filter (ISO format)"
                            },
                            "time_max": {
                                "type": "string",
                                "description": "End time filter (ISO format)"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_get_availability",
                    "description": "Get available time slots from calendar",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: primary)",
                                "default": "primary"
                            },
                            "time_min": {
                                "type": "string",
                                "description": "Start time filter (ISO format)"
                            },
                            "time_max": {
                                "type": "string",
                                "description": "End time filter (ISO format)"
                            },
                            "duration_minutes": {
                                "type": "integer",
                                "description": "Duration in minutes",
                                "default": 30
                            }
                        },
                        "required": ["time_min", "time_max"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_create_event",
                    "description": "Create a Google Calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: primary)",
                                "default": "primary"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Event summary/title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Event description"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Event start time (ISO format)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Event end time (ISO format)"
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of attendee email addresses"
                            }
                        },
                        "required": ["summary", "start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "hubspot_get_contacts",
                    "description": "Get HubSpot contacts",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of contacts",
                                "default": 10
                            },
                            "properties": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Contact properties to return"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "hubspot_create_contact",
                    "description": "Create a HubSpot contact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Contact email address"
                            },
                            "first_name": {
                                "type": "string",
                                "description": "Contact first name"
                            },
                            "last_name": {
                                "type": "string",
                                "description": "Contact last name"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Contact phone number"
                            },
                            "company": {
                                "type": "string",
                                "description": "Contact company"
                            }
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "hubspot_create_note",
                    "description": "Create a HubSpot contact note",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "HubSpot contact ID"
                            },
                            "note_body": {
                                "type": "string",
                                "description": "Note content"
                            }
                        },
                        "required": ["contact_id", "note_body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "hubspot_search_contacts",
                    "description": "Search HubSpot contacts",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get available tools for the AI assistant.
        
        Returns:
            List[Dict]: Tool definitions
        """
        return self.tools
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user: User
    ) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user: User executing the tool
            
        Returns:
            Dict: Tool execution result
            
        Raises:
            ValidationError: If tool or parameters are invalid
            ExternalServiceError: If tool execution fails
        """
        try:
            # Validate tool exists
            tool_def = self._get_tool_definition(tool_name)
            if not tool_def:
                raise ValidationError(f"Unknown tool: {tool_name}")
            
            # Validate parameters
            self._validate_tool_parameters(tool_def, parameters)
            
            # Execute tool
            if tool_name == "gmail_send":
                return await self._execute_gmail_send(parameters, user)
            elif tool_name == "gmail_search":
                return await self._execute_gmail_search(parameters, user)
            elif tool_name == "calendar_get_events":
                return await self._execute_calendar_get_events(parameters, user)
            elif tool_name == "calendar_get_availability":
                return await self._execute_calendar_get_availability(parameters, user)
            elif tool_name == "calendar_create_event":
                return await self._execute_calendar_create_event(parameters, user)
            elif tool_name == "hubspot_get_contacts":
                return await self._execute_hubspot_get_contacts(parameters, user)
            elif tool_name == "hubspot_create_contact":
                return await self._execute_hubspot_create_contact(parameters, user)
            elif tool_name == "hubspot_create_note":
                return await self._execute_hubspot_create_note(parameters, user)
            elif tool_name == "hubspot_search_contacts":
                return await self._execute_hubspot_search_contacts(parameters, user)
            else:
                raise ValidationError(f"Tool execution not implemented: {tool_name}")
                
        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            raise ExternalServiceError("tool_execution", f"Tool execution failed: {str(e)}")
    
    def _get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool definition by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Optional[Dict]: Tool definition
        """
        for tool in self.tools:
            if tool["function"]["name"] == tool_name:
                return tool
        return None
    
    def _validate_tool_parameters(self, tool_def: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """
        Validate tool parameters against definition.
        
        Args:
            tool_def: Tool definition
            parameters: Parameters to validate
            
        Raises:
            ValidationError: If parameters are invalid
        """
        required_params = tool_def["function"]["parameters"].get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                raise ValidationError(f"Missing required parameter: {param}")
        
        # Check parameter types (basic validation)
        properties = tool_def["function"]["parameters"].get("properties", {})
        for param_name, param_value in parameters.items():
            if param_name in properties:
                param_type = properties[param_name].get("type")
                if param_type == "string" and not isinstance(param_value, str):
                    raise ValidationError(f"Parameter {param_name} must be a string")
                elif param_type == "integer" and not isinstance(param_value, int):
                    raise ValidationError(f"Parameter {param_name} must be an integer")
                elif param_type == "array" and not isinstance(param_value, list):
                    raise ValidationError(f"Parameter {param_name} must be an array")
    
    async def _execute_gmail_send(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute Gmail send tool."""
        if not user.has_google_access:
            raise ExternalServiceError("gmail", "User does not have Google access")
        
        # Get Google credentials
        credentials = self._get_google_credentials(user)
        
        # Send email
        result = await self.google_service.send_gmail_message(
            credentials=credentials,
            to=parameters["to"],
            subject=parameters["subject"],
            body=parameters["body"],
            cc=parameters.get("cc"),
            bcc=parameters.get("bcc")
        )
        
        return {
            "success": True,
            "message_id": result["id"],
            "to": parameters["to"],
            "subject": parameters["subject"]
        }
    
    async def _execute_gmail_search(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute Gmail search tool."""
        if not user.has_google_access:
            raise ExternalServiceError("gmail", "User does not have Google access")
        
        # Get Google credentials
        credentials = self._get_google_credentials(user)
        
        # Search emails
        messages = await self.google_service.get_gmail_messages(
            credentials=credentials,
            query=parameters["query"],
            max_results=parameters.get("max_results", 10)
        )
        
        # Format results
        results = []
        for msg in messages:
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            
            # Extract common headers
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")
            
            results.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "date": date,
                "snippet": msg.get("snippet", "")
            })
        
        return {
            "success": True,
            "query": parameters["query"],
            "results": results,
            "total": len(results)
        }
    
    async def _execute_calendar_get_events(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute calendar get events tool."""
        if not user.has_google_access:
            raise ExternalServiceError("calendar", "User does not have Google access")
        
        # Get Google credentials
        credentials = self._get_google_credentials(user)
        
        # Get events
        events = await self.google_service.get_calendar_events(
            credentials=credentials,
            calendar_id=parameters.get("calendar_id", "primary"),
            time_min=parameters.get("time_min"),
            time_max=parameters.get("time_max"),
            max_results=parameters.get("max_results", 10)
        )
        
        # Format results
        results = []
        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})
            
            results.append({
                "id": event["id"],
                "summary": event.get("summary", ""),
                "description": event.get("description", ""),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "attendees": [att.get("email") for att in event.get("attendees", [])],
                "status": event.get("status", "")
            })
        
        return {
            "success": True,
            "calendar_id": parameters.get("calendar_id", "primary"),
            "events": results,
            "total": len(results)
        }
    
    async def _execute_calendar_get_availability(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute calendar get availability tool."""
        if not user.has_google_access:
            raise ExternalServiceError("calendar", "User does not have Google access")
        
        # Get Google credentials
        credentials = self._get_google_credentials(user)
        
        # Get available time slots
        availability = await self.google_service.get_calendar_availability(
            credentials=credentials,
            time_min=parameters["time_min"],
            time_max=parameters["time_max"],
            calendar_id=parameters.get("calendar_id", "primary"),
            duration_minutes=parameters.get("duration_minutes", 30)
        )
        
        return {
            "success": True,
            "calendar_id": parameters.get("calendar_id", "primary"),
            "available_slots": availability,
            "total": len(availability)
        }
    
    async def _execute_calendar_create_event(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute calendar create event tool."""
        if not user.has_google_access:
            raise ExternalServiceError("calendar", "User does not have Google access")
        
        # Get Google credentials
        credentials = self._get_google_credentials(user)
        
        # Create event
        result = await self.google_service.create_calendar_event(
            credentials=credentials,
            calendar_id=parameters.get("calendar_id", "primary"),
            summary=parameters["summary"],
            description=parameters.get("description", ""),
            start_time=parameters["start_time"],
            end_time=parameters["end_time"],
            attendees=parameters.get("attendees")
        )
        
        return {
            "success": True,
            "event_id": result["id"],
            "summary": result.get("summary", ""),
            "start": result.get("start", {}).get("dateTime"),
            "end": result.get("end", {}).get("dateTime")
        }
    
    async def _execute_hubspot_get_contacts(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute HubSpot get contacts tool."""
        if not user.has_hubspot_access:
            raise ExternalServiceError("hubspot", "User does not have HubSpot access")
        
        # Get HubSpot access token
        access_token = user.hubspot_access_token
        
        # Get contacts
        contacts_data = await self.hubspot_service.get_contacts(
            access_token=access_token,
            limit=parameters.get("limit", 10),
            properties=parameters.get("properties")
        )
        
        return {
            "success": True,
            "contacts": contacts_data.get("results", []),
            "total": len(contacts_data.get("results", []))
        }
    
    async def _execute_hubspot_create_contact(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute HubSpot create contact tool."""
        if not user.has_hubspot_access:
            raise ExternalServiceError("hubspot", "User does not have HubSpot access")
        
        # Get HubSpot access token
        access_token = user.hubspot_access_token
        
        # Create contact
        result = await self.hubspot_service.create_contact(
            access_token=access_token,
            email=parameters["email"],
            first_name=parameters.get("first_name"),
            last_name=parameters.get("last_name"),
            phone=parameters.get("phone"),
            company=parameters.get("company")
        )
        
        return {
            "success": True,
            "contact_id": result["id"],
            "email": result["properties"].get("email", ""),
            "name": f"{result['properties'].get('firstname', '')} {result['properties'].get('lastname', '')}".strip()
        }
    
    async def _execute_hubspot_create_note(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute HubSpot create note tool."""
        if not user.has_hubspot_access:
            raise ExternalServiceError("hubspot", "User does not have HubSpot access")
        
        # Get HubSpot access token
        access_token = user.hubspot_access_token
        
        # Create note
        result = await self.hubspot_service.create_contact_note(
            access_token=access_token,
            contact_id=parameters["contact_id"],
            note_body=parameters["note_body"]
        )
        
        return {
            "success": True,
            "note_id": result["id"],
            "contact_id": parameters["contact_id"],
            "note_body": parameters["note_body"]
        }
    
    async def _execute_hubspot_search_contacts(self, parameters: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Execute HubSpot search contacts tool."""
        if not user.has_hubspot_access:
            raise ExternalServiceError("hubspot", "User does not have HubSpot access")
        
        # Get HubSpot access token
        access_token = user.hubspot_access_token
        
        # Search contacts
        results = await self.hubspot_service.search_contacts(
            access_token=access_token,
            query=parameters["query"],
            limit=parameters.get("limit", 10)
        )
        
        return {
            "success": True,
            "query": parameters["query"],
            "contacts": results,
            "total": len(results)
        }
    
    def _get_google_credentials(self, user: User):
        """Get Google OAuth credentials for user with auto-refresh."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from app.core.config import settings
        
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        # Auto-refresh if expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                logger.info("Auto-refreshed Google credentials for tool execution")
            except Exception as e:
                logger.error("Failed to refresh Google credentials", error=str(e))
                raise ExternalServiceError("google", "Failed to refresh credentials")
        
        return credentials