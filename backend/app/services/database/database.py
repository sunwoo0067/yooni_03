"""
Database connection and session management.
"""
import logging
from typing import AsyncGenerator, Generator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.base import Base
from app.core.database import DatabasePoolConfig

# Setup logging
logger = logging.getLogger(__name__)

# Synchronous database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# Asynchronous database engine - SQLite 및 PostgreSQL 지원
try:
    if "sqlite" in settings.DATABASE_URL:
        async_engine = create_async_engine(
            settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=settings.DEBUG,
        )
    elif "postgresql" in settings.DATABASE_URL:
        # PostgreSQL async 엔진 지원
        async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        async_engine = create_async_engine(
            async_db_url,
            echo=settings.DEBUG,
            **DatabasePoolConfig.get_async_pool_args()
        )
    else:
        # 다른 DB의 경우 async 엔진 비활성화
        async_engine = None
        logger.warning(f"Unsupported database for async operations: {settings.DATABASE_URL}")
except Exception as e:
    logger.warning(f"Async engine 초기화 실패, 동기 모드만 사용: {e}")
    async_engine = None

# Session makers
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Database connection events
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite)."""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=1000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


@event.listens_for(engine, "connect")
def set_postgresql_timezone(dbapi_connection, connection_record):
    """Set PostgreSQL timezone."""
    if "postgresql" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone TO 'UTC'")
        cursor.close()


# Dependency functions for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Get synchronous database session.
    Used as FastAPI dependency.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get asynchronous database session.
    Used as FastAPI dependency for async endpoints.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await db.rollback()
            raise
        finally:
            await db.close()


# Context managers
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Get database session with context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with context manager."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception as e:
            logger.error(f"Async database context error: {e}")
            await db.rollback()
            raise


# Database initialization and management
class DatabaseManager:
    """Database management utilities."""
    
    @staticmethod
    def create_tables():
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    @staticmethod
    def drop_tables():
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    @staticmethod
    async def create_tables_async():
        """Create all database tables asynchronously."""
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully (async)")
        except Exception as e:
            logger.error(f"Error creating database tables (async): {e}")
            raise
    
    @staticmethod
    async def drop_tables_async():
        """Drop all database tables asynchronously."""
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully (async)")
        except Exception as e:
            logger.error(f"Error dropping database tables (async): {e}")
            raise
    
    @staticmethod
    def check_connection():
        """Check database connection."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    @staticmethod
    async def check_connection_async():
        """Check async database connection."""
        try:
            async with async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Async database connection successful")
            return True
        except Exception as e:
            logger.error(f"Async database connection failed: {e}")
            return False
    
    @staticmethod
    def get_table_info():
        """Get information about database tables."""
        try:
            with engine.connect() as conn:
                result = conn.execute("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                """)
                return result.fetchall()
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return []
    
    @staticmethod
    def backup_database(backup_path: str):
        """Create database backup (PostgreSQL specific)."""
        import subprocess
        import os
        
        try:
            # Extract connection details from DATABASE_URL
            db_url = settings.DATABASE_URL
            # This is a simplified example - you might want to use a proper URL parser
            
            env = os.environ.copy()
            env['PGPASSWORD'] = '1234'  # Password from connection string
            
            cmd = [
                'pg_dump',
                '-h', 'localhost',
                '-p', '5433',
                '-U', 'postgress',
                '-d', 'yooni_03',
                '-f', backup_path
            ]
            
            subprocess.run(cmd, env=env, check=True)
            logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    @staticmethod
    def restore_database(backup_path: str):
        """Restore database from backup (PostgreSQL specific)."""
        import subprocess
        import os
        
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = '1234'  # Password from connection string
            
            cmd = [
                'psql',
                '-h', 'localhost',
                '-p', '5433',
                '-U', 'postgress',
                '-d', 'yooni_03',
                '-f', backup_path
            ]
            
            subprocess.run(cmd, env=env, check=True)
            logger.info(f"Database restored from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False


# Initialize database manager
db_manager = DatabaseManager()

# Simple init_db function for compatibility
def init_db():
    """Initialize database tables."""
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# Health check function
async def health_check() -> dict:
    """Perform database health check."""
    try:
        sync_ok = db_manager.check_connection()
        async_ok = await db_manager.check_connection_async()
        
        return {
            "database": {
                "sync_connection": sync_ok,
                "async_connection": async_ok,
                "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "hidden",
                "status": "healthy" if sync_ok and async_ok else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "database": {
                "sync_connection": False,
                "async_connection": False,
                "status": "unhealthy",
                "error": str(e)
            }
        }


# Export commonly used items
__all__ = [
    "engine",
    "async_engine", 
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_db_context",
    "get_async_db_context",
    "DatabaseManager",
    "db_manager",
    "init_db",
    "health_check",
]