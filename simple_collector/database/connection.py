from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# 데이터베이스 엔진 생성
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 설정
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL 설정
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,  # SQL 로깅 비활성화 (프로덕션용)
        pool_pre_ping=True,  # 연결 유효성 검사
        pool_recycle=3600,   # 1시간마다 연결 재생성
        pool_size=10,
        max_overflow=20
    )

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()

def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """모든 테이블 생성"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """모든 테이블 삭제 (개발용)"""
    Base.metadata.drop_all(bind=engine)