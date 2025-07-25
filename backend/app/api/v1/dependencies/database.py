"""
Database dependency for API endpoints
"""
from sqlalchemy.orm import Session
from app.services.database.database import SessionLocal


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()