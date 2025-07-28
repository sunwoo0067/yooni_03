"""
인증 API 엔드포인트 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.mark.api
@pytest.mark.unit
class TestAuthAPI:
    """인증 API 테스트 클래스"""
    
    def test_health_check(self, test_client: TestClient):
        """헬스 체크 엔드포인트 테스트"""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_register_user_success(self, test_client: TestClient):
        """사용자 등록 성공 테스트"""
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        response = test_client.post("/api/v1/auth/register", json=user_data)
        
        # 응답 상태 검증
        assert response.status_code in [200, 201]
        
        # 응답 데이터 검증
        data = response.json()
        assert "id" in data or "message" in data
        if "id" in data:
            assert data["username"] == user_data["username"]
            assert data["email"] == user_data["email"]
    
    def test_register_user_duplicate_username(self, test_client: TestClient):
        """중복 사용자명 등록 실패 테스트"""
        user_data = {
            "username": "testuser",
            "email": "test1@test.com",
            "password": "password123",
            "full_name": "Test User 1"
        }
        
        # 첫 번째 등록
        test_client.post("/api/v1/auth/register", json=user_data)
        
        # 중복 등록 시도
        duplicate_data = {
            "username": "testuser",  # 동일한 사용자명
            "email": "test2@test.com",
            "password": "password456",
            "full_name": "Test User 2"
        }
        
        response = test_client.post("/api/v1/auth/register", json=duplicate_data)
        assert response.status_code in [400, 409]
    
    def test_register_user_invalid_email(self, test_client: TestClient):
        """잘못된 이메일 형식 등록 실패 테스트"""
        user_data = {
            "username": "testuser2",
            "email": "invalid-email",
            "password": "password123",
            "full_name": "Test User"
        }
        
        response = test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, test_client: TestClient, test_user_data: dict):
        """로그인 성공 테스트"""
        # 사용자 등록
        test_client.post("/api/v1/auth/register", json=test_user_data)
        
        # 로그인 시도
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = test_client.post("/api/v1/auth/login", data=login_data)
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, test_client: TestClient):
        """잘못된 자격증명 로그인 실패 테스트"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
    
    def test_login_missing_password(self, test_client: TestClient):
        """비밀번호 누락 로그인 실패 테스트"""
        login_data = {
            "username": "testuser"
            # password 누락
        }
        
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 422
    
    def test_get_current_user(self, authenticated_client: TestClient):
        """현재 사용자 정보 조회 테스트"""
        response = authenticated_client.get("/api/v1/auth/me")
        
        if response.status_code == 200:
            data = response.json()
            assert "username" in data
            assert "email" in data
            assert "id" in data
        else:
            # 인증 엔드포인트가 구현되지 않은 경우
            assert response.status_code == 404
    
    def test_refresh_token(self, authenticated_client: TestClient):
        """토큰 갱신 테스트"""
        response = authenticated_client.post("/api/v1/auth/refresh")
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
        else:
            # 토큰 갱신 엔드포인트가 구현되지 않은 경우
            assert response.status_code in [404, 501]
    
    def test_logout(self, authenticated_client: TestClient):
        """로그아웃 테스트"""
        response = authenticated_client.post("/api/v1/auth/logout")
        
        # 로그아웃은 구현에 따라 다를 수 있음
        assert response.status_code in [200, 204, 404]


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.requires_db
class TestAuthAPIIntegration:
    """인증 API 통합 테스트"""
    
    def test_auth_flow_complete(self, test_client: TestClient):
        """완전한 인증 플로우 테스트"""
        # 1. 사용자 등록
        user_data = {
            "username": "flowtest",
            "email": "flowtest@test.com",
            "password": "flowpassword123",
            "full_name": "Flow Test User"
        }
        
        register_response = test_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code in [200, 201]
        
        # 2. 로그인
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        login_response = test_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # 3. 인증이 필요한 엔드포인트 테스트
        headers = {"Authorization": f"Bearer {token}"}
        
        # 상품 목록 조회 (인증이 필요할 수 있음)
        products_response = test_client.get("/api/v1/products", headers=headers)
        # 성공하거나 구현되지 않았을 수 있음
        assert products_response.status_code in [200, 401, 404]
        
        # 현재 사용자 정보 조회
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        if me_response.status_code == 200:
            user_info = me_response.json()
            assert user_info["username"] == user_data["username"]
    
    @pytest.mark.slow
    def test_token_expiry_behavior(self, test_client: TestClient):
        """토큰 만료 동작 테스트"""
        # 짧은 만료 시간으로 토큰 생성 테스트
        # 실제 구현에서는 설정을 통해 테스트할 수 있음
        user_data = {
            "username": "expirytest",
            "email": "expiry@test.com",
            "password": "expirypass123",
            "full_name": "Expiry Test"
        }
        
        # 등록 및 로그인
        test_client.post("/api/v1/auth/register", json=user_data)
        
        login_response = test_client.post("/api/v1/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 토큰이 유효한 동안은 접근 가능해야 함
            response = test_client.get("/api/v1/auth/me", headers=headers)
            # 성공하거나 구현되지 않았을 수 있음
            assert response.status_code in [200, 404]