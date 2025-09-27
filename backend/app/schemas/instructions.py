"""
Instructions schemas for request/response validation.

This module defines Pydantic models for instruction-related
API requests and responses, including ongoing instruction management.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class OngoingInstructionCreateRequest(BaseModel):
    """Request schema for creating ongoing instructions."""
    
    title: str = Field(..., description="Instruction title", min_length=1, max_length=255)
    description: str = Field(..., description="Instruction description", min_length=1, max_length=1000)
    trigger_conditions: Dict[str, Any] = Field(..., description="Conditions for triggering the instruction")
    action_template: Dict[str, Any] = Field(..., description="Template for actions to execute")
    priority: int = Field(default=0, description="Instruction priority", ge=0, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Auto-create HubSpot contact for new emails",
                "description": "When I receive an email from someone not in HubSpot, create a contact with a note about the email",
                "trigger_conditions": {
                    "event_types": ["message_created"],
                    "sources": ["gmail"],
                    "custom_conditions": {
                        "contains_keywords": ["new client", "interested", "inquiry"]
                    }
                },
                "action_template": {
                    "tool_name": "hubspot_create_contact",
                    "parameters": {
                        "email": "{{event.sender_email}}",
                        "first_name": "{{event.sender_name}}",
                        "company": "{{event.sender_company}}"
                    }
                },
                "priority": 10
            }
        }


class OngoingInstructionUpdateRequest(BaseModel):
    """Request schema for updating ongoing instructions."""
    
    title: Optional[str] = Field(None, description="Instruction title", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Instruction description", min_length=1, max_length=1000)
    trigger_conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions for triggering the instruction")
    action_template: Optional[Dict[str, Any]] = Field(None, description="Template for actions to execute")
    priority: Optional[int] = Field(None, description="Instruction priority", ge=0, le=100)
    is_active: Optional[bool] = Field(None, description="Whether instruction is active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated instruction title",
                "description": "Updated instruction description",
                "is_active": False
            }
        }


class OngoingInstructionResponse(BaseModel):
    """Response schema for ongoing instructions."""
    
    id: str = Field(..., description="Instruction ID")
    user_id: str = Field(..., description="User ID")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    instruction_type: str = Field(..., description="Instruction type")
    title: str = Field(..., description="Instruction title")
    description: str = Field(..., description="Instruction description")
    trigger_conditions: Dict[str, Any] = Field(..., description="Trigger conditions")
    action_template: Dict[str, Any] = Field(..., description="Action template")
    is_active: bool = Field(..., description="Whether instruction is active")
    priority: int = Field(..., description="Instruction priority")
    trigger_count: int = Field(..., description="Number of times triggered")
    last_triggered_at: Optional[datetime] = Field(None, description="Last trigger timestamp")
    success_count: int = Field(..., description="Number of successful executions")
    failure_count: int = Field(..., description="Number of failed executions")
    success_rate: float = Field(..., description="Success rate percentage")
    is_expired: bool = Field(..., description="Whether instruction is expired")
    should_trigger: bool = Field(..., description="Whether instruction should trigger")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "task_id": None,
                "instruction_type": "email_rule",
                "title": "Auto-create HubSpot contact for new emails",
                "description": "When I receive an email from someone not in HubSpot, create a contact with a note about the email",
                "trigger_conditions": {
                    "event_types": ["message_created"],
                    "sources": ["gmail"],
                    "custom_conditions": {
                        "contains_keywords": ["new client", "interested", "inquiry"]
                    }
                },
                "action_template": {
                    "tool_name": "hubspot_create_contact",
                    "parameters": {
                        "email": "{{event.sender_email}}",
                        "first_name": "{{event.sender_name}}",
                        "company": "{{event.sender_company}}"
                    }
                },
                "is_active": True,
                "priority": 10,
                "trigger_count": 5,
                "last_triggered_at": "2024-01-01T00:00:00Z",
                "success_count": 4,
                "failure_count": 1,
                "success_rate": 80.0,
                "is_expired": False,
                "should_trigger": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "expires_at": None
            }
        }


class OngoingInstructionListResponse(BaseModel):
    """Response schema for ongoing instruction list."""
    
    instructions: List[OngoingInstructionResponse] = Field(..., description="List of instructions")
    total: int = Field(..., description="Total number of instructions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "instructions": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "title": "Auto-create HubSpot contact for new emails",
                        "description": "When I receive an email from someone not in HubSpot, create a contact with a note about the email",
                        "is_active": True,
                        "priority": 10,
                        "trigger_count": 5,
                        "success_rate": 80.0,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1
            }
        }