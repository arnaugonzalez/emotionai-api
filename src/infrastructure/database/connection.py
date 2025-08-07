"""
Database Connection Management

Handles database connections, session management, and health checks
for the clean architecture infrastructure layer.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base

from ..config.settings import Settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()


class DatabaseConnection:
    """Database connection manager with async support"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self._is_connected = False
        
    async def connect(self) -> None:
        """Initialize database connection"""
        try:
            logger.info("Connecting to database...")
            
            # Create async engine with connection pooling
            async_database_url = self._get_async_database_url()
            self.async_engine = create_async_engine(
                async_database_url,
                echo=self.settings.database_echo,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_pre_ping=True,  # Verify connections before use
            )
            
            # Create sync engine for migrations and other sync operations
            self.engine = create_engine(
                self.settings.database_url,
                echo=self.settings.database_echo,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_pre_ping=True,  # Verify connections before use
                connect_args=self._get_connect_args()
            )
            
            # Create async session factory
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Create sync session factory (for migrations)
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            # Test connection with simple query (avoid circular dependency)
            try:
                session = self.session_factory()
                session.execute(text("SELECT 1"))
                session.close()
                logger.info("Database connection test successful")
            except Exception as e:
                logger.error(f"Database connection test failed: {e}")
                raise
            
            self._is_connected = True
            
            logger.info("Database connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _get_async_database_url(self) -> str:
        """Convert sync database URL to async format"""
        url = self.settings.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url
    
    def _get_connect_args(self) -> Dict[str, Any]:
        """Get database-specific connection arguments"""
        if "sqlite" in self.settings.database_url:
            return {
                "check_same_thread": False,
                "poolclass": StaticPool
            }
        elif "postgresql" in self.settings.database_url:
            return {
                "connect_timeout": 30
            }
        return {}
    
    async def disconnect(self) -> None:
        """Close database connection"""
        try:
            logger.info("Closing database connections...")
            if self.async_engine:
                await self.async_engine.dispose()
            if self.engine:
                self.engine.dispose()
            self._is_connected = False
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup"""
        if not self._is_connected:
            await self.connect()
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    def get_sync_session(self) -> Session:
        """Get synchronous database session (for legacy compatibility)"""
        if not self._is_connected:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        return self.session_factory()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                # Simple query to test connection
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def create_tables(self) -> None:
        """Create all database tables"""
        try:
            logger.info("Creating database tables...")
            
            # Import models module to ensure all models are registered with Base
            try:
                from . import models  # This will import all SQLAlchemy models
            except ImportError:
                logger.warning("Models module not found, creating tables with current metadata")
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)"""
        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def get_pool_size(self) -> int:
        """Get current database connection pool size"""
        if self.engine and hasattr(self.engine.pool, 'size'):
            return self.engine.pool.size()
        return 0
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed database pool status"""
        if not self.engine or not hasattr(self.engine.pool, 'status'):
            return {"status": "not_available"}
        
        pool = self.engine.pool
        return {
            "pool_size": getattr(pool, 'size', lambda: 0)(),
            "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
            "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
            "overflow": getattr(pool, 'overflow', lambda: 0)(),
            "invalid": getattr(pool, 'invalid', lambda: 0)()
        }
    
    @classmethod
    async def create(cls, settings: Settings) -> 'DatabaseConnection':
        """Factory method to create and connect database"""
        db = cls(settings)
        await db.connect()
        return db
    
    async def close(self) -> None:
        """Alias for disconnect for consistency"""
        await self.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected 