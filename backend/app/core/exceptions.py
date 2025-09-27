"""
Custom exception classes for the Financial Advisor AI Assistant.

This module defines custom exceptions that provide structured error handling
and consistent error responses across the application.
"""

from typing import Any, Dict, Optional


class AdvisorAIException(Exception):
    """
    Base exception class for all application-specific exceptions.
    
    Provides structured error information with error codes, messages,
    and optional details for consistent error handling.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code for API responses
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AdvisorAIException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(AdvisorAIException):
    """Exception raised for authorization failures."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class ValidationError(AdvisorAIException):
    """Exception raised for data validation failures."""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class NotFoundError(AdvisorAIException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details=details
        )


class ConflictError(AdvisorAIException):
    """Exception raised for resource conflicts."""
    
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class RateLimitError(AdvisorAIException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class ExternalServiceError(AdvisorAIException):
    """Exception raised for external service failures."""
    
    def __init__(
        self,
        service: str,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details
        )


class DatabaseError(AdvisorAIException):
    """Exception raised for database operation failures."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class AIError(AdvisorAIException):
    """Exception raised for AI/LLM operation failures."""
    
    def __init__(self, message: str = "AI operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AI_ERROR",
            status_code=500,
            details=details
        )


class OAuthError(AdvisorAIException):
    """Exception raised for OAuth authentication failures."""
    
    def __init__(
        self,
        provider: str,
        message: str = "OAuth authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{provider} OAuth: {message}",
            error_code="OAUTH_ERROR",
            status_code=401,
            details=details
        )


class IntegrationError(AdvisorAIException):
    """Exception raised for third-party integration failures."""
    
    def __init__(
        self,
        integration: str,
        message: str = "Integration error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{integration}: {message}",
            error_code="INTEGRATION_ERROR",
            status_code=502,
            details=details
        )


class TaskError(AdvisorAIException):
    """Exception raised for background task failures."""
    
    def __init__(self, message: str = "Task execution failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="TASK_ERROR",
            status_code=500,
            details=details
        )


class ConfigurationError(AdvisorAIException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str = "Configuration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )