"""
Chat endpoints for AI assistant interactions.

This module handles chat sessions, message processing, streaming responses,
and context management for the AI assistant.
"""

import json
from typing import Dict, Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.exceptions import ValidationError, AIError
from app.core.logging import log_ai_interaction
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.services.ai_service import AIService
from app.services.rag_service import RAGService
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatHistoryResponse,
    StreamResponse
)
from app.api.v1.endpoints.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatSessionResponse:
    """
    Create a new chat session.
    
    Args:
        request: HTTP request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse: Created chat session
    """
    try:
        # Create new chat session
        session = ChatSession(
            user_id=current_user.id,
            title="New Chat",
            context={}
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info("Created chat session", user_id=str(current_user.id), session_id=str(session.id))
        
        return ChatSessionResponse.from_orm(session)
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[ChatSessionResponse]:
    """
    Get user's chat sessions.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[ChatSessionResponse]: User's chat sessions
    """
    try:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = result.scalars().all()
        
        return [ChatSessionResponse.from_orm(session) for session in sessions]
        
    except Exception as e:
        logger.error("Failed to get chat sessions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatSessionResponse:
    """
    Get a specific chat session.
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse: Chat session
    """
    try:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        return ChatSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat session"
        )


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatHistoryResponse:
    """
    Get chat history for a session.
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatHistoryResponse: Chat history
    """
    try:
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Get messages
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=[ChatMessageResponse.from_orm(msg) for msg in messages]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get chat history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat history"
        )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatMessageResponse:
    """
    Send a message to the AI assistant.
    
    Args:
        session_id: Chat session ID
        request: Chat message request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatMessageResponse: AI response
    """
    try:
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.message,
            message_type="text"
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        
        # Get chat history for context
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)  # Last 10 messages for context
        )
        recent_messages = result.scalars().all()
        
        # Prepare messages for AI
        messages = []
        for msg in reversed(recent_messages):  # Reverse to get chronological order
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Get RAG context
        rag_service = RAGService(db)
        context = await rag_service.retrieve_context_for_query(
            user_id=str(current_user.id),
            query=request.message,
            limit=5
        )
        
        # Generate AI response
        ai_service = AIService()
        response_generator = ai_service.chat_completion(
            messages=messages,
            user_id=str(current_user.id),
            context=context
        )
        
        # Get the response
        ai_response = await response_generator.__anext__()
        
        # Save AI response
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response["content"],
            message_type="text",
            model_used=ai_response.get("model_used"),
            tokens_used=ai_response.get("tokens_used"),
            context_sources=[item["source"] for item in context] if context else None,
            tools_called=ai_response.get("tool_calls")
        )
        db.add(assistant_message)
        
        # Update session
        session.last_message_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(assistant_message)
        
        log_ai_interaction(
            interaction_type="chat",
            user_id=str(current_user.id),
            model=ai_response.get("model_used"),
            tokens_used=ai_response.get("tokens_used")
        )
        
        return ChatMessageResponse.from_orm(assistant_message)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to send message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Stream a message response from the AI assistant.
    
    Args:
        session_id: Chat session ID
        request: Chat message request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        StreamingResponse: Streamed AI response
    """
    try:
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.message,
            message_type="text"
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        
        # Get chat history for context
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        recent_messages = result.scalars().all()
        
        # Prepare messages for AI
        messages = []
        for msg in reversed(recent_messages):
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Get RAG context
        rag_service = RAGService(db)
        context = await rag_service.retrieve_context_for_query(
            user_id=str(current_user.id),
            query=request.message,
            limit=5
        )
        
        # Create streaming response
        async def generate_stream():
            try:
                # Create assistant message for streaming
                assistant_message = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content="",
                    message_type="text",
                    is_streaming=True,
                    is_complete=False
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)
                
                # Generate AI response
                ai_service = AIService()
                response_generator = ai_service.chat_completion(
                    messages=messages,
                    user_id=str(current_user.id),
                    context=context,
                    stream=True
                )
                
                full_content = ""
                async for chunk in response_generator:
                    if chunk["type"] == "content":
                        full_content += chunk["content"]
                        yield f"data: {json.dumps(chunk)}\n\n"
                    elif chunk["type"] == "finish":
                        # Update assistant message
                        assistant_message.content = full_content
                        assistant_message.is_streaming = False
                        assistant_message.is_complete = True
                        assistant_message.model_used = chunk.get("model_used")
                        assistant_message.tools_called = chunk.get("tool_calls")
                        assistant_message.context_sources = [item["source"] for item in context] if context else None
                        
                        # Update session
                        session.last_message_at = datetime.utcnow()
                        session.updated_at = datetime.utcnow()
                        
                        await db.commit()
                        
                        # Send final chunk
                        final_chunk = {
                            "type": "finish",
                            "message_id": str(assistant_message.id),
                            "content": full_content,
                            "model_used": chunk.get("model_used"),
                            "tools_called": chunk.get("tool_calls")
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        
                        log_ai_interaction(
                            interaction_type="chat_stream",
                            user_id=str(current_user.id),
                            model=chunk.get("model_used")
                        )
                        break
                    elif chunk["type"] == "error":
                        yield f"data: {json.dumps(chunk)}\n\n"
                        break
                
            except Exception as e:
                logger.error("Streaming error", error=str(e))
                error_chunk = {
                    "type": "error",
                    "error": "Streaming failed",
                    "content": "I apologize, but I encountered an error while processing your request."
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to stream message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream message"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a chat session.
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Delete session (messages will be deleted by cascade)
        await db.delete(session)
        await db.commit()
        
        logger.info("Deleted chat session", user_id=str(current_user.id), session_id=session_id)
        
        return {"message": "Chat session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )