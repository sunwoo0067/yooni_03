"""
개인 사용자용 데이터베이스 서비스 모듈

이 모듈은 개인 사용자용 Yooni Dropshipping 플랫폼의 데이터베이스 연결 및 세션 관리를 담당합니다.
주요 기능:
- SQLite/PostgreSQL 자동 감지 및 연결
- 간소화된 연결 풀 관리
- 연결 상태 모니터링 및 헬스 체크
- 세션 생명주기 관리

Author: Yooni Development Team
"""

import logging
import os
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables from .env if present
load_dotenv()


def get_database_url() -> str:
    """
    환경 설정에 따라 데이터베이스 URL을 결정합니다.
    
    Returns:
        str: 데이터베이스 URL
    """
    # 개인 사용자 모드에서는 SQLite를 기본으로 사용
    if settings.ENVIRONMENT == "personal":
        default_url = "sqlite:///./yooni_personal.db"
    else:
        # 로컬 개발용 PostgreSQL
        default_url = "postgresql://postgres:12345678@localhost:5433/yooni_03"
    
    # 환경 변수에서 URL 가져오기 (우선순위 높음)
    db_url = os.getenv("DATABASE_URL", default_url)
    
    logger.info(f"Using database URL: {db_url}")
    return db_url


def create_sync_engine_safe(db_url: str):
    """
    동기 데이터베이스 엔진을 생성합니다.
    
    Args:
        db_url (str): 데이터베이스 URL
        
    Returns:
        Engine: SQLAlchemy 엔진
    """
    try:
        if "sqlite" in db_url:
            # SQLite 엔진 생성
            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                connect_args={"check_same_thread": False}  # SQLite 다중 스레드 지원
            )
            logger.info("SQLite 동기 엔진 생성 완료")
        elif "postgresql" in db_url:
            # PostgreSQL 엔진 생성
            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
            )
            logger.info("PostgreSQL 동기 엔진 생성 완료")
        else:
            # 기타 데이터베이스
            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
            )
            logger.info("기본 동기 엔진 생성 완료")
        
        return engine
    except Exception as e:
        logger.error(f"동기 엔진 생성 실패: {e}")
        raise


def create_async_engine_safe(db_url: str) -> Optional[Any]:
    """
    비동기 데이터베이스 엔진을 생성합니다.
    
    Args:
        db_url (str): 데이터베이스 URL
        
    Returns:
        AsyncEngine or None: SQLAlchemy 비동기 엔진 또는 None
    """
    try:
        if "sqlite" in db_url:
            # SQLite는 비동기 엔진을 지원하지 않음
            logger.info("SQLite는 비동기 엔진을 지원하지 않습니다")
            return None
        elif "postgresql" in db_url:
            # PostgreSQL 비동기 엔진 생성
            async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            engine = create_async_engine(
                async_db_url,
                echo=settings.DEBUG,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
                pool_reset_on_return="commit",
            )
            logger.info("PostgreSQL 비동기 엔진 생성 완료")
            return engine
        else:
            # 기타 데이터베이스는 비동기 엔진을 지원하지 않음
            logger.info("현재 데이터베이스는 비동기 엔진을 지원하지 않습니다")
            return None
    except Exception as e:
        logger.warning(f"비동기 엔진 생성 실패: {e}")
        return None


# 데이터베이스 URL 결정
DATABASE_URL = get_database_url()

# 동기 엔진 생성
engine = create_sync_engine_safe(DATABASE_URL)

# 비동기 엔진 생성 (SQLite는 제외)
async_engine = create_async_engine_safe(DATABASE_URL)

# 세션 팩토리 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)

AsyncSessionLocal = (
    sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    if async_engine
    else None
)


# SQLite용 이벤트 리스너
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 설정을 적용합니다."""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# PostgreSQL용 이벤트 리스너
@event.listens_for(engine, "connect")
def set_postgresql_timezone(dbapi_connection, connection_record):
    """PostgreSQL 타임존을 설정합니다."""
    if "postgresql" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone TO 'UTC'")
        cursor.close()


# 의존성 함수들
def get_db() -> Generator[Session, None, None]:
    """
    동기 데이터베이스 세션을 제공합니다.
    FastAPI 의존성으로 사용됩니다.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 세션 오류: {e}")
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error(f"롤백 실패: {rollback_error}")
        raise
    finally:
        try:
            db.close()
        except Exception as close_error:
            logger.error(f"세션 종료 실패: {close_error}")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    비동기 데이터베이스 세션을 제공합니다.
    FastAPI 의존성으로 사용됩니다.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("비동기 세션이 사용 불가능합니다")

    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"비동기 데이터베이스 세션 오류: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"비동기 롤백 실패: {rollback_error}")
            raise
        finally:
            try:
                await db.close()
            except Exception as close_error:
                logger.error(f"비동기 세션 종료 실패: {close_error}")


