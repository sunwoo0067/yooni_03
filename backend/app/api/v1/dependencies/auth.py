"""
Authentication dependency for API endpoints
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.user import User
from app.api.v1.dependencies.database import get_db

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    # This is a placeholder implementation
    # In a real implementation, you would:
    # 1. Validate the JWT token
    # 2. Extract user info from token
    # 3. Get user from database
    
    # For now, return a mock user
    # Replace with actual JWT validation logic
    mock_user = User(
        id="mock-user-id",
        email="user@example.com",
        is_active=True
    )
    
    return mock_user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user