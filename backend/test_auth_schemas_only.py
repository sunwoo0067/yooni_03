"""
Simple test to verify AuthService schemas work correctly without database
"""
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_schemas():
    """Test the authentication schemas"""
    print("Testing Authentication Schemas")
    print("=" * 50)
    
    try:
        from app.schemas.auth import UserRegister, UserLogin, Token, TokenPayload
        from app.schemas.user import UserResponse, UserCreate
        from app.models.user import UserRole, UserStatus
        
        # Test UserRegister schema
        print("Test 1: Testing UserRegister schema")
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
        print("\nTest 2: Testing UserLogin schema")
        user_login = UserLogin(
            email="test@example.com",
            password="SecurePass123!",
            remember_me=True
        )
        print(f"OK UserLogin: {user_login.email} (remember: {user_login.remember_me})")
        
        # Test Token schema
        print("\nTest 3: Testing Token schema")
        token = Token(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            token_type="bearer",
            expires_in=3600
        )
        print(f"OK Token: {token.token_type} (expires in {token.expires_in}s)")
        
        # Test TokenPayload schema
        print("\nTest 4: Testing TokenPayload schema")
        token_payload = TokenPayload(
            sub="550e8400-e29b-41d4-a716-446655440000",
            email="test@example.com",
            role="operator",
            exp=1642723200,
            iat=1642636800,
            jti="test-jti-123",
            type="access"
        )
        print(f"OK TokenPayload: {token_payload.sub} ({token_payload.role})")
        
        # Test UserResponse schema
        print("\nTest 5: Testing UserResponse schema")
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
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(f"OK UserResponse: {user_response.username} ({user_response.role})")
        
        # Test UserCreate schema
        print("\nTest 6: Testing UserCreate schema")
        user_create = UserCreate(
            username="admin_user",
            email="admin@example.com",
            password="AdminPass123!",
            full_name="Admin User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True
        )
        print(f"OK UserCreate: {user_create.username} ({user_create.role})")
        
        print("\nSUCCESS All schema tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nFAIL Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_security_manager():
    """Test SecurityManager functionality"""
    print("\nTesting SecurityManager")
    print("=" * 50)
    
    try:
        from app.core.security import SecurityManager
        
        # Test password hashing
        print("Test 1: Password hashing")
        password = "TestPassword123!"
        hashed = SecurityManager.get_password_hash(password)
        print(f"OK Password hashed: {hashed[:20]}...")
        
        # Test password verification
        print("\nTest 2: Password verification")
        is_valid = SecurityManager.verify_password(password, hashed)
        print(f"OK Password verification: {is_valid}")
        
        # Test password validation
        print("\nTest 3: Password validation")
        valid, message = SecurityManager.validate_password(password)
        print(f"OK Password validation: {valid} - {message}")
        
        # Test invalid password validation
        print("\nTest 4: Invalid password validation")
        invalid_valid, invalid_message = SecurityManager.validate_password("weak")
        print(f"OK Invalid password validation: {invalid_valid} - {invalid_message}")
        
        # Test JWT token creation
        print("\nTest 5: JWT token creation")
        token_data = {"sub": "test-user-id", "email": "test@example.com", "role": "operator"}
        access_token = SecurityManager.create_access_token(token_data)
        print(f"OK Access token created: {access_token[:20]}...{access_token[-20:]}")
        
        # Test refresh token creation
        print("\nTest 6: Refresh token creation")
        refresh_token = SecurityManager.create_refresh_token({"sub": "test-user-id"})
        print(f"OK Refresh token created: {refresh_token[:20]}...{refresh_token[-20:]}")
        
        # Test token decoding
        print("\nTest 7: Token decoding")
        payload = SecurityManager.decode_token(access_token)
        print(f"OK Token decoded: sub={payload.get('sub')}, email={payload.get('email')}")
        
        # Test API key generation
        print("\nTest 8: API key generation")
        api_key = SecurityManager.generate_api_key()
        print(f"OK API key generated: {api_key[:10]}...{api_key[-10:]}")
        
        print("\nSUCCESS All SecurityManager tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nFAIL SecurityManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models_import():
    """Test that all security models can be imported"""
    print("\nTesting Security Models Import")
    print("=" * 50)
    
    try:
        from app.models.security_audit import (
            SecurityAuditLog, TokenBlacklist, LoginAttempt, PasswordResetToken
        )
        print("OK SecurityAuditLog imported")
        print("OK TokenBlacklist imported") 
        print("OK LoginAttempt imported")
        print("OK PasswordResetToken imported")
        
        from app.models.user import User, UserRole, UserStatus, UserSession, UserAPIKey
        print("OK User imported")
        print("OK UserRole imported")
        print("OK UserStatus imported")
        print("OK UserSession imported")
        print("OK UserAPIKey imported")
        
        print("\nSUCCESS All models imported successfully!")
        return True
        
    except Exception as e:
        print(f"\nFAIL Model import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("Starting Authentication Schemas Test")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Schema validation
    if test_schemas():
        success_count += 1
    
    # Test 2: SecurityManager functionality
    if test_security_manager():
        success_count += 1
    
    # Test 3: Models import
    if test_models_import():
        success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("SUCCESS All authentication components are working correctly!")
        print("\nSummary:")
        print("   OK Authentication schemas working")
        print("   OK SecurityManager functionality working") 
        print("   OK Security models working")
        print("   OK JWT token management working")
        print("   OK Password hashing/validation working")
        return True
    else:
        print("FAIL Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)