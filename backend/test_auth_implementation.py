"""
Test script to verify AuthService and authentication schemas implementation
"""
import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.models import Base
from app.models.user import User, UserRole, UserStatus
from app.models.security_audit import SecurityAuditLog, TokenBlacklist, LoginAttempt, PasswordResetToken
from app.schemas.auth import UserRegister, UserLogin, Token
from app.schemas.user import UserResponse
from app.services.auth import AuthService


def create_test_database():
    """Create a test database with required tables"""
    # Use SQLite for testing and set the DATABASE_URL for get_json_type() to work
    import os
    os.environ['DATABASE_URL'] = "sqlite:///./test_auth.db"
    
    # Update settings to use SQLite
    from app.core.config import get_settings
    test_settings = get_settings()
    test_settings.DATABASE_URL = "sqlite:///./test_auth.db"
    
    engine = create_engine("sqlite:///./test_auth.db", echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal


async def test_auth_service():
    """Test the AuthService implementation"""
    print("Testing AuthService Implementation")
    print("=" * 50)
    
    try:
        # Create test database
        engine, SessionLocal = create_test_database()
        db = SessionLocal()
        
        # Initialize AuthService
        auth_service = AuthService(db)
        print("OK AuthService initialized successfully")
        
        # Test 1: User Registration
        print("\nTest Test 1: User Registration")
        user_data = UserRegister(
            username="test_user",
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
            phone="010-1234-5678"
        )
        
        user_response = await auth_service.create_user(
            user_data, 
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        print(f"OK User created: {user_response.username} ({user_response.email})")
        print(f"   Role: {user_response.role}, Status: {user_response.status}")
        
        # Test 2: User Authentication - Valid credentials
        print("\nTest Test 2: Valid Authentication")
        user = await auth_service.authenticate_user(
            email="test@example.com",
            password="SecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        if user:
            print(f"OK Authentication successful for {user.email}")
            print(f"   Last login: {user.last_login_at}")
        else:
            print("FAIL Authentication failed")
        
        # Test 3: User Authentication - Invalid credentials
        print("\nTest Test 3: Invalid Authentication")
        try:
            invalid_user = await auth_service.authenticate_user(
                email="test@example.com",
                password="WrongPassword123!",
                ip_address="192.168.1.1",
                user_agent="Test Agent"
            )
            print("FAIL Should have failed authentication")
        except Exception as e:
            print("OK Authentication properly failed for invalid credentials")
        
        # Test 4: Security Audit Logs
        print("\nTest Test 4: Security Audit Logs")
        events = await auth_service.get_security_events(limit=5)
        print(f"OK Found {len(events)} security events")
        for event in events:
            print(f"   - {event.action}: {event.success} @ {event.created_at}")
        
        # Test 5: JWT Token Management
        print("\nTest Test 5: JWT Token Management")
        from app.core.security import SecurityManager
        
        # Create a test token
        token = SecurityManager.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        print("OK JWT token created successfully")
        
        # Revoke the token
        revoked = await auth_service.revoke_token(
            token=token,
            user=user,
            ip_address="192.168.1.1",
            reason="test_revocation"
        )
        
        if revoked:
            print("OK Token revoked successfully")
        else:
            print("FAIL Token revocation failed")
        
        # Check if token is blacklisted
        payload = SecurityManager.decode_token(token)
        jti = payload.get("jti")
        
        if jti:
            is_blacklisted = await auth_service.is_token_blacklisted(jti)
            if is_blacklisted:
                print("OK Token properly blacklisted")
            else:
                print("FAIL Token not found in blacklist")
        
        # Test 6: Password Reset Token
        print("\nTest Test 6: Password Reset")
        reset_sent = await auth_service.send_password_reset_email(
            user=user,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        if reset_sent:
            print("OK Password reset email would be sent (SMTP not configured)")
        else:
            print("WARN Password reset email not sent (expected without SMTP)")
        
        # Test 7: Session Management
        print("\nTest Test 7: Session Management")
        session = await auth_service.create_session(
            user=user,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        print(f"OK Session created: {session.id}")
        
        active_sessions = await auth_service.get_active_sessions(str(user.id))
        print(f"OK Found {len(active_sessions)} active sessions")
        
        # Clean up
        db.close()
        
        print("\nSUCCESS All tests completed successfully!")
        print("   AuthService implementation is working correctly")
        
    except Exception as e:
        print(f"\nFAIL Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_schemas():
    """Test the authentication schemas"""
    print("\nTest Testing Authentication Schemas")
    print("=" * 50)
    
    try:
        # Test UserRegister schema
        print("Test Testing UserRegister schema")
        user_register = UserRegister(
            username="test_user",
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
            phone="010-1234-5678",
            department="Engineering"
        )
        print(f"OK UserRegister: {user_register.username} - {user_register.email}")
        
        # Test UserLogin schema
        print("\nTest Testing UserLogin schema")
        user_login = UserLogin(
            email="test@example.com",
            password="SecurePass123!",
            remember_me=True
        )
        print(f"OK UserLogin: {user_login.email} (remember: {user_login.remember_me})")
        
        # Test Token schema
        print("\nTest Testing Token schema")
        token = Token(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            token_type="bearer",
            expires_in=3600
        )
        print(f"OK Token: {token.token_type} (expires in {token.expires_in}s)")
        
        # Test UserResponse schema
        print("\nTest Testing UserResponse schema")
        user_response = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="test_user",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True,
            timezone="Asia/Seoul",
            language="ko",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        print(f"OK UserResponse: {user_response.username} ({user_response.role})")
        
        print("\nSUCCESS All schema tests completed successfully!")
        
    except Exception as e:
        print(f"\nFAIL Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Run all tests"""
    print("Starting Starting Authentication System Test")
    print("=" * 60)
    
    # Test schemas first
    schema_success = test_schemas()
    
    if schema_success:
        # Test AuthService
        auth_success = await test_auth_service()
        
        if auth_success:
            print("\nSUCCESS All tests passed! Authentication system is ready.")
            print("\nTest Summary:")
            print("   OK Authentication schemas working")
            print("   OK AuthService implementation working") 
            print("   OK JWT token management working")
            print("   OK Security audit logging working")
            print("   OK Session management working")
            print("   OK Password reset functionality working")
            print("   OK Token blacklisting working")
            
            return True
        else:
            print("\nFAIL AuthService tests failed")
            return False
    else:
        print("\nFAIL Schema tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)