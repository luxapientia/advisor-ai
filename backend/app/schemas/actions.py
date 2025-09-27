"""
Actions schemas for request/response validation.

This module defines Pydantic models for action-related
API requests and responses, including tool execution and task management.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class ToolExecutionRequest(BaseModel):
    """Request schema for tool execution."""
    
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "gmail_send",
                "parameters": {
                    "to": "client@example.com",
                    "subject": "Meeting Follow-up",
                    "body": "Hi, thanks for the meeting today. Let's schedule a follow-up."
                }
            }
        }


class ToolExecutionResponse(BaseModel):
    """Response schema for tool execution."""
    
    tool_name: str = Field(..., description="Name of the executed tool")
    success: bool = Field(..., description="Whether execution was successful")
    result: Dict[str, Any] = Field(..., description="Tool execution result")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "gmail_send",
                "success": True,
                "result": {
                    "message_id": "msg_123456789",
                    "to": "client@example.com",
                    "subject": "Meeting Follow-up"
                },
                "error_message": None
            }
        }


class TaskCreateRequest(BaseModel):
    """Request schema for task creation."""
    
    task_type: str = Field(..., description="Type of task")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    tool_name: Optional[str] = Field(None, description="Tool name if applicable")
    tool_parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters if applicable")
    priority: int = Field(default=0, description="Task priority")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled execution time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_type": "tool_call",
                "title": "Send follow-up email",
                "description": "Send follow-up email to client after meeting",
                "input_data": {
                    "client_email": "client@example.com",
                    "meeting_date": "2024-01-01"
                },
                "tool_name": "gmail_send",
                "tool_parameters": {
                    "to": "client@example.com",
                    "subject": "Meeting Follow-up",
                    "body": "Hi, thanks for the meeting today."
                },
                "priority": 1,
                "scheduled_for": "2024-01-01T10:00:00Z"
            }
        }


class TaskResponse(BaseModel):
    """Response schema for task information."""
    
    id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="User ID")
    task_type: str = Field(..., description="Task type")
    status: str = Field(..., description="Task status")
    title: Optional[str] = Field(None, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    input_data: Dict[str, Any] = Field(..., description="Task input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Task output data")
    tool_name: Optional[str] = Field(None, description="Tool name")
    tool_parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    tool_result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    depends_on_task_id: Optional[str] = Field(None, description="Dependent task ID")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled execution time")
    priority: int = Field(..., description="Task priority")
    progress_percentage: int = Field(..., description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current step")
    total_steps: Optional[int] = Field(None, description="Total steps")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(..., description="Retry count")
    max_retries: int = Field(..., description="Maximum retries")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "task_type": "tool_call",
                "status": "completed",
                "title": "Send follow-up email",
                "description": "Send follow-up email to client after meeting",
                "input_data": {
                    "client_email": "client@example.com",
                    "meeting_date": "2024-01-01"
                },
                "output_data": {
                    "message_id": "msg_123456789",
                    "sent_at": "2024-01-01T10:00:00Z"
                },
                "tool_name": "gmail_send",
                "tool_parameters": {
                    "to": "client@example.com",
                    "subject": "Meeting Follow-up",
                    "body": "Hi, thanks for the meeting today."
                },
                "tool_result": {
                    "success": True,
                    "message_id": "msg_123456789"
                },
                "parent_task_id": None,
                "depends_on_task_id": None,
                "scheduled_for": None,
                "priority": 1,
                "progress_percentage": 100,
                "current_step": "completed",
                "total_steps": 1,
                "error_message": None,
                "retry_count": 0,
                "max_retries": 3,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:00:00Z"
            }
        }


class TaskListResponse(BaseModel):
    """Response schema for task list."""
    
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "task_type": "tool_call",
                        "status": "completed",
                        "title": "Send follow-up email",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1
            }
        }


class TaskExecutionLogResponse(BaseModel):
    """Response schema for task execution log."""
    
    id: str = Field(..., description="Log entry ID")
    task_id: str = Field(..., description="Task ID")
    execution_type: str = Field(..., description="Execution type")
    step_name: Optional[str] = Field(None, description="Step name")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data")
    error_data: Optional[Dict[str, Any]] = Field(None, description="Error data")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    memory_usage_mb: Optional[int] = Field(None, description="Memory usage in MB")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "task_id": "123e4567-e89b-12d3-a456-426614174001",
                "execution_type": "start",
                "step_name": "tool_execution",
                "input_data": {
                    "tool_name": "gmail_send",
                    "parameters": {"to": "client@example.com"}
                },
                "output_data": {
                    "success": True,
                    "message_id": "msg_123456789"
                },
                "error_data": None,
                "execution_time_ms": 1200,
                "memory_usage_mb": 50,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }