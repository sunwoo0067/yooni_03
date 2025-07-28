"""
데이터베이스 연결 풀 최적화 설정
"""
import logging
from typing import AsyncGenerator, Generator, Optional
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, event, text, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from app.core.config import settings
from app.models.base import Base

logger = logging.getLogger(__name__)


class DatabasePoolConfig:
    """데이터베이스 연결 풀 설정"""
    
    # 연결 풀 크기 설정
    POOL_SIZE = 20  # 기본 풀 크기
    MAX_OVERFLOW = 10  # 추가 연결 허용 수
    POOL_TIMEOUT = 30  # 연결 대기 시간 (초)
    POOL_RECYCLE = 3600  # 연결 재활용 시간 (초)
    POOL_PRE_PING = True  # 연결 사전 확인
    
    # 환경별 설정
    if settings.ENVIRONMENT == "production":
        POOL_SIZE = 50
        MAX_OVERFLOW = 20
    elif settings.ENVIRONMENT == "development":
        POOL_SIZE = 5
        MAX_OVERFLOW = 5
        
    @classmethod
    def get_pool_args(cls) -> dict:
        """연결 풀 인자 반환"""
        # SQLite는 특별 처리
        if "sqlite" in settings.DATABASE_URL:
            return {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False}
            }
            
        # PostgreSQL, MySQL 등
        return {
            "poolclass": QueuePool,
            "pool_size": cls.POOL_SIZE,
            "max_overflow": cls.MAX_OVERFLOW,
            "pool_timeout": cls.POOL_TIMEOUT,
            "pool_recycle": cls.POOL_RECYCLE,
            "pool_pre_ping": cls.POOL_PRE_PING,
            "echo_pool": settings.DEBUG,  # 디버그 모드에서 풀 이벤트 로깅
        }
        
    @classmethod
    def get_async_pool_args(cls) -> dict:
        """비동기 연결 풀 인자 반환"""
        # SQLite는 특별 처리
        if "sqlite" in settings.DATABASE_URL:
            return {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False}
            }
            
        # 비동기 엔진에서는 AsyncAdaptedQueuePool이 자동으로 사용됨
        # poolclass를 명시적으로 지정하지 않음
        return {
            "pool_size": cls.POOL_SIZE,
            "max_overflow": cls.MAX_OVERFLOW,
            "pool_timeout": cls.POOL_TIMEOUT,
            "pool_recycle": cls.POOL_RECYCLE,
            "pool_pre_ping": cls.POOL_PRE_PING,
        }


# 동기 데이터베이스 엔진
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **DatabasePoolConfig.get_pool_args()
)

# 비동기 데이터베이스 엔진
if "sqlite" in settings.DATABASE_URL:
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=settings.DEBUG,
        **DatabasePoolConfig.get_async_pool_args()
    )
else:
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        **DatabasePoolConfig.get_async_pool_args()
    )

# 세션 메이커
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # 커밋 후 객체 만료 방지
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# 연결 이벤트 리스너
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 성능 최적화 설정"""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB 캐시
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB 메모리 맵
        cursor.close()


@event.listens_for(engine, "connect")
def set_postgresql_options(dbapi_connection, connection_record):
    """PostgreSQL 성능 최적화 설정"""
    if "postgresql" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone TO 'UTC'")
        cursor.execute("SET statement_timeout = '30s'")  # 쿼리 타임아웃
        cursor.execute("SET lock_timeout = '10s'")  # 락 타임아웃
        cursor.execute("SET idle_in_transaction_session_timeout = '60s'")
        cursor.close()


@event.listens_for(engine, "checkout")
def log_checkout(dbapi_connection, connection_record, connection_proxy):
    """연결 체크아웃 로깅 (디버그용)"""
    if settings.DEBUG:
        logger.debug(f"연결 체크아웃: {id(dbapi_connection)}")


@event.listens_for(engine, "checkin")
def log_checkin(dbapi_connection, connection_record):
    """연결 체크인 로깅 (디버그용)"""
    if settings.DEBUG:
        logger.debug(f"연결 체크인: {id(dbapi_connection)}")


# 의존성 함수
def get_db() -> Generator[Session, None, None]:
    """동기 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 세션 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """비동기 데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"비동기 데이터베이스 세션 오류: {e}")
            await db.rollback()
            raise
        finally:
            await db.close()


# 테스트용 별칭
get_async_session = get_async_db


# 컨텍스트 매니저
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """동기 데이터베이스 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """비동기 데이터베이스 컨텍스트 매니저"""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


# 연결 풀 모니터링
class PoolMonitor:
    """연결 풀 모니터링"""
    
    @staticmethod
    def get_pool_status() -> dict:
        """연결 풀 상태 조회"""
        pool = engine.pool
        
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "max_overflow": DatabasePoolConfig.MAX_OVERFLOW,
            "pool_size": DatabasePoolConfig.POOL_SIZE,
        }
        
    @staticmethod
    async def get_async_pool_status() -> dict:
        """비동기 연결 풀 상태 조회"""
        pool = async_engine.pool
        
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "max_overflow": DatabasePoolConfig.MAX_OVERFLOW,
            "pool_size": DatabasePoolConfig.POOL_SIZE,
        }
        
    @staticmethod
    def reset_pool():
        """연결 풀 재설정"""
        engine.dispose()
        logger.info("연결 풀 재설정 완료")
        
    @staticmethod
    async def reset_async_pool():
        """비동기 연결 풀 재설정"""
        await async_engine.dispose()
        logger.info("비동기 연결 풀 재설정 완료")


# 데이터베이스 헬스 체크
async def health_check() -> dict:
    """데이터베이스 헬스 체크"""
    try:
        # 동기 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            sync_ok = True
            
        # 비동기 연결 테스트
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            async_ok = True
            
        # 풀 상태
        pool_status = PoolMonitor.get_pool_status()
        async_pool_status = await PoolMonitor.get_async_pool_status()
        
        return {
            "status": "healthy",
            "sync_connection": sync_ok,
            "async_connection": async_ok,
            "sync_pool": pool_status,
            "async_pool": async_pool_status,
        }
        
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# 데이터베이스 초기화
def init_db():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)
    logger.info("데이터베이스 테이블 생성 완료")


async def init_async_db():
    """비동기 데이터베이스 테이블 생성"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("비동기 데이터베이스 테이블 생성 완료")


# 익스포트
__all__ = [
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_async_session",
    "get_db_context",
    "get_async_db_context",
    "PoolMonitor",
    "health_check",
    "init_db",
    "init_async_db",
]