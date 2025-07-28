"""Database connection and session management"""
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import yaml
from pathlib import Path

# Load configuration
config_path = Path(__file__).parent.parent.parent / "configs" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

db_config = config['database']

# Build database URL
DATABASE_URL = f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['name']}"
SYNC_DATABASE_URL = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['name']}"


class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.engine: AsyncEngine = None
        self.async_session_factory = None
        self.sync_engine = None
        self.sync_session_factory = None
    
    async def initialize(self):
        """Initialize database connections"""
        # Async engine for main application
        self.engine = create_async_engine(
            DATABASE_URL,
            echo=config['app']['debug'],
            pool_size=db_config['pool_size'],
            max_overflow=db_config['max_overflow'],
            pool_pre_ping=True,
        )
        
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Sync engine for migrations and some operations
        self.sync_engine = create_engine(
            SYNC_DATABASE_URL,
            echo=config['app']['debug'],
            pool_size=db_config['pool_size'],
            max_overflow=db_config['max_overflow'],
            pool_pre_ping=True,
        )
        
        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False,
        )
    
    async def close(self):
        """Close all connections"""
        if self.engine:
            await self.engine.dispose()
        
        if self.sync_engine:
            self.sync_engine.dispose()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """Get sync database session"""
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with db_manager.get_session() as session:
        yield session


async def init_db():
    """Initialize database (create tables if not exist)"""
    from .models import Base
    
    await db_manager.initialize()
    
    # Create tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await db_manager.close()