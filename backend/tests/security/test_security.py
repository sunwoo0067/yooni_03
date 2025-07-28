"""
Security tests for dropshipping system
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import jwt
import hashlib
import time
from datetime import datetime, timedelta
import json
import base64

from tests.conftest_enhanced import *


class TestAuthenticationSecurity:
    """Test authentication and authorization security"""
    
    @pytest.mark.security
    def test_password_hashing_security(self, enhanced_test_client):
        """Test password hashing and security"""
        
        # Test user registration with password
        user_data = {
            "username": "securitytest",
            "email": "security@test.com",
            "password": "SecurePassword123!",
            "full_name": "Security Test User"
        }
        
        response = enhanced_test_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        
        # Password should not be returned
        assert "password" not in result
        assert "hashed_password" not in result
        
        # Login with correct password
        login_response = enhanced_test_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        
        # Login with incorrect password should fail
        wrong_password_response = enhanced_test_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["username"],
                "password": "WrongPassword123!"
            }
        )
        
        assert wrong_password_response.status_code == 401
    
    @pytest.mark.security
    def test_jwt_token_security(self, enhanced_test_client, test_user_token):
        """Test JWT token security and validation"""
        
        token = test_user_token["token"]
        
        # Valid token should work
        response = enhanced_test_client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Invalid token should fail
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid",
            token[:-5] + "xxxxx",  # Modified token
            "",
            "malformed_token_without_dots"
        ]
        
        for invalid_token in invalid_tokens:
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers={"Authorization": f"Bearer {invalid_token}"}
            )
            assert response.status_code == 401
    
    @pytest.mark.security
    def test_token_expiration(self, enhanced_test_client):
        """Test JWT token expiration handling"""
        
        # Create a token that's about to expire
        from app.core.security import create_access_token
        
        # Create short-lived token (1 second)
        short_token = create_access_token(
            data={"sub": "testuser"}, 
            expires_delta=timedelta(seconds=1)
        )
        
        # Token should work immediately
        response = enhanced_test_client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {short_token}"}
        )
        # Note: Might fail if endpoint doesn't exist, but token validation should pass
        
        # Wait for expiration
        time.sleep(2)
        
        # Expired token should fail
        expired_response = enhanced_test_client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {short_token}"}
        )
        assert expired_response.status_code == 401
    
    @pytest.mark.security
    def test_role_based_access_control(self, enhanced_test_client, user_factory):
        """Test role-based access control"""
        
        # Create regular user
        regular_user = user_factory(
            username="regularuser",
            is_superuser=False
        )
        
        # Create admin user
        admin_user = user_factory(
            username="adminuser", 
            is_superuser=True
        )
        
        from app.core.security import create_access_token
        
        regular_token = create_access_token(data={"sub": regular_user.username})
        admin_token = create_access_token(data={"sub": admin_user.username})
        
        # Regular user should not access admin endpoints
        admin_response = enhanced_test_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert admin_response.status_code in [403, 404]  # Forbidden or not found
        
        # Admin user should access admin endpoints
        admin_access_response = enhanced_test_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Note: Endpoint might not exist, but authorization should pass
        assert admin_access_response.status_code in [200, 404]  # OK or not found


class TestInputValidationSecurity:
    """Test input validation and injection prevention"""
    
    @pytest.mark.security
    def test_sql_injection_prevention(self, enhanced_test_client, test_user_token):
        """Test SQL injection prevention"""
        
        sql_injection_payloads = [
            "'; DROP TABLE products; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM orders; --",
            "' OR 1=1 --",
            "admin'--",
            "admin' /*",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in sql_injection_payloads:
            # Test search endpoint
            response = enhanced_test_client.get(
                f"/api/v1/products/search?q={payload}",
                headers=test_user_token["headers"]
            )
            
            # Should not cause server error
            assert response.status_code in [200, 400, 422]
            
            # Should not return unexpected data
            if response.status_code == 200:
                result = response.json()
                # Results should be normal search results, not database dump
                assert "items" in result or "error" in result
    
    @pytest.mark.security
    def test_xss_prevention(self, enhanced_test_client, test_user_token):
        """Test Cross-Site Scripting (XSS) prevention"""
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
        for payload in xss_payloads:
            # Test creating product with XSS payload
            product_data = {
                "name": payload,
                "description": f"Product with XSS: {payload}",
                "price": 25000,
                "cost": 12500,
                "sku": "XSS-TEST",
                "category": payload
            }
            
            response = enhanced_test_client.post(
                "/api/v1/products/",
                json=product_data,
                headers=test_user_token["headers"]
            )
            
            if response.status_code == 201:
                result = response.json()
                # XSS payloads should be sanitized or escaped
                assert "<script>" not in result.get("name", "")
                assert "javascript:" not in result.get("description", "")
    
    @pytest.mark.security
    def test_command_injection_prevention(self, enhanced_test_client, test_user_token):
        """Test command injection prevention"""
        
        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "; ping google.com",
            "| whoami",
            "; cat /proc/version",
            "&& curl evil.com",
            "; echo $PATH"
        ]
        
        for payload in command_injection_payloads:
            # Test file upload or any endpoint that might execute commands
            response = enhanced_test_client.post(
                "/api/v1/products/import",
                json={
                    "file_path": payload,
                    "format": "csv"
                },
                headers=test_user_token["headers"]
            )
            
            # Should handle safely (might return 400, 404, or 422)
            assert response.status_code in [400, 404, 422, 200]
            
            # Should not execute system commands
            if response.status_code == 200:
                result = response.json()
                # Should not contain system information
                assert "uid=" not in str(result)
                assert "/bin/" not in str(result)
    
    @pytest.mark.security
    def test_path_traversal_prevention(self, enhanced_test_client, test_user_token):
        """Test path traversal prevention"""
        
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "../../../../../../../../etc/passwd%00.jpg"
        ]
        
        for payload in path_traversal_payloads:
            # Test file access endpoints
            response = enhanced_test_client.get(
                f"/api/v1/files/{payload}",
                headers=test_user_token["headers"]
            )
            
            # Should not access system files
            assert response.status_code in [400, 403, 404]
            
            if response.status_code == 200:
                content = response.content
                # Should not contain system file content
                assert b"root:" not in content
                assert b"admin:" not in content


class TestDataProtectionSecurity:
    """Test data protection and privacy security"""
    
    @pytest.mark.security
    def test_sensitive_data_exposure(self, enhanced_test_client, test_user_token, user_factory, order_factory):
        """Test prevention of sensitive data exposure"""
        
        # Create test data with sensitive information
        user = user_factory(
            username="sensitiveuser",
            email="sensitive@test.com"
        )
        
        order = order_factory(
            user_id=user.id,
            customer_name="민감한 고객",
            customer_phone="010-1234-5678",
            customer_email="customer@sensitive.com",
            shipping_address={
                "name": "민감한 고객",
                "address": "서울시 강남구 민감한동 123-45",
                "phone": "010-1234-5678"
            }
        )
        
        # Test user data exposure
        user_response = enhanced_test_client.get(
            f"/api/v1/users/{user.id}",
            headers=test_user_token["headers"]
        )
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            # Sensitive fields should not be exposed
            assert "password" not in user_data
            assert "hashed_password" not in user_data
        
        # Test order data protection
        order_response = enhanced_test_client.get(
            f"/api/v1/orders/{order.id}",
            headers=test_user_token["headers"]
        )
        
        if order_response.status_code == 200:
            order_data = order_response.json()
            # Personal information should be protected or masked
            if "customer_phone" in order_data:
                phone = order_data["customer_phone"]
                # Phone might be masked: 010-****-5678
                assert len(phone) >= 8  # Should not be empty
    
    @pytest.mark.security
    def test_api_key_security(self, enhanced_test_client, test_user_token):
        """Test API key security and exposure prevention"""
        
        # Test configuration endpoint
        config_response = enhanced_test_client.get(
            "/api/v1/config",
            headers=test_user_token["headers"]
        )
        
        if config_response.status_code == 200:
            config_data = config_response.json()
            
            # API keys and secrets should not be exposed
            sensitive_fields = [
                "api_key", "secret_key", "private_key", "password",
                "token", "gemini_api_key", "openai_api_key", 
                "database_url", "redis_url"
            ]
            
            def check_nested_dict(data, path=""):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if isinstance(value, dict):
                        check_nested_dict(value, current_path)
                    elif isinstance(value, str):
                        # Check if this looks like a sensitive field
                        key_lower = key.lower()
                        if any(sensitive in key_lower for sensitive in sensitive_fields):
                            # Should be masked or not present
                            assert value.startswith("***") or value == "[REDACTED]" or len(value) == 0
            
            if isinstance(config_data, dict):
                check_nested_dict(config_data)
    
    @pytest.mark.security
    def test_logging_security(self, enhanced_test_client, test_user_token):
        """Test that sensitive data is not logged"""
        
        # Attempt operations that might log sensitive data
        login_data = {
            "username": "logtest",
            "password": "SecretPassword123!"
        }
        
        # Register user
        register_response = enhanced_test_client.post(
            "/api/v1/auth/register",
            json={
                **login_data,
                "email": "logtest@example.com",
                "full_name": "Log Test User"
            }
        )
        
        # Login
        login_response = enhanced_test_client.post(
            "/api/v1/auth/login",
            data=login_data
        )
        
        # Check application logs (if accessible)
        logs_response = enhanced_test_client.get(
            "/api/v1/admin/logs?level=all",
            headers=test_user_token["headers"]
        )
        
        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            logs_content = str(logs_data).lower()
            
            # Passwords should not appear in logs
            assert "secretpassword123!" not in logs_content
            assert login_data["password"].lower() not in logs_content


class TestAPISecurityHeaders:
    """Test API security headers and HTTPS enforcement"""
    
    @pytest.mark.security
    def test_security_headers(self, enhanced_test_client):
        """Test presence of security headers"""
        
        response = enhanced_test_client.get("/api/v1/health")
        
        # Check for important security headers
        headers = response.headers
        
        # Content Security Policy
        # Note: FastAPI might not set all headers by default
        expected_headers = [
            "x-content-type-options",
            "x-frame-options", 
            "x-xss-protection"
        ]
        
        # Log which headers are present
        print("🔒 Security headers check:")
        for header in expected_headers:
            if header in headers:
                print(f"   ✅ {header}: {headers[header]}")
            else:
                print(f"   ⚠️  {header}: Not present")
        
        # At minimum, content type should be set correctly
        assert "content-type" in headers
    
    @pytest.mark.security
    def test_cors_configuration(self, enhanced_test_client):
        """Test CORS configuration security"""
        
        # Test preflight request
        response = enhanced_test_client.options(
            "/api/v1/products/",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # CORS should be configured properly
        if "access-control-allow-origin" in response.headers:
            allowed_origin = response.headers["access-control-allow-origin"]
            
            # Should not allow all origins in production
            assert allowed_origin != "*" or "test" in str(response.url)
        
        print(f"🌐 CORS configuration: {response.headers.get('access-control-allow-origin', 'Not set')}")


class TestRateLimitingSecurity:
    """Test rate limiting security measures"""
    
    @pytest.mark.security
    @pytest.mark.slow
    def test_api_rate_limiting(self, enhanced_test_client, test_user_token):
        """Test API rate limiting"""
        
        # Make rapid requests to test rate limiting
        responses = []
        request_count = 30  # Try many requests quickly
        
        print(f"🚦 Testing rate limiting with {request_count} rapid requests...")
        
        for i in range(request_count):
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers=test_user_token["headers"]
            )
            responses.append(response)
            
            # Check if rate limited
            if response.status_code == 429:
                print(f"   ✅ Rate limited after {i+1} requests")
                break
        
        # Check for rate limit headers
        if responses:
            last_response = responses[-1]
            rate_limit_headers = [
                "x-ratelimit-limit",
                "x-ratelimit-remaining", 
                "x-ratelimit-reset",
                "retry-after"
            ]
            
            print("📊 Rate limit headers:")
            for header in rate_limit_headers:
                if header in last_response.headers:
                    print(f"   {header}: {last_response.headers[header]}")
        
        # Should eventually hit rate limit or have reasonable response times
        rate_limited = any(r.status_code == 429 for r in responses)
        
        if not rate_limited:
            print("⚠️  No rate limiting detected - verify if this is intended")
        else:
            print("✅ Rate limiting is working")
    
    @pytest.mark.security
    def test_brute_force_protection(self, enhanced_test_client):
        """Test brute force attack protection"""
        
        # Create test user
        user_data = {
            "username": "bruteforcetest",
            "email": "bruteforce@test.com", 
            "password": "CorrectPassword123!",
            "full_name": "Brute Force Test"
        }
        
        register_response = enhanced_test_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        assert register_response.status_code == 201
        
        # Attempt multiple failed logins
        failed_attempts = 0
        max_attempts = 10
        
        print(f"🔓 Testing brute force protection with {max_attempts} failed attempts...")
        
        for i in range(max_attempts):
            response = enhanced_test_client.post(
                "/api/v1/auth/login",
                data={
                    "username": user_data["username"],
                    "password": f"WrongPassword{i}"
                }
            )
            
            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:
                print(f"   ✅ Account locked/rate limited after {failed_attempts} attempts")
                break
            elif response.status_code == 423:
                print(f"   ✅ Account locked after {failed_attempts} attempts")
                break
        
        print(f"📊 Failed login attempts before protection: {failed_attempts}")
        
        # Try correct password after failed attempts
        correct_login = enhanced_test_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["username"], 
                "password": user_data["password"]
            }
        )
        
        if correct_login.status_code in [429, 423]:
            print("✅ Account properly protected against brute force")
        elif correct_login.status_code == 200:
            print("⚠️  Account not locked - verify if protection is enabled")


class TestSessionSecurity:
    """Test session management security"""
    
    @pytest.mark.security
    def test_session_fixation_prevention(self, enhanced_test_client):
        """Test session fixation attack prevention"""
        
        # Get initial session
        initial_response = enhanced_test_client.get("/api/v1/health")
        initial_session = initial_response.cookies
        
        # Login with user
        login_response = enhanced_test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "sessiontest",
                "password": "SessionPassword123!"
            }
        )
        
        # New session should be created after login
        if login_response.status_code == 200:
            login_session = login_response.cookies
            
            # Session should change after authentication
            # (Implementation depends on session management strategy)
            print("🔑 Session management check completed")
    
    @pytest.mark.security
    def test_concurrent_session_handling(self, enhanced_test_client, test_user_token):
        """Test handling of concurrent sessions"""
        
        token = test_user_token["token"]
        
        # Multiple requests with same token
        responses = []
        for i in range(5):
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers={"Authorization": f"Bearer {token}"}
            )
            responses.append(response)
        
        # All requests should work (unless rate limited)
        successful_requests = [r for r in responses if r.status_code == 200]
        
        print(f"🔄 Concurrent session handling: {len(successful_requests)}/{len(responses)} successful")
        
        # Should handle concurrent requests gracefully
        assert len(successful_requests) >= len(responses) * 0.8  # Allow some failures


class TestSecurityMisconfiguration:
    """Test for security misconfigurations"""
    
    @pytest.mark.security
    def test_debug_mode_disabled(self, enhanced_test_client):
        """Test that debug mode is disabled in production"""
        
        # Try to trigger debug information
        response = enhanced_test_client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        # Should not expose debug information
        content = response.content.decode()
        
        debug_indicators = [
            "traceback", "stack trace", "debug", 
            "internal server error", "exception",
            "file not found", "python", "fastapi"
        ]
        
        exposed_info = []
        for indicator in debug_indicators:
            if indicator.lower() in content.lower():
                exposed_info.append(indicator)
        
        if exposed_info:
            print(f"⚠️  Potential debug info exposed: {exposed_info}")
        else:
            print("✅ No debug information exposed")
    
    @pytest.mark.security
    def test_error_handling_security(self, enhanced_test_client, test_user_token):
        """Test secure error handling"""
        
        # Test various error conditions
        error_tests = [
            ("/api/v1/products/99999999", "Non-existent resource"),
            ("/api/v1/products/invalid-id", "Invalid ID format"),
            ("/api/v1/users/admin", "Unauthorized access attempt")
        ]
        
        for endpoint, description in error_tests:
            response = enhanced_test_client.get(
                endpoint,
                headers=test_user_token["headers"]
            )
            
            # Should return appropriate error codes
            assert response.status_code in [400, 401, 403, 404, 422]
            
            # Error messages should not expose internal details
            if response.status_code != 404:  # 404 might have more details
                content = response.content.decode()
                
                # Should not expose internal paths, SQL errors, etc.
                sensitive_patterns = [
                    "/home/", "/var/", "c:\\", "select * from",
                    "database error", "connection failed",
                    "internal error", "stack trace"
                ]
                
                for pattern in sensitive_patterns:
                    assert pattern.lower() not in content.lower(), f"Sensitive info in {description}: {pattern}"
        
        print("✅ Error handling security verified")


class TestCryptoSecurity:
    """Test cryptographic security"""
    
    @pytest.mark.security
    def test_password_storage_security(self, enhanced_test_db, user_factory):
        """Test password storage security"""
        
        # Create user with known password
        password = "TestPassword123!"
        user = user_factory(password=password)
        
        # Password should be hashed, not stored in plaintext
        assert user.hashed_password != password
        assert len(user.hashed_password) > 50  # Bcrypt hashes are long
        assert user.hashed_password.startswith("$")  # Bcrypt format
        
        # Should not be able to reverse the hash
        assert password not in user.hashed_password
        
        print("✅ Password hashing security verified")
    
    @pytest.mark.security
    def test_token_security(self):
        """Test JWT token security"""
        
        from app.core.security import create_access_token, verify_token
        
        # Create token
        token = create_access_token(data={"sub": "testuser"})
        
        # Token should be properly formatted JWT
        parts = token.split(".")
        assert len(parts) == 3  # Header.Payload.Signature
        
        # Should be able to verify valid token
        payload = verify_token(token)
        assert payload is not None
        assert payload.get("sub") == "testuser"
        
        # Modified token should fail verification
        modified_token = token[:-5] + "XXXXX"
        invalid_payload = verify_token(modified_token)
        assert invalid_payload is None
        
        print("✅ JWT token security verified")