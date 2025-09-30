"""
Financial Advisor AI Assistant - Main FastAPI Application

This is the main entry point for the FastAPI backend application.
It sets up the application, middleware, routes, and database connections.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, ensure_pgvector_extension, check_database_connection
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.core.exceptions import AdvisorAIException

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    
    This handles:
    - Database connection check
    - pgvector extension check
    - Background task initialization
    - Cleanup on shutdown
    """
    logger.info("Starting Financial Advisor AI Assistant")
    
    # Check database connection
    if not await check_database_connection():
        raise Exception("Database connection failed")
    
    # Ensure pgvector extension is available
    await ensure_pgvector_extension()
    
    # Initialize background tasks
    # TODO: Initialize Celery workers, webhook handlers, etc.
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Financial Advisor AI Assistant")


# Create FastAPI application
app = FastAPI(
    title="Financial Advisor AI Assistant",
    description="AI assistant for financial advisors with Gmail, Calendar, and HubSpot integration",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# Security middleware
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["localhost", "127.0.0.1", "*.render.com", "*.fly.dev"]
# )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(AdvisorAIException)
async def advisor_ai_exception_handler(request: Request, exc: AdvisorAIException) -> JSONResponse:
    """
    Global exception handler for custom AdvisorAI exceptions.
    
    Args:
        request: The incoming request
        exc: The raised exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(
        "AdvisorAI exception occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unexpected exceptions.
    
    Args:
        request: The incoming request
        exc: The raised exception
        
    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        "Unexpected exception occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        }
    )


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "financial-advisor-ai",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root() -> dict:
    """
    Root endpoint with basic API information.
    
    Returns:
        dict: API information
    """
    return {
        "message": "Financial Advisor AI Assistant API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "Documentation not available in production",
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )