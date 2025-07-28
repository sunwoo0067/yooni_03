"""Authentication API endpoints
Login, logout, token refresh, password management, etc.
"""
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    HAS_SLOWAPI = True
except ImportError:
    # Fallback if slowapi is not available
    HAS_SLOWAPI = False
    class DummyLimiter:
        def limit(self, rate_limit):
            def decorator(func):
                return func
            return decorator
        def exception_handler(self, exc_type):
            def decorator(func):
                return func
            return decorator
    
    Limiter = DummyLimiter
    def get_remote_address(request):
        return request.client.host if request.client else "unknown"
    
    class RateLimitExceeded(Exception):
        pass

from app.core import security
from app.api.v1.dependencies.database import get_db
from app.core.security import SecurityManager
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    Token, TokenPayload, UserLogin, UserRegister, LoginResponse,
    PasswordChange, PasswordResetRequest, PasswordReset,
    RefreshTokenRequest, MessageResponse, SuccessResponse
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize limiter based on availability
if HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
    
    # Add rate limit handler
    @router.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded: {exc.detail}"}
        )
        response = request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )
        return response
else:
    limiter = Limiter()


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client IP and user agent from request"""
    # Get real IP address from headers (for proxy/load balancer scenarios)
    ip_address = (
        request.headers.get("x-forwarded-for", "")
        or request.headers.get("x-real-ip", "")
        or request.client.host if request.client else None
    )
    
    # Handle comma-separated IPs in x-forwarded-for
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    user_agent = request.headers.get("user-agent")
    
    return ip_address, user_agent


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request,
    user_in: UserRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 등록
    - 이메일/사용자명 중복 확인
    - 비밀번호 정책 검증
    - 이메일 인증 링크 발송
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Validate password policy
        is_valid, message = SecurityManager.validate_password(user_in.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Create user through AuthService (handles all validation and logging)
        user = await auth_service.create_user(
            user_data=user_in,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"User registered successfully: {user_in.email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 등록 중 오류가 발생했습니다."
        )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 인증 및 토큰 발급
    - OAuth2 호환 (username = email)
    - 자동 브루트포스 방지
    - 세션 생성 및 추적
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Authenticate user (includes rate limiting and security logging)
        user = await auth_service.authenticate_user(
            email=form_data.username,  # OAuth2 standard uses username field for email
            password=form_data.password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Generate tokens
        access_token = SecurityManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = SecurityManager.create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        # Create session for tracking
        session = await auth_service.create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": security.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    리프레시 토큰으로 새 액세스 토큰 발급
    - 토큰 블랙리스트 확인
    - 사용자 상태 검증
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        refresh_token = token_request.refresh_token
        
        # Decode and validate refresh token
        payload = SecurityManager.decode_token(refresh_token)
        token_type = payload.get("type")
        jti = payload.get("jti")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰 타입입니다"
            )
        
        # Check if token is blacklisted
        if jti and await auth_service.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="무효화된 토큰입니다"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # Generate new access token
        access_token = SecurityManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        
        # Log token refresh
        await auth_service._log_security_event(
            action="token_refreshed",
            user_id=user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user.email}
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Keep existing refresh token
            "token_type": "bearer",
            "expires_in": security.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰을 갱신할 수 없습니다"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(security.oauth2_scheme),
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 로그아웃
    - 토큰 블랙리스트 추가
    - 활성 세션 종료
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Revoke current token
        success = await auth_service.revoke_token(
            token=token,
            user=current_user,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="logout"
        )
        
        if not success:
            logger.warning(f"Failed to revoke token for user: {current_user.email}")
        
        # Log successful logout
        await auth_service._log_security_event(
            action="logout",
            user_id=current_user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": current_user.email}
        )
        
        logger.info(f"User logged out successfully: {current_user.email}")
        
        return MessageResponse(message="로그아웃되었습니다")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if logging fails, return success for UX
        return MessageResponse(message="로그아웃되었습니다")


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    현재 인증된 사용자 정보 조회
    - 토큰에서 추출한 사용자 정보 반환
    - 자동으로 최신 사용자 상태 반영
    """
    return UserResponse.from_orm(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    비밀번호 변경
    - 현재 비밀번호 확인
    - 새 비밀번호 정책 검증
    - 모든 세션 무효화
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Verify current password
        if not SecurityManager.verify_password(
            password_data.current_password, 
            current_user.hashed_password
        ):
            await auth_service._log_security_event(
                action="password_change_failed",
                user_id=current_user.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": current_user.email, "reason": "wrong_current_password"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 올바르지 않습니다"
            )
        
        # Validate new password policy
        is_valid, message = SecurityManager.validate_password(password_data.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Update password
        current_user.hashed_password = SecurityManager.get_password_hash(password_data.new_password)
        current_user.password_changed_at = datetime.utcnow()
        db.commit()
        
        # Revoke all user sessions except current one
        revoked_count = await auth_service.revoke_all_sessions(
            user_id=current_user.id,
            ip_address=ip_address
        )
        
        # Log successful password change
        await auth_service._log_security_event(
            action="password_changed",
            user_id=current_user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "email": current_user.email,
                "sessions_revoked": revoked_count
            }
        )
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return MessageResponse(message="비밀번호가 변경되었습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다."
        )


@router.post("/request-password-reset", response_model=MessageResponse)
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    비밀번호 재설정 요청
    - 이메일로 재설정 링크 발송
    - 사용자 존재 여부와 관계없이 동일한 응답 (보안)
    - 요청 빈도 제한 (브루트포스 방지)
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Find user (but don't reveal if user exists)
        user = db.query(User).filter(User.email == reset_request.email).first()
        
        if user:
            # Send reset email (includes rate limiting)
            await auth_service.send_password_reset_email(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
        else:
            # Log attempt even if user doesn't exist
            await auth_service._log_security_event(
                action="password_reset_requested_nonexistent",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": reset_request.email}
            )
        
        # Always return same message for security
        return MessageResponse(
            message="비밀번호 재설정 링크가 이메일로 발송되었습니다 (등록된 이메일인 경우)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Return generic success message even on error
        return MessageResponse(
            message="비밀번호 재설정 링크가 이메일로 발송되었습니다 (등록된 이메일인 경우)"
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: Request,
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
) -> Any:
    """
    비밀번호 재설정 완료
    - 재설정 토큰 검증
    - 새 비밀번호 정책 검증
    - 모든 세션 무효화
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        # Validate new password policy first
        is_valid, message = SecurityManager.validate_password(reset_data.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Reset password using AuthService (handles token validation and logging)
        success = await auth_service.reset_password(
            token=reset_data.token,
            new_password=reset_data.new_password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않거나 만료된 토큰입니다"
            )
        
        logger.info("Password reset completed successfully")
        
        return MessageResponse(message="비밀번호가 재설정되었습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 중 오류가 발생했습니다."
        )


@router.get("/sessions", response_model=list)
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    현재 사용자의 활성 세션 목록 조회
    - 모든 활성 세션 정보 반환
    - IP 주소, 디바이스 정보 포함
    """
    try:
        auth_service = AuthService(db)
        sessions = await auth_service.get_active_sessions(current_user.id)
        
        return [
            {
                "id": session.id,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "country": getattr(session, 'country', None),
                "city": getattr(session, 'city', None)
            }
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 정보를 조회할 수 없습니다."
        )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    특정 세션 무효화
    - 지정된 세션 ID의 세션 종료
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        success = await auth_service.revoke_session(
            session_id=session_id,
            user_id=current_user.id,
            ip_address=ip_address
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        logger.info(f"Session {session_id} revoked for user: {current_user.email}")
        
        return MessageResponse(message="세션이 종료되었습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 종료 중 오류가 발생했습니다."
        )


@router.delete("/sessions", response_model=MessageResponse)
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    모든 세션 무효화 (현재 세션 제외)
    - 모든 디바이스에서 로그아웃
    - 보안 감사 로그 기록
    """
    ip_address, user_agent = get_client_info(request)
    
    try:
        auth_service = AuthService(db)
        
        revoked_count = await auth_service.revoke_all_sessions(
            user_id=current_user.id,
            ip_address=ip_address
        )
        
        logger.info(f"{revoked_count} sessions revoked for user: {current_user.email}")
        
        return MessageResponse(
            message=f"{revoked_count}개의 세션이 종료되었습니다"
        )
        
    except Exception as e:
        logger.error(f"All sessions revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 종료 중 오류가 발생했습니다."
        )


@router.get("/security-events", response_model=list)
async def get_security_events(
    current_user: User = Depends(get_current_user),
    action: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> Any:
    """
    사용자 보안 이벤트 조회
    - 로그인/로그아웃 기록
    - 비밀번호 변경 기록
    - 기타 보안 관련 활동
    """
    try:
        auth_service = AuthService(db)
        
        events = await auth_service.get_security_events(
            user_id=current_user.id,
            action=action,
            limit=min(limit, 100)  # Maximum 100 events
        )
        
        return [
            {
                "id": event.id,
                "action": event.action,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "success": event.success,
                "details": event.details,
                "created_at": event.created_at
            }
            for event in events
        ]
        
    except Exception as e:
        logger.error(f"Error fetching security events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="보안 이벤트를 조회할 수 없습니다."
        )