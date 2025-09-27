"""
Instructions endpoints for managing ongoing instructions and proactive behavior.

This module handles the creation, management, and monitoring of ongoing
instructions that drive the AI assistant's proactive behavior.
"""

from typing import Dict, Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.models.user import User
from app.models.task import OngoingInstruction
from app.services.proactive_agent import ProactiveAgent
from app.schemas.instructions import (
    OngoingInstructionCreateRequest,
    OngoingInstructionResponse,
    OngoingInstructionUpdateRequest,
    OngoingInstructionListResponse
)
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=OngoingInstructionResponse)
async def create_ongoing_instruction(
    request: OngoingInstructionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OngoingInstructionResponse:
    """
    Create a new ongoing instruction.
    
    Args:
        request: Instruction creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        OngoingInstructionResponse: Created instruction
    """
    try:
        proactive_agent = ProactiveAgent(db)
        
        # Create instruction
        instruction = await proactive_agent.create_ongoing_instruction(
            user_id=str(current_user.id),
            title=request.title,
            description=request.description,
            trigger_conditions=request.trigger_conditions,
            action_template=request.action_template,
            priority=request.priority
        )
        
        logger.info("Created ongoing instruction", user_id=str(current_user.id), instruction_id=str(instruction.id))
        
        return OngoingInstructionResponse.from_orm(instruction)
        
    except Exception as e:
        logger.error("Failed to create ongoing instruction", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ongoing instruction"
        )


@router.get("/", response_model=OngoingInstructionListResponse)
async def get_ongoing_instructions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OngoingInstructionListResponse:
    """
    Get user's ongoing instructions.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        OngoingInstructionListResponse: User's instructions
    """
    try:
        proactive_agent = ProactiveAgent(db)
        
        # Get instructions
        instructions = await proactive_agent.get_user_instructions(str(current_user.id))
        
        return OngoingInstructionListResponse(
            instructions=[OngoingInstructionResponse.from_orm(inst) for inst in instructions],
            total=len(instructions)
        )
        
    except Exception as e:
        logger.error("Failed to get ongoing instructions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ongoing instructions"
        )


@router.get("/{instruction_id}", response_model=OngoingInstructionResponse)
async def get_ongoing_instruction(
    instruction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OngoingInstructionResponse:
    """
    Get a specific ongoing instruction.
    
    Args:
        instruction_id: Instruction ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        OngoingInstructionResponse: Instruction details
    """
    try:
        from sqlalchemy import select
        
        # Get instruction
        result = await db.execute(
            select(OngoingInstruction).where(
                OngoingInstruction.id == instruction_id,
                OngoingInstruction.user_id == current_user.id
            )
        )
        instruction = result.scalar_one_or_none()
        
        if not instruction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instruction not found"
            )
        
        return OngoingInstructionResponse.from_orm(instruction)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get ongoing instruction", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ongoing instruction"
        )


@router.put("/{instruction_id}", response_model=OngoingInstructionResponse)
async def update_ongoing_instruction(
    instruction_id: str,
    request: OngoingInstructionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OngoingInstructionResponse:
    """
    Update an ongoing instruction.
    
    Args:
        instruction_id: Instruction ID
        request: Instruction update request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        OngoingInstructionResponse: Updated instruction
    """
    try:
        from sqlalchemy import select, update
        
        # Verify instruction belongs to user
        result = await db.execute(
            select(OngoingInstruction).where(
                OngoingInstruction.id == instruction_id,
                OngoingInstruction.user_id == current_user.id
            )
        )
        instruction = result.scalar_one_or_none()
        
        if not instruction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instruction not found"
            )
        
        # Update instruction
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.trigger_conditions is not None:
            update_data["trigger_conditions"] = request.trigger_conditions
        if request.action_template is not None:
            update_data["action_template"] = request.action_template
        if request.priority is not None:
            update_data["priority"] = request.priority
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        update_data["updated_at"] = datetime.utcnow()
        
        await db.execute(
            update(OngoingInstruction)
            .where(OngoingInstruction.id == instruction_id)
            .values(**update_data)
        )
        
        await db.commit()
        await db.refresh(instruction)
        
        logger.info("Updated ongoing instruction", user_id=str(current_user.id), instruction_id=instruction_id)
        
        return OngoingInstructionResponse.from_orm(instruction)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update ongoing instruction", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ongoing instruction"
        )


@router.delete("/{instruction_id}")
async def delete_ongoing_instruction(
    instruction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an ongoing instruction.
    
    Args:
        instruction_id: Instruction ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        from sqlalchemy import select, delete
        
        # Verify instruction belongs to user
        result = await db.execute(
            select(OngoingInstruction).where(
                OngoingInstruction.id == instruction_id,
                OngoingInstruction.user_id == current_user.id
            )
        )
        instruction = result.scalar_one_or_none()
        
        if not instruction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instruction not found"
            )
        
        # Delete instruction
        await db.execute(
            delete(OngoingInstruction).where(OngoingInstruction.id == instruction_id)
        )
        
        await db.commit()
        
        logger.info("Deleted ongoing instruction", user_id=str(current_user.id), instruction_id=instruction_id)
        
        return {"message": "Instruction deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete ongoing instruction", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete ongoing instruction"
        )


@router.put("/{instruction_id}/status")
async def update_instruction_status(
    instruction_id: str,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Update the status of an ongoing instruction.
    
    Args:
        instruction_id: Instruction ID
        is_active: Whether instruction is active
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Update confirmation
    """
    try:
        proactive_agent = ProactiveAgent(db)
        
        # Update status
        success = await proactive_agent.update_instruction_status(instruction_id, is_active)
        
        if success:
            return {"message": f"Instruction {'activated' if is_active else 'deactivated'} successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instruction not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update instruction status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update instruction status"
        )