# 컨텍스트 매니저들
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """컨텍스트 매니저를 통해 데이터베이스 세션을 제공합니다."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"데이터베이스 컨텍스트 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """비동기 컨텍스트 매니저를 통해 데이터베이스 세션을 제공합니다."""
    if AsyncSessionLocal is None:
        raise RuntimeError("비동기 세션이 사용 불가능합니다")

    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception as e:
            logger.error(f"비동기 데이터베이스 컨텍스트 오류: {e}")
            await db.rollback()
            raise


class PersonalDatabaseManager:
    """개인 사용자용 데이터베이스 관리 클래스"""

    def __init__(self):
        self.engine = engine
        self.async_engine = async_engine
        self.session_factory = SessionLocal
        self.async_session_factory = AsyncSessionLocal

    def initialize(self):
        """데이터베이스를 초기화합니다."""
        try:
            logger.info(f"데이터베이스 초기화 중: {DATABASE_URL}")
            
            # 연결 테스트
            if not self.check_connection():
                raise ConnectionError("데이터베이스 연결 실패")
            
            # 테이블 생성
            self.create_tables()
            
            logger.info("데이터베이스 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    def create_tables(self):
        """데이터베이스 테이블을 생성합니다."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"데이터베이스 테이블 생성 오류: {e}")
            raise

    def drop_tables(self):
        """데이터베이스 테이블을 삭제합니다."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("데이터베이스 테이블 삭제 완료")
        except Exception as e:
            logger.error(f"데이터베이스 테이블 삭제 오류: {e}")
            raise

    def check_connection(self, max_retries: int = 3) -> bool:
        """데이터베이스 연결을 확인합니다."""
        for attempt in range(max_retries):
            try:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("데이터베이스 연결 성공")
                return True
            except Exception as e:
                logger.warning(f"데이터베이스 연결 시도 {attempt + 1}/{max_retries} 실패: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    logger.error(f"데이터베이스 연결 실패")
                    return False

    async def check_connection_async(self, max_retries: int = 3) -> bool:
        """비동기 데이터베이스 연결을 확인합니다."""
        if self.async_engine is None:
            logger.warning("비동기 엔진이 사용 불가능합니다")
            return False

        for attempt in range(max_retries):
            try:
                async with self.async_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("비동기 데이터베이스 연결 성공")
                return True
            except Exception as e:
                logger.warning(f"비동기 데이터베이스 연결 시도 {attempt + 1}/{max_retries} 실패: {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(1)
                else:
                    logger.error(f"비동기 데이터베이스 연결 실패")
                    return False

    def get_health_status(self) -> dict:
        """데이터베이스 상태를 확인합니다."""
        try:
            connection_status = self.check_connection(max_retries=1)
            
            # URL에서 비밀번호 마스킹
            masked_url = str(self.engine.url)
            if "@" in masked_url:
                parts = masked_url.split("@")
                if ":" in parts[0]:
                    user_pass = parts[0].split(":")
                    if len(user_pass) >= 3:
                        user_pass[-1] = "***"
                        parts[0] = ":".join(user_pass)
                masked_url = "@".join(parts)

            return {
                "status": "healthy" if connection_status else "unhealthy",
                "connection": connection_status,
                "url": masked_url,
                "driver": self.engine.dialect.name,
                "async_available": self.async_engine is not None,
            }
        except Exception as e:
            logger.error(f"상태 확인 오류: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def close(self):
        """데이터베이스 연결을 종료합니다."""
        try:
            if hasattr(self, "engine") and self.engine:
                self.engine.dispose()
                logger.info("데이터베이스 엔진 종료 완료")
        except Exception as e:
            logger.error(f"엔진 종료 오류: {e}")


# 데이터베이스 관리자 초기화
db_manager = PersonalDatabaseManager()


def init_db():
    """데이터베이스를 초기화합니다."""
    try:
        db_manager.initialize()
        logger.info("데이터베이스 초기화 성공")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise