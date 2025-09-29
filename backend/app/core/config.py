"""
Application configuration management using Pydantic settings.
"""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application
    ENVIRONMENT: str = Field(default="development")
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4.1")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = Field(..., description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., description="Google OAuth client secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback"
    )
    
    # HubSpot OAuth
    HUBSPOT_CLIENT_ID: str = Field(..., description="HubSpot OAuth client ID")
    HUBSPOT_CLIENT_SECRET: str = Field(..., description="HubSpot OAuth client secret")
    HUBSPOT_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/v1/auth/hubspot/callback"
    )
    
    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # RAG Settings
    VECTOR_DIMENSION: int = Field(default=1536)
    SIMILARITY_THRESHOLD: float = Field(default=0.7)
    MAX_CONTEXT_LENGTH: int = Field(default=4000)
    
    # Background Tasks
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    # Test User
    TEST_USER_EMAIL: str = Field(default="webshookeng@gmail.com")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    return settings.DATABASE_URL


def get_redis_url() -> str:
    return settings.REDIS_URL


def is_development() -> bool:
    return settings.ENVIRONMENT == "development"


def is_production() -> bool:
    return settings.ENVIRONMENT == "production"