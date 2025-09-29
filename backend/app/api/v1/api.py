"""
API v1 router configuration.

This module sets up the main API router for version 1 of the API,
including all endpoint routers and middleware.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, actions, rag, integrations, users, gmail_sync

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(gmail_sync.router, prefix="/gmail", tags=["gmail-sync"])