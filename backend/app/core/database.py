"""
Database configuration and connection management.

This module handles database connections, session management, and
table creation for the PostgreSQL database with pgvector support.
"""

import asyncio
from typing import AsyncGenerator

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """
    Base class for all database models.
    
    Provides common functionality and metadata for all ORM models.
    """
    pass


# Database engine for synchronous operations (for Alembic migrations)
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL logging - too verbose
    pool_pre_ping=True,
    pool_recycle=300,
)

# Database engine for asynchronous operations (for FastAPI)
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,  # Disable SQL logging - too verbose
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session for FastAPI endpoints.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def ensure_pgvector_extension() -> None:
    """
    Ensure pgvector extension is enabled.
    
    This should be run before migrations.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled")
    except Exception as e:
        logger.error("Failed to enable pgvector extension", error=str(e))
        raise




async def check_database_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


async def get_database_info() -> dict:
    """
    Get database information and statistics.
    
    Returns:
        dict: Database information
    """
    try:
        async with async_engine.begin() as conn:
            # Get database version
            version_result = await conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get pgvector version
            vector_result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            vector_version = vector_result.scalar()
            
            # Get table count
            table_result = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = table_result.scalar()
            
            return {
                "postgres_version": version,
                "pgvector_version": vector_version,
                "table_count": table_count,
                "connection_pool_size": async_engine.pool.size(),
                "checked_out_connections": async_engine.pool.checkedout(),
            }
    except Exception as e:
        logger.error("Failed to get database info", error=str(e))
        return {"error": str(e)}


class DatabaseManager:
    """
    Database manager for handling complex database operations.
    
    Provides methods for common database tasks like migrations,
    backups, and maintenance operations.
    """
    
    def __init__(self):
        self.engine = async_engine
        self.session_factory = AsyncSessionLocal
    
    async def execute_raw_sql(self, sql: str, params: dict = None) -> list:
        """
        Execute raw SQL query.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            list: Query results
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error("Raw SQL execution failed", sql=sql, error=str(e))
            raise
    
    async def get_table_stats(self, table_name: str) -> dict:
        """
        Get statistics for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Table statistics
        """
        try:
            sql = """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE tablename = :table_name
            """
            results = await self.execute_raw_sql(sql, {"table_name": table_name})
            
            return {
                "table_name": table_name,
                "columns": [
                    {
                        "name": row.attname,
                        "distinct_values": row.n_distinct,
                        "correlation": row.correlation
                    }
                    for row in results
                ]
            }
        except Exception as e:
            logger.error("Failed to get table stats", table_name=table_name, error=str(e))
            raise
    
    async def vacuum_table(self, table_name: str) -> bool:
        """
        Vacuum a specific table.
        
        Args:
            table_name: Name of the table to vacuum
            
        Returns:
            bool: True if successful
        """
        try:
            await self.execute_raw_sql(f"VACUUM ANALYZE {table_name}")
            logger.info("Table vacuumed successfully", table_name=table_name)
            return True
        except Exception as e:
            logger.error("Table vacuum failed", table_name=table_name, error=str(e))
            return False


# Global database manager instance
db_manager = DatabaseManager()