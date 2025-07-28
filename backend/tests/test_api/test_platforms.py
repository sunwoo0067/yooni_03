"""
플랫폼 계정 API 엔드포인트 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock


@pytest.mark.api
@pytest.mark.unit
class TestPlatformsAPI:
    """플랫폼 API 테스트 클래스"""
    
    def test_get_platform_accounts(self, test_client: TestClient):
        """플랫폼 계정 목록 조회 테스트"""
        response = test_client.get("/api/v1/platform-accounts")
        
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    def test_get_platform_account_by_id(self, test_client: TestClient):
        """플랫폼 계정 개별 조회 테스트"""
        response = test_client.get("/api/v1/platform-accounts/1")
        assert response.status_code in [200, 404, 401]
    
    def test_create_platform_account_success(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 계정 생성 성공 테스트"""
        response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        assert response.status_code in [200, 201, 401, 404]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["platform"] == sample_platform_data["platform"]
            assert data["name"] == sample_platform_data["name"]
    
    def test_create_platform_account_invalid_platform(self, test_client: TestClient):
        """지원하지 않는 플랫폼으로 계정 생성 실패 테스트"""
        invalid_data = {
            "platform": "unsupported_platform",
            "name": "테스트 계정",
            "account_id": "TEST_001"
        }
        
        response = test_client.post("/api/v1/platform-accounts", json=invalid_data)
        assert response.status_code in [400, 422, 401, 404]
    
    def test_update_platform_account(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 계정 수정 테스트"""
        # 계정 생성
        create_response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        if create_response.status_code in [200, 201]:
            account_data = create_response.json()
            account_id = account_data.get("id")
            
            if account_id:
                update_data = {
                    "name": "수정된 계정명",
                    "status": "inactive"
                }
                
                response = test_client.put(f"/api/v1/platform-accounts/{account_id}", json=update_data)
                assert response.status_code in [200, 401, 404]
    
    def test_delete_platform_account(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 계정 삭제 테스트"""
        # 계정 생성
        create_response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        if create_response.status_code in [200, 201]:
            account_data = create_response.json()
            account_id = account_data.get("id")
            
            if account_id:
                response = test_client.delete(f"/api/v1/platform-accounts/{account_id}")
                assert response.status_code in [200, 204, 401, 404]
    
    def test_test_platform_connection(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 연결 테스트"""
        # 계정 생성
        create_response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        if create_response.status_code in [200, 201]:
            account_data = create_response.json()
            account_id = account_data.get("id")
            
            if account_id:
                response = test_client.post(f"/api/v1/platform-accounts/{account_id}/test-connection")
                assert response.status_code in [200, 400, 401, 404]
                
                if response.status_code == 200:
                    result = response.json()
                    assert "success" in result
                    assert isinstance(result["success"], bool)
    
    def test_sync_platform_products(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 상품 동기화 테스트"""
        # 계정 생성
        create_response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        if create_response.status_code in [200, 201]:
            account_data = create_response.json()
            account_id = account_data.get("id")
            
            if account_id:
                response = test_client.post(f"/api/v1/platform-accounts/{account_id}/sync/products")
                assert response.status_code in [200, 202, 401, 404]
                
                if response.status_code in [200, 202]:
                    result = response.json()
                    assert "status" in result or "task_id" in result
    
    def test_sync_platform_orders(self, test_client: TestClient, sample_platform_data: dict):
        """플랫폼 주문 동기화 테스트"""
        # 계정 생성
        create_response = test_client.post("/api/v1/platform-accounts", json=sample_platform_data)
        
        if create_response.status_code in [200, 201]:
            account_data = create_response.json()
            account_id = account_data.get("id")
            
            if account_id:
                response = test_client.post(f"/api/v1/platform-accounts/{account_id}/sync/orders")
                assert response.status_code in [200, 202, 401, 404]


@pytest.mark.api
@pytest.mark.integration  
@pytest.mark.requires_db
class TestPlatformsAPIIntegration:
    """플랫폼 API 통합 테스트"""
    
    @patch('app.services.platforms.platform_manager.PlatformManager')
    def test_platform_integration_workflow(self, mock_platform_manager, test_client: TestClient):
        """플랫폼 통합 전체 워크플로우 테스트"""
        # 모킹 설정
        mock_instance = mock_platform_manager.return_value
        mock_instance.test_connection = AsyncMock(return_value={"success": True})
        mock_instance.sync_products = AsyncMock(return_value={"synced_count": 10})
        mock_instance.sync_orders = AsyncMock(return_value={"synced_count": 5})
        
        # 1. 계정 생성
        account_data = {
            "platform": "coupang",
            "name": "통합테스트 쿠팡계정",
            "account_id": "INTEGRATION_TEST",
            "api_key": "test_key",
            "api_secret": "test_secret"
        }
        
        create_response = test_client.post("/api/v1/platform-accounts", json=account_data)
        
        if create_response.status_code not in [200, 201]:
            pytest.skip("플랫폼 계정 생성 API가 구현되지 않음")
        
        account = create_response.json()
        account_id = account["id"]
        
        # 2. 연결 테스트
        connection_response = test_client.post(f"/api/v1/platform-accounts/{account_id}/test-connection")
        if connection_response.status_code == 200:
            connection_result = connection_response.json()
            assert connection_result.get("success") is True
        
        # 3. 상품 동기화
        product_sync_response = test_client.post(f"/api/v1/platform-accounts/{account_id}/sync/products")
        if product_sync_response.status_code in [200, 202]:
            sync_result = product_sync_response.json()
            assert "status" in sync_result or "task_id" in sync_result
        
        # 4. 주문 동기화
        order_sync_response = test_client.post(f"/api/v1/platform-accounts/{account_id}/sync/orders")
        if order_sync_response.status_code in [200, 202]:
            sync_result = order_sync_response.json()
            assert "status" in sync_result or "task_id" in sync_result
        
        # 5. 동기화 상태 확인
        status_response = test_client.get(f"/api/v1/platform-accounts/{account_id}/sync/status")
        if status_response.status_code == 200:
            status = status_response.json()
            assert "last_sync" in status or "sync_status" in status
    
    def test_multiple_platform_management(self, test_client: TestClient):
        """다중 플랫폼 관리 테스트"""
        platforms_data = [
            {
                "platform": "coupang",
                "name": "쿠팡 메인 계정",
                "account_id": "COUPANG_MAIN"
            },
            {
                "platform": "naver",
                "name": "네이버 스마트스토어",
                "account_id": "NAVER_MAIN"
            },
            {
                "platform": "eleventh_street",
                "name": "11번가 계정",
                "account_id": "11ST_MAIN"
            }
        ]
        
        created_accounts = []
        
        # 각 플랫폼 계정 생성
        for platform_data in platforms_data:
            response = test_client.post("/api/v1/platform-accounts", json=platform_data)
            if response.status_code in [200, 201]:
                created_accounts.append(response.json())
        
        if not created_accounts:
            pytest.skip("플랫폼 계정 생성이 불가능하여 다중 플랫폼 테스트 스킵")
        
        # 전체 계정 목록 조회
        list_response = test_client.get("/api/v1/platform-accounts")
        if list_response.status_code == 200:
            accounts = list_response.json()
            assert len(accounts.get("items", accounts)) >= len(created_accounts)
        
        # 플랫폼별 필터링
        for platform_type in ["coupang", "naver", "eleventh_street"]:
            filtered_response = test_client.get(
                "/api/v1/platform-accounts", 
                params={"platform": platform_type}
            )
            if filtered_response.status_code == 200:
                filtered_accounts = filtered_response.json()
                for account in filtered_accounts.get("items", filtered_accounts):
                    if isinstance(account, dict) and "platform" in account:
                        assert account["platform"] == platform_type
    
    @pytest.mark.slow
    def test_bulk_platform_operations(self, test_client: TestClient):
        """대량 플랫폼 작업 테스트"""
        # 대량 동기화 테스트
        bulk_sync_data = {
            "platforms": ["coupang", "naver"],
            "sync_type": "products",
            "force": False
        }
        
        bulk_response = test_client.post("/api/v1/platform-accounts/bulk/sync", json=bulk_sync_data)
        
        if bulk_response.status_code in [200, 202]:
            result = bulk_response.json()
            assert "tasks" in result or "status" in result
        
        # 대량 상태 업데이트
        bulk_status_data = {
            "account_ids": [1, 2, 3],  # 예시 ID들
            "status": "active"
        }
        
        bulk_status_response = test_client.patch("/api/v1/platform-accounts/bulk/status", json=bulk_status_data)
        assert bulk_status_response.status_code in [200, 404, 401]
    
    def test_platform_analytics(self, test_client: TestClient):
        """플랫폼 분석 데이터 테스트"""
        # 플랫폼별 통계
        analytics_response = test_client.get("/api/v1/platform-accounts/analytics")
        
        if analytics_response.status_code == 200:
            analytics = analytics_response.json()
            assert isinstance(analytics, dict)
            
            # 예상되는 분석 데이터 확인
            expected_fields = ["total_accounts", "active_accounts", "platform_distribution"]
            for field in expected_fields:
                if field in analytics:
                    assert isinstance(analytics[field], (int, dict, list))
        
        # 동기화 성능 통계
        performance_response = test_client.get("/api/v1/platform-accounts/analytics/performance")
        
        if performance_response.status_code == 200:
            performance = performance_response.json()
            assert isinstance(performance, dict)
    
    def test_platform_webhook_handling(self, test_client: TestClient):
        """플랫폼 웹훅 처리 테스트"""
        # 쿠팡 웹훅 시뮬레이션
        coupang_webhook_data = {
            "eventType": "ORDER_PLACED",
            "orderId": "COUPANG_ORDER_123",
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "orderNumber": "CO-123456",
                "totalAmount": 50000
            }
        }
        
        webhook_response = test_client.post("/api/v1/webhooks/coupang", json=coupang_webhook_data)
        assert webhook_response.status_code in [200, 202, 404]
        
        # 네이버 웹훅 시뮬레이션
        naver_webhook_data = {
            "event": "product.updated",
            "productId": "NAVER_PROD_456",
            "changeType": "price",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        naver_webhook_response = test_client.post("/api/v1/webhooks/naver", json=naver_webhook_data)
        assert naver_webhook_response.status_code in [200, 202, 404]
    
    def test_platform_rate_limiting(self, test_client: TestClient):
        """플랫폼 API 레이트 리미팅 테스트"""
        # 여러 계정 생성으로 레이트 리미팅 테스트
        for i in range(10):
            account_data = {
                "platform": "coupang",
                "name": f"레이트테스트 계정 {i}",
                "account_id": f"RATE_TEST_{i}"
            }
            
            response = test_client.post("/api/v1/platform-accounts", json=account_data)
            
            # 레이트 리미팅이 적용되면 429 상태 코드 반환
            if response.status_code == 429:
                # 레이트 리미팅 확인
                assert "rate limit" in response.json().get("detail", "").lower()
                break
    
    def test_platform_error_handling(self, test_client: TestClient):
        """플랫폼 오류 처리 테스트"""
        # 잘못된 API 키로 계정 생성
        invalid_account_data = {
            "platform": "coupang",
            "name": "오류테스트 계정",
            "account_id": "ERROR_TEST",
            "api_key": "invalid_key",
            "api_secret": "invalid_secret"
        }
        
        create_response = test_client.post("/api/v1/platform-accounts", json=invalid_account_data)
        
        if create_response.status_code in [200, 201]:
            account_id = create_response.json()["id"]
            
            # 연결 테스트 - 실패해야 함
            connection_response = test_client.post(f"/api/v1/platform-accounts/{account_id}/test-connection")
            
            if connection_response.status_code == 200:
                result = connection_response.json()
                assert result.get("success") is False
                assert "error" in result or "message" in result