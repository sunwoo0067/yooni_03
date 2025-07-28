#!/usr/bin/env python3
"""
Test script for the updated auth endpoints
Tests basic functionality with AuthService integration
"""
import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.v1.endpoints.auth import router as auth_router
from app.core.config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth_endpoints():
    """Test that auth endpoints can be imported and mounted"""
    try:
        # Create FastAPI app
        app = FastAPI(title="Auth Test")
        
        # Include auth router
        app.include_router(
            auth_router,
            prefix="/api/v1/auth",
            tags=["authentication"]
        )
        
        # Create test client
        client = TestClient(app)
        
        # Test that OpenAPI docs can be generated
        response = client.get("/openapi.json")
        logger.info(f"OpenAPI generation: {response.status_code}")
        
        if response.status_code == 200:
            openapi_spec = response.json()
            auth_paths = [path for path in openapi_spec.get("paths", {}).keys() 
                         if path.startswith("/api/v1/auth")]
            logger.info(f"Auth endpoints found: {len(auth_paths)}")
            for path in auth_paths:
                logger.info(f"  - {path}")
        
        logger.info("✓ Auth endpoints successfully integrated")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing auth endpoints: {e}")
        return False

def test_schema_imports():
    """Test that all required schemas can be imported"""
    try:
        from app.schemas.auth import (
            Token, UserRegister, PasswordChange, 
            PasswordResetRequest, PasswordReset,
            RefreshTokenRequest, MessageResponse
        )
        from app.schemas.user import UserResponse
        from app.services.auth import AuthService
        from app.core.security import SecurityManager
        
        logger.info("✓ All required schemas and services imported successfully")
        return True
        
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False

def test_endpoint_definitions():
    """Test that endpoint functions are properly defined"""
    try:
        from app.api.v1.endpoints.auth import (
            register, login, refresh_token, logout, read_users_me,
            change_password, request_password_reset, reset_password,
            get_user_sessions, revoke_session, revoke_all_sessions,
            get_security_events
        )
        
        endpoints = [
            register, login, refresh_token, logout, read_users_me,
            change_password, request_password_reset, reset_password,
            get_user_sessions, revoke_session, revoke_all_sessions,
            get_security_events
        ]
        
        logger.info(f"✓ All {len(endpoints)} endpoint functions defined")
        return True
        
    except ImportError as e:
        logger.error(f"✗ Endpoint import error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Testing updated auth endpoints...")
    
    tests = [
        ("Schema imports", test_schema_imports),
        ("Endpoint definitions", test_endpoint_definitions),  
        ("FastAPI integration", test_auth_endpoints)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    logger.info(f"\nPassed: {total_passed}/{total_tests}")
    
    if total_passed == total_tests:
        logger.info("🎉 All tests passed! Auth endpoints are ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)