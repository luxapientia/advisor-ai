"""
Actions endpoints for tool calling and task management.

This module handles tool execution, task creation, and management
for the AI assistant's action system.
"""

from typing import Dict, Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ValidationError, ExternalServiceError
from app.models.user import User
from app.models.task import Task, TaskExecutionLog
from app.services.tool_service import ToolService
from app.schemas.actions import (
    ToolExecutionRequest,
    ToolExecutionResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse
)
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ToolExecutionResponse:
    """
    Execute a tool with given parameters.
    
    Args:
        request: Tool execution request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ToolExecutionResponse: Tool execution result
    """
    try:
        tool_service = ToolService(db)
        
        # Execute tool
        result = await tool_service.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters,
            user=current_user
        )
        
        logger.info("Executed tool", user_id=str(current_user.id), tool_name=request.tool_name)
        
        return ToolExecutionResponse(
            tool_name=request.tool_name,
            success=result.get("success", False),
            result=result,
            error_message=result.get("error_message")
        )
        
    except ValidationError as e:
        logger.warning("Tool execution validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExternalServiceError as e:
        logger.error("Tool execution failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Tool execution failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tool execution failed"
        )


@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get available tools for the AI assistant.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[Dict]: Available tools
    """
    try:
        tool_service = ToolService(db)
        tools = tool_service.get_tools()
        
        return tools
        
    except Exception as e:
        logger.error("Failed to get available tools", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available tools"
        )


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Create a new task.
    
    Args:
        request: Task creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TaskResponse: Created task
    """
    try:
        # Create task
        task = Task(
            user_id=current_user.id,
            task_type=request.task_type,
            title=request.title,
            description=request.description,
            input_data=request.input_data,
            tool_name=request.tool_name,
            tool_parameters=request.tool_parameters,
            priority=request.priority,
            scheduled_for=request.scheduled_for
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info("Created task", user_id=str(current_user.id), task_id=str(task.id))
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """
    Get user's tasks.
    
    Args:
        status: Filter by task status
        task_type: Filter by task type
        limit: Maximum number of tasks
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TaskListResponse: User's tasks
    """
    try:
        # Build query
        query = select(Task).where(Task.user_id == current_user.id)
        
        if status:
            query = query.where(Task.status == status)
        if task_type:
            query = query.where(Task.task_type == task_type)
        
        query = query.order_by(Task.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return TaskListResponse(
            tasks=[TaskResponse.from_orm(task) for task in tasks],
            total=len(tasks)
        )
        
    except Exception as e:
        logger.error("Failed to get tasks", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tasks"
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Get a specific task.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TaskResponse: Task details
    """
    try:
        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == current_user.id
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return TaskResponse.from_orm(task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task"
        )


@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Update task status.
    
    Args:
        task_id: Task ID
        status: New status
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Update confirmation
    """
    try:
        # Verify task belongs to user
        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == current_user.id
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Update status
        task.status = status
        task.updated_at = datetime.utcnow()
        
        if status == "completed":
            task.completed_at = datetime.utcnow()
        elif status == "in_progress":
            task.started_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info("Updated task status", user_id=str(current_user.id), task_id=task_id, status=status)
        
        return {"message": "Task status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update task status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status"
        )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a task.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        # Verify task belongs to user
        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == current_user.id
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Delete task
        await db.delete(task)
        await db.commit()
        
        logger.info("Deleted task", user_id=str(current_user.id), task_id=task_id)
        
        return {"message": "Task deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )