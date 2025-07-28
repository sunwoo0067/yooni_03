"""
Authentication dependency for API endpoints
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.models.user import User
from app.models.security_audit import TokenBlacklist
from app.api.v1.dependencies.database import get_db
from app.core.security import SecurityManager
from app.services.cache_service import cache_service
from datetime import datetime
from sqlalchemy import and_

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    try:
        # JWT 토큰 검증 및 디코딩
        payload = SecurityManager.decode_token(token)
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        
        if user_id is None or jti is None:
            raise credentials_exception
        
        # Check if token is blacklisted
        if await _is_token_blacklisted(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 무효화되었습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError:
        raise credentials_exception
    
    # 데이터베이스에서 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 사용자입니다"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_user_ws(
    token: str,
    db: Session
) -> Optional[User]:
    """Get current user for WebSocket connection"""
    try:
        # JWT 토큰 검증 및 디코딩
        payload = SecurityManager.decode_token(token)
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        
        if user_id is None or jti is None:
            return None
        
        # Check if token is blacklisted
        if await _is_token_blacklisted(jti, db):
            return None
            
        # 데이터베이스에서 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None or not user.is_active:
            return None
            
        return user
        
    except JWTError:
        return None


async def _is_token_blacklisted(jti: str, db: Session) -> bool:
    """Check if a token is blacklisted"""
    try:
        # Check Redis cache first
        if cache_service and cache_service.redis_client:
            cache_key = f"blacklisted_token:{jti}"
            cached = await cache_service.get(cache_key)
            if cached:
                return True
        
        # Check database
        blacklisted = db.query(TokenBlacklist).filter(
            and_(
                TokenBlacklist.jti == jti,
                TokenBlacklist.expires_at > datetime.utcnow()
            )
        ).first()
        
        return blacklisted is not None
        
    except Exception:
        # If cache/db check fails, err on the side of caution but don't block
        return False