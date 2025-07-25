"""
인증 관련 API 엔드포인트
로그인, 로그아웃, 토큰 갱신 등
"""
from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from ....core import security
from ....core.database import get_db
from ....core.security import SecurityManager, get_current_user
from ....models.user import User
from ....schemas.auth import Token, TokenPayload, UserLogin, UserRegister
from ....schemas.user import UserResponse
from ....services.auth import AuthService
from ....utils.validators import validate_email

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserRegister
) -> Any:
    """
    새 사용자 등록
    - 이메일 중복 확인
    - 비밀번호 정책 검증
    - 환영 이메일 발송
    """
    # 이메일 검증
    if not validate_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 이메일 형식입니다"
        )
    
    # 비밀번호 정책 검증
    is_valid, message = SecurityManager.validate_password(user_in.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 이메일 중복 확인
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다"
        )
    
    # 사용자 생성
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_in)
    
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 호환 토큰 로그인
    - username은 이메일로 사용
    - 실패 시 로그인 시도 횟수 기록
    """
    auth_service = AuthService(db)
    
    # 사용자 인증
    user = await auth_service.authenticate_user(
        email=form_data.username,  # OAuth2 표준에 따라 username 필드 사용
        password=form_data.password
    )
    
    if not user:
        # 로그인 실패 기록
        await auth_service.record_failed_login(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    # 토큰 생성
    access_token = SecurityManager.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    refresh_token = SecurityManager.create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    # 로그인 성공 기록
    await auth_service.record_successful_login(user)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": security.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    *,
    db: Session = Depends(get_db),
    refresh_token: str = Body(..., embed=True)
) -> Any:
    """
    리프레시 토큰으로 새 액세스 토큰 발급
    """
    try:
        payload = SecurityManager.decode_token(refresh_token)
        token_type = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰 타입입니다"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        
        # 사용자 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 새 토큰 생성
        access_token = SecurityManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # 기존 리프레시 토큰 유지
            "token_type": "bearer",
            "expires_in": security.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰을 갱신할 수 없습니다"
        )


@router.post("/logout")
async def logout(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(security.oauth2_scheme)
) -> Any:
    """
    로그아웃
    - 토큰을 블랙리스트에 추가
    - 세션 종료 기록
    """
    auth_service = AuthService(db)
    
    # 토큰 무효화
    await auth_service.revoke_token(token, current_user)
    
    return {"message": "로그아웃되었습니다"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    현재 로그인한 사용자 정보 조회
    """
    return current_user


@router.post("/change-password")
async def change_password(
    *,
    db: Session = Depends(get_db),
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    비밀번호 변경
    """
    # 현재 비밀번호 확인
    if not SecurityManager.verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다"
        )
    
    # 새 비밀번호 정책 검증
    is_valid, message = SecurityManager.validate_password(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 비밀번호 업데이트
    current_user.hashed_password = SecurityManager.get_password_hash(new_password)
    current_user.password_changed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "비밀번호가 변경되었습니다"}


@router.post("/request-password-reset")
@limiter.limit("3/hour")
async def request_password_reset(
    *,
    db: Session = Depends(get_db),
    email: str = Body(..., embed=True)
) -> Any:
    """
    비밀번호 재설정 요청
    - 이메일로 재설정 링크 발송
    """
    auth_service = AuthService(db)
    
    # 사용자 확인 (존재하지 않아도 동일한 응답)
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        await auth_service.send_password_reset_email(user)
    
    return {
        "message": "비밀번호 재설정 링크가 이메일로 발송되었습니다"
    }


@router.post("/reset-password")
async def reset_password(
    *,
    db: Session = Depends(get_db),
    token: str = Body(...),
    new_password: str = Body(...)
) -> Any:
    """
    비밀번호 재설정
    """
    auth_service = AuthService(db)
    
    # 토큰 검증 및 사용자 확인
    user = await auth_service.verify_password_reset_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 토큰입니다"
        )
    
    # 새 비밀번호 정책 검증
    is_valid, message = SecurityManager.validate_password(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 비밀번호 업데이트
    user.hashed_password = SecurityManager.get_password_hash(new_password)
    user.password_changed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "비밀번호가 재설정되었습니다"}