"""
Authentication service for user management and security
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, text
from pydantic import EmailStr
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from app.core.security import SecurityManager
from app.core.config import settings
from app.models.user import User, UserRole, UserStatus, UserSession
from app.models.security_audit import (
    SecurityAuditLog, TokenBlacklist, LoginAttempt, PasswordResetToken
)
from app.schemas.auth import UserRegister, UserLogin
from app.schemas.user import UserCreate, UserResponse
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and user management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.security_manager = SecurityManager()
        
        # Rate limiting settings
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOGIN_LOCKOUT_MINUTES = 30
        self.MAX_PASSWORD_RESET_ATTEMPTS = 3
        self.PASSWORD_RESET_LOCKOUT_HOURS = 24
    
    # ==================
    # User Authentication
    # ==================
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with email and password
        Includes rate limiting and security logging
        """
        try:
            # Check rate limiting first
            if await self._is_rate_limited(email, ip_address):
                await self._log_security_event(
                    action="login_rate_limited",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": email, "reason": "too_many_attempts"}
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="너무 많은 로그인 시도가 있었습니다. 잠시 후 다시 시도해주세요."
                )
            
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            
            if not user:
                await self._record_login_attempt(
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason="user_not_found"
                )
                await self._log_security_event(
                    action="login_failure",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": email, "reason": "user_not_found"}
                )
                return None
            
            # Check if account is locked or suspended
            if user.status == UserStatus.SUSPENDED:
                await self._log_security_event(
                    action="login_suspended_account",
                    user_id=user.id,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": email}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="계정이 정지되었습니다. 관리자에게 문의하세요."
                )
            
            # Verify password
            if not self.security_manager.verify_password(password, user.hashed_password):
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account if too many failed attempts
                if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    user.status = UserStatus.SUSPENDED
                    await self._log_security_event(
                        action="account_locked",
                        user_id=user.id,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details={"email": email, "failed_attempts": user.failed_login_attempts}
                    )
                
                self.db.commit()
                
                await self._record_login_attempt(
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason="invalid_password",
                    user_id=user.id
                )
                
                await self._log_security_event(
                    action="login_failure",
                    user_id=user.id,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": email, "reason": "invalid_password"}
                )
                return None
            
            # Check if account is active
            if not user.is_active:
                await self._log_security_event(
                    action="login_inactive_account",
                    user_id=user.id,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": email}
                )
                return None
            
            # Successful authentication - reset failed attempts
            user.failed_login_attempts = 0
            user.last_login_at = datetime.utcnow()
            self.db.commit()
            
            await self._record_login_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                user_id=user.id
            )
            
            await self._log_security_event(
                action="login_success",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email}
            )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self._log_security_event(
                action="login_error",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="인증 처리 중 오류가 발생했습니다."
            )
    
    # ==================
    # User Registration
    # ==================
    
    async def create_user(
        self, 
        user_data: UserRegister,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserResponse:
        """Create new user account"""
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                or_(User.email == user_data.email, User.username == user_data.username)
            ).first()
            
            if existing_user:
                if existing_user.email == user_data.email:
                    error_msg = "이미 등록된 이메일입니다."
                else:
                    error_msg = "이미 사용 중인 사용자명입니다."
                
                await self._log_security_event(
                    action="registration_duplicate",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": user_data.email, "username": user_data.username}
                )
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Create new user
            user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=self.security_manager.get_password_hash(user_data.password),
                phone=user_data.phone,
                department=user_data.department,
                timezone=user_data.timezone,
                language=user_data.language,
                role=UserRole.OPERATOR,  # Default role
                status=UserStatus.PENDING,  # Require email verification
                is_active=True,
                is_verified=False
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            await self._log_security_event(
                action="registration_success",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": user_data.email, "username": user_data.username}
            )
            
            # Send welcome email (if email service is configured)
            try:
                await self._send_welcome_email(user)
            except Exception as e:
                logger.warning(f"Failed to send welcome email to {user.email}: {e}")
            
            return UserResponse.from_orm(user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation error: {e}")
            await self._log_security_event(
                action="registration_error",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": user_data.email, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 생성 중 오류가 발생했습니다."
            )
    
    # ==================
    # Session Management
    # ==================
    
    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> UserSession:
        """Create new user session"""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
                is_active=True
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            await self._log_security_event(
                action="session_created",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": str(session.id)}
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="세션 생성 중 오류가 발생했습니다."
            )
    
    async def get_active_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user"""
        return self.db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).order_by(desc(UserSession.created_at)).all()
    
    async def revoke_session(
        self,
        session_id: str,
        user_id: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """Revoke a specific session"""
        try:
            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            ).first()
            
            if not session:
                return False
            
            session.is_active = False
            self.db.commit()
            
            await self._log_security_event(
                action="session_revoked",
                user_id=user_id,
                success=True,
                ip_address=ip_address,
                details={"session_id": session_id}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Session revocation error: {e}")
            return False
    
    async def revoke_all_sessions(
        self,
        user_id: str,
        except_session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> int:
        """Revoke all sessions for a user (except optionally one)"""
        try:
            query = self.db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
            
            if except_session_id:
                query = query.filter(UserSession.id != except_session_id)
            
            sessions = query.all()
            count = len(sessions)
            
            for session in sessions:
                session.is_active = False
            
            self.db.commit()
            
            await self._log_security_event(
                action="all_sessions_revoked",
                user_id=user_id,
                success=True,
                ip_address=ip_address,
                details={"revoked_count": count, "except_session": except_session_id}
            )
            
            return count
            
        except Exception as e:
            logger.error(f"All sessions revocation error: {e}")
            return 0
    
    # ==================
    # Token Management
    # ==================
    
    async def revoke_token(
        self,
        token: str,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: str = "logout"
    ) -> bool:
        """Revoke (blacklist) a JWT token"""
        try:
            # Decode token to get JTI and expiration
            payload = SecurityManager.decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            token_type = payload.get("type", "access")
            
            if not jti or not exp:
                return False
            
            expires_at = datetime.fromtimestamp(exp)
            
            # Add to blacklist
            blacklisted_token = TokenBlacklist(
                jti=jti,
                token_type=token_type,
                user_id=user.id,
                expires_at=expires_at,
                revoke_reason=reason,
                revoke_ip=ip_address,
                revoke_user_agent=user_agent
            )
            
            self.db.add(blacklisted_token)
            self.db.commit()
            
            # Cache in Redis for fast lookup
            if cache_service:
                cache_key = f"blacklisted_token:{jti}"
                await cache_service.set(cache_key, "1", ttl=int((expires_at - datetime.utcnow()).total_seconds()))
            
            await self._log_security_event(
                action="token_revoked",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"jti": jti, "reason": reason, "token_type": token_type}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted"""
        try:
            # Check Redis cache first
            if cache_service:
                cache_key = f"blacklisted_token:{jti}"
                cached = await cache_service.get(cache_key)
                if cached:
                    return True
            
            # Check database
            blacklisted = self.db.query(TokenBlacklist).filter(
                and_(
                    TokenBlacklist.jti == jti,
                    TokenBlacklist.expires_at > datetime.utcnow()
                )
            ).first()
            
            return blacklisted is not None
            
        except Exception as e:
            logger.error(f"Token blacklist check error: {e}")
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired blacklisted tokens"""
        try:
            expired_tokens = self.db.query(TokenBlacklist).filter(
                TokenBlacklist.expires_at <= datetime.utcnow()
            ).all()
            
            count = len(expired_tokens)
            
            for token in expired_tokens:
                self.db.delete(token)
            
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired blacklisted tokens")
            return count
            
        except Exception as e:
            logger.error(f"Token cleanup error: {e}")
            return 0
    
    # ==================
    # Password Reset
    # ==================
    
    async def send_password_reset_email(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Send password reset email to user"""
        try:
            # Check rate limiting for password reset
            recent_resets = self.db.query(PasswordResetToken).filter(
                and_(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.created_at > datetime.utcnow() - timedelta(hours=1)
                )
            ).count()
            
            if recent_resets >= self.MAX_PASSWORD_RESET_ATTEMPTS:
                await self._log_security_event(
                    action="password_reset_rate_limited",
                    user_id=user.id,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"email": user.email}
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="비밀번호 재설정 요청이 너무 많습니다. 1시간 후 다시 시도해주세요."
                )
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Save reset token
            password_reset = PasswordResetToken(
                token=reset_token,
                user_id=user.id,
                expires_at=expires_at,
                request_ip=ip_address,
                request_user_agent=user_agent
            )
            
            self.db.add(password_reset)
            self.db.commit()
            
            # Send email
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            await self._send_password_reset_email(user, reset_url)
            
            await self._log_security_event(
                action="password_reset_requested",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": user.email}
            )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password reset email error: {e}")
            await self._log_security_event(
                action="password_reset_error",
                user_id=user.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": user.email, "error": str(e)}
            )
            return False
    
    async def verify_password_reset_token(self, token: str) -> Optional[User]:
        """Verify password reset token and return user"""
        try:
            reset_token = self.db.query(PasswordResetToken).filter(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not reset_token:
                return None
            
            user = self.db.query(User).filter(User.id == reset_token.user_id).first()
            return user
            
        except Exception as e:
            logger.error(f"Password reset token verification error: {e}")
            return None
    
    async def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Reset user password using reset token"""
        try:
            reset_token = self.db.query(PasswordResetToken).filter(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not reset_token:
                return False
            
            user = self.db.query(User).filter(User.id == reset_token.user_id).first()
            if not user:
                return False
            
            # Update password
            user.hashed_password = SecurityManager.get_password_hash(new_password)
            user.password_changed_at = datetime.utcnow()
            user.failed_login_attempts = 0  # Reset failed attempts
            
            # Mark token as used
            reset_token.mark_used(ip_address, user_agent)
            
            self.db.commit()
            
            # Revoke all existing sessions
            await self.revoke_all_sessions(user.id, ip_address=ip_address)
            
            await self._log_security_event(
                action="password_reset_completed",
                user_id=user.id,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": user.email}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return False
    
    # ==================
    # Security Monitoring
    # ==================
    
    async def record_successful_login(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Record successful login for monitoring"""
        await self._log_security_event(
            action="login_success",
            user_id=user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user.email}
        )
    
    async def record_failed_login(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Record failed login attempt"""
        await self._record_login_attempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="authentication_failed"
        )
    
    async def get_security_events(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityAuditLog]:
        """Get security audit events"""
        try:
            query = self.db.query(SecurityAuditLog)
            
            if user_id:
                query = query.filter(SecurityAuditLog.user_id == user_id)
            if action:
                query = query.filter(SecurityAuditLog.action == action)
            if ip_address:
                query = query.filter(SecurityAuditLog.ip_address == ip_address)
            
            return query.order_by(desc(SecurityAuditLog.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error fetching security events: {e}")
            return []
    
    # ==================
    # Private Helper Methods
    # ==================
    
    async def _is_rate_limited(self, email: str, ip_address: Optional[str] = None) -> bool:
        """Check if login attempts are rate limited"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.LOGIN_LOCKOUT_MINUTES)
            
            # Check by email
            email_attempts = self.db.query(LoginAttempt).filter(
                and_(
                    LoginAttempt.email == email,
                    LoginAttempt.success == False,
                    LoginAttempt.created_at > cutoff_time
                )
            ).count()
            
            if email_attempts >= self.MAX_LOGIN_ATTEMPTS:
                return True
            
            # Check by IP address
            if ip_address:
                ip_attempts = self.db.query(LoginAttempt).filter(
                    and_(
                        LoginAttempt.ip_address == ip_address,
                        LoginAttempt.success == False,
                        LoginAttempt.created_at > cutoff_time
                    )
                ).count()
                
                if ip_attempts >= self.MAX_LOGIN_ATTEMPTS * 2:  # Higher limit for IP
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rate limiting check error: {e}")
            return False
    
    async def _record_login_attempt(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = False,
        failure_reason: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Record login attempt"""
        try:
            attempt = LoginAttempt(
                email=email,
                ip_address=ip_address or "unknown",
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
                user_id=user_id
            )
            
            self.db.add(attempt)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Login attempt recording error: {e}")
    
    async def _log_security_event(
        self,
        action: str,
        success: bool,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource: Optional[str] = None
    ):
        """Log security event"""
        try:
            event = SecurityAuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                details=details
            )
            
            self.db.add(event)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Security event logging error: {e}")
    
    async def _send_welcome_email(self, user: User):
        """Send welcome email to new user"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping welcome email")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = user.email
            msg['Subject'] = f"{settings.PROJECT_NAME} 계정이 생성되었습니다"
            
            body = f"""
            안녕하세요 {user.full_name}님,
            
            {settings.PROJECT_NAME}에 오신 것을 환영합니다!
            
            계정 정보:
            - 사용자명: {user.username}
            - 이메일: {user.email}
            - 가입일: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            
            로그인하여 서비스를 이용해보세요.
            
            감사합니다.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.get_secret_value())
                server.send_message(msg)
            
            logger.info(f"Welcome email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            raise
    
    async def _send_password_reset_email(self, user: User, reset_url: str):
        """Send password reset email"""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping password reset email")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = user.email
            msg['Subject'] = f"{settings.PROJECT_NAME} 비밀번호 재설정"
            
            body = f"""
            안녕하세요 {user.full_name}님,
            
            비밀번호 재설정을 요청하셨습니다.
            
            아래 링크를 클릭하여 새 비밀번호를 설정해주세요:
            {reset_url}
            
            이 링크는 24시간 후에 만료됩니다.
            
            본인이 요청하지 않으셨다면 이 이메일을 무시하세요.
            
            감사합니다.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.get_secret_value())
                server.send_message(msg)
            
            logger.info(f"Password reset email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            raise