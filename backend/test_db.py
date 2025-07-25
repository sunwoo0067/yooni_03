#!/usr/bin/env python3
"""
Simple database test script
"""
import os
from sqlalchemy import create_engine, text
from app.core.config import settings

def test_database_connection():
    """Test database connection."""
    try:
        # Use sync URL
        engine = create_engine(settings.database_url_sync)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"Database connection successful! Test result: {row.test}")
            
        # Test database existence
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"Connected to database: {db_name}")
            
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
    return True

def create_tables_manually():
    """Create tables manually without Alembic.""" 
    try:
        from app.models.base import Base
        # Import all models explicitly
        from app.models import user, platform_account, product, order, inventory, ai_log
        
        engine = create_engine(settings.database_url_sync)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully!")
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"Created tables: {', '.join(tables)}")
            
    except Exception as e:
        print(f"Table creation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing database connection...")
    print(f"Database URL: {settings.DATABASE_URL}")
    
    if test_database_connection():
        print("\nCreating database tables...")
        create_tables_manually()
    else:
        print("Cannot proceed with table creation due to connection issues")