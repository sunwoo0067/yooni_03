"""
보안 관련 유틸리티
JWT 토큰 생성/검증, 비밀번호 해싱 등
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import secrets
import re

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User


# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=True
)

# JWT 설정
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES


class SecurityManager:
    """보안 관리 클래스"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        비밀번호 정책 검증
        - 최소 8자 이상
        - 대문자, 소문자, 숫자, 특수문자 포함
        """
        if len(password) < 8:
            return False, "비밀번호는 최소 8자 이상이어야 합니다"
        
        if not re.search(r"[A-Z]", password):
            return False, "비밀번호는 최소 1개의 대문자를 포함해야 합니다"
        
        if not re.search(r"[a-z]", password):
            return False, "비밀번호는 최소 1개의 소문자를 포함해야 합니다"
        
        if not re.search(r"\d", password):
            return False, "비밀번호는 최소 1개의 숫자를 포함해야 합니다"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "비밀번호는 최소 1개의 특수문자를 포함해야 합니다"
        
        return True, "OK"
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID for token revocation
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """리프레시 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """토큰 디코딩"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰을 검증할 수 없습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def generate_api_key() -> str:
        """API 키 생성"""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """웹훅 시크릿 생성"""
        return f"whsec_{secrets.token_urlsafe(32)}"


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """현재 인증된 사용자 가져오기"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = SecurityManager.decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
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
    current_user: User = Depends(get_current_user)
) -> User:
    """활성 사용자만 허용"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 사용자입니다"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """관리자만 허용"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 부족합니다"
        )
    return current_user


class RoleChecker:
    """역할 기반 접근 제어"""
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 부족합니다. 필요한 역할: {', '.join(self.allowed_roles)}"
            )
        return current_user


# 역할별 의존성
require_admin = RoleChecker(["admin", "superuser"])
require_seller = RoleChecker(["seller", "admin", "superuser"])
require_viewer = RoleChecker(["viewer", "seller", "admin", "superuser"])