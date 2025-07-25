"""
헬스 체크 엔드포인트
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db

router = APIRouter()


@router.get("/database")
async def check_database_health(db: Session = Depends(get_db)):
    """데이터베이스 연결 상태 확인"""
    try:
        # 간단한 쿼리 실행
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        
        # 테이블 수 확인
        table_count_result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = table_count_result.scalar()
        
        return {
            "status": "healthy",
            "database": {
                "connected": True,
                "tables": table_count,
                "message": "Database is operational"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": {
                "connected": False,
                "error": str(e),
                "message": "Database connection failed"
            }
        }