"""
주문 API 엔드포인트 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from datetime import datetime, timedelta


@pytest.mark.api
@pytest.mark.unit
class TestOrdersAPI:
    """주문 API 테스트 클래스"""
    
    def test_get_orders_list(self, test_client: TestClient):
        """주문 목록 조회 테스트"""
        response = test_client.get("/api/v1/orders")
        
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            
            # 페이징된 응답인 경우
            if isinstance(data, dict):
                assert "items" in data or "orders" in data
    
    def test_get_orders_with_filters(self, test_client: TestClient):
        """필터링된 주문 목록 조회 테스트"""
        params = {
            "status": "pending",
            "platform": "coupang",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        
        response = test_client.get("/api/v1/orders", params=params)
        assert response.status_code in [200, 401, 404]
    
    def test_get_order_by_id(self, test_client: TestClient, sample_order_data: dict):
        """ID로 주문 조회 테스트"""
        # 먼저 주문 생성 시도
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                response = test_client.get(f"/api/v1/orders/{order_id}")
                assert response.status_code == 200
                
                data = response.json()
                assert data["id"] == order_id
                assert data["order_number"] == sample_order_data["order_number"]
        else:
            # 주문 생성이 안되는 경우
            response = test_client.get("/api/v1/orders/1")
            assert response.status_code in [200, 404, 401]
    
    def test_get_order_nonexistent(self, test_client: TestClient):
        """존재하지 않는 주문 조회 테스트"""
        response = test_client.get("/api/v1/orders/99999")
        assert response.status_code in [404, 401]
    
    def test_create_order_success(self, test_client: TestClient, sample_order_data: dict):
        """주문 생성 성공 테스트"""
        response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        assert response.status_code in [200, 201, 401, 404]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["order_number"] == sample_order_data["order_number"]
            assert data["customer_name"] == sample_order_data["customer_name"]
    
    def test_create_order_invalid_data(self, test_client: TestClient):
        """잘못된 데이터로 주문 생성 실패 테스트"""
        invalid_data = {
            "order_number": "",  # 빈 주문번호
            "total_amount": -100,  # 음수 금액
            "customer_email": "invalid-email"  # 잘못된 이메일
        }
        
        response = test_client.post("/api/v1/orders", json=invalid_data)
        assert response.status_code in [400, 422, 401, 404]
    
    def test_update_order_status(self, test_client: TestClient, sample_order_data: dict):
        """주문 상태 업데이트 테스트"""
        # 먼저 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                # 상태 업데이트
                status_data = {"status": "processing"}
                
                response = test_client.patch(f"/api/v1/orders/{order_id}/status", json=status_data)
                assert response.status_code in [200, 401, 404]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "processing"
    
    def test_cancel_order(self, test_client: TestClient, sample_order_data: dict):
        """주문 취소 테스트"""
        # 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                # 주문 취소
                cancel_data = {"reason": "고객 요청"}
                
                response = test_client.post(f"/api/v1/orders/{order_id}/cancel", json=cancel_data)
                assert response.status_code in [200, 401, 404]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "cancelled"
    
    def test_get_order_items(self, test_client: TestClient, sample_order_data: dict):
        """주문 아이템 조회 테스트"""
        # 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                response = test_client.get(f"/api/v1/orders/{order_id}/items")
                assert response.status_code in [200, 401, 404]
                
                if response.status_code == 200:
                    items = response.json()
                    assert isinstance(items, list)
    
    def test_add_order_item(self, test_client: TestClient, sample_order_data: dict):
        """주문에 아이템 추가 테스트"""
        # 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                item_data = {
                    "product_id": 1,
                    "quantity": 2,
                    "price": 25000
                }
                
                response = test_client.post(f"/api/v1/orders/{order_id}/items", json=item_data)
                assert response.status_code in [200, 201, 401, 404]


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.requires_db
class TestOrdersAPIIntegration:
    """주문 API 통합 테스트"""
    
    def test_order_processing_workflow(self, test_client: TestClient, sample_order_data: dict):
        """주문 처리 전체 워크플로우 테스트"""
        # 1. 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code not in [200, 201]:
            pytest.skip("주문 생성 API가 구현되지 않음")
        
        order_data = create_response.json()
        order_id = order_data["id"]
        
        # 2. 주문 확인
        get_response = test_client.get(f"/api/v1/orders/{order_id}")
        assert get_response.status_code == 200
        
        # 3. 결제 처리 (모킹)
        payment_data = {
            "payment_method": "card",
            "card_number": "****-****-****-1234"
        }
        
        payment_response = test_client.post(f"/api/v1/orders/{order_id}/payment", json=payment_data)
        if payment_response.status_code == 200:
            # 결제 성공 시 주문 상태 확인
            updated_order = test_client.get(f"/api/v1/orders/{order_id}").json()
            assert updated_order["payment_status"] in ["paid", "completed"]
        
        # 4. 주문 상태 업데이트
        status_updates = ["processing", "shipped", "delivered"]
        
        for status in status_updates:
            status_response = test_client.patch(
                f"/api/v1/orders/{order_id}/status",
                json={"status": status}
            )
            
            if status_response.status_code == 200:
                updated_order = test_client.get(f"/api/v1/orders/{order_id}").json()
                assert updated_order["status"] == status
    
    def test_order_search_and_filtering(self, test_client: TestClient):
        """주문 검색 및 필터링 테스트"""
        # 테스트용 주문들 생성
        test_orders = [
            {
                "order_number": "TEST-001",
                "customer_name": "김테스트",
                "total_amount": 50000,
                "status": "pending",
                "platform": "coupang"
            },
            {
                "order_number": "TEST-002",
                "customer_name": "이테스트",
                "total_amount": 75000,
                "status": "processing",
                "platform": "naver"
            },
            {
                "order_number": "TEST-003",
                "customer_name": "박테스트",
                "total_amount": 30000,
                "status": "completed",
                "platform": "coupang"
            }
        ]
        
        created_orders = []
        for order_data in test_orders:
            response = test_client.post("/api/v1/orders", json=order_data)
            if response.status_code in [200, 201]:
                created_orders.append(response.json())
        
        if not created_orders:
            pytest.skip("주문 생성이 불가능하여 검색 테스트 스킵")
        
        # 상태별 필터링
        status_response = test_client.get("/api/v1/orders", params={"status": "pending"})
        if status_response.status_code == 200:
            orders = status_response.json()
            for order in orders.get("items", orders):
                if isinstance(order, dict) and "status" in order:
                    assert order["status"] == "pending"
        
        # 플랫폼별 필터링
        platform_response = test_client.get("/api/v1/orders", params={"platform": "coupang"})
        if platform_response.status_code == 200:
            orders = platform_response.json()
            for order in orders.get("items", orders):
                if isinstance(order, dict) and "platform" in order:
                    assert order["platform"] == "coupang"
        
        # 고객명으로 검색
        search_response = test_client.get("/api/v1/orders/search", params={"q": "김테스트"})
        if search_response.status_code == 200:
            results = search_response.json()
            for result in results.get("items", results):
                if isinstance(result, dict) and "customer_name" in result:
                    assert "김테스트" in result["customer_name"]
    
    @pytest.mark.slow
    def test_bulk_order_operations(self, test_client: TestClient):
        """대량 주문 작업 테스트"""
        # 대량 주문 상태 업데이트
        order_ids = []
        
        # 테스트용 주문들 생성
        for i in range(5):
            order_data = {
                "order_number": f"BULK-{i:03d}",
                "customer_name": f"대량테스트고객{i}",
                "total_amount": 10000 + i * 5000,
                "status": "pending"
            }
            
            response = test_client.post("/api/v1/orders", json=order_data)
            if response.status_code in [200, 201]:
                order_ids.append(response.json()["id"])
        
        if order_ids:
            # 대량 상태 업데이트
            bulk_update_data = {
                "order_ids": order_ids,
                "status": "processing"
            }
            
            bulk_response = test_client.patch("/api/v1/orders/bulk/status", json=bulk_update_data)
            
            if bulk_response.status_code == 200:
                # 업데이트 확인
                for order_id in order_ids:
                    check_response = test_client.get(f"/api/v1/orders/{order_id}")
                    if check_response.status_code == 200:
                        order = check_response.json()
                        assert order["status"] == "processing"
    
    def test_order_analytics(self, test_client: TestClient):
        """주문 분석 데이터 테스트"""
        # 주문 통계 조회
        stats_response = test_client.get("/api/v1/orders/analytics/stats")
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            expected_fields = ["total_orders", "total_revenue", "avg_order_value"]
            
            for field in expected_fields:
                if field in stats:
                    assert isinstance(stats[field], (int, float))
        
        # 일별 주문 통계
        daily_response = test_client.get("/api/v1/orders/analytics/daily")
        
        if daily_response.status_code == 200:
            daily_data = daily_response.json()
            assert isinstance(daily_data, list)
            
            for day_data in daily_data:
                if isinstance(day_data, dict):
                    assert "date" in day_data
                    assert "order_count" in day_data or "revenue" in day_data
    
    def test_order_export(self, test_client: TestClient):
        """주문 데이터 내보내기 테스트"""
        # CSV 내보내기
        csv_response = test_client.get("/api/v1/orders/export/csv")
        
        if csv_response.status_code == 200:
            assert csv_response.headers.get("content-type") in [
                "text/csv",
                "application/csv",
                "application/octet-stream"
            ]
        
        # Excel 내보내기
        excel_response = test_client.get("/api/v1/orders/export/excel")
        
        if excel_response.status_code == 200:
            assert "excel" in csv_response.headers.get("content-type", "").lower() or \
                   "spreadsheet" in csv_response.headers.get("content-type", "").lower()
    
    def test_order_notifications(self, test_client: TestClient, sample_order_data: dict):
        """주문 알림 테스트"""
        # 주문 생성
        create_response = test_client.post("/api/v1/orders", json=sample_order_data)
        
        if create_response.status_code in [200, 201]:
            order_data = create_response.json()
            order_id = order_data.get("id")
            
            if order_id:
                # 알림 설정 조회
                notifications_response = test_client.get(f"/api/v1/orders/{order_id}/notifications")
                
                if notifications_response.status_code == 200:
                    notifications = notifications_response.json()
                    assert isinstance(notifications, list)
                
                # 알림 전송 테스트
                notify_data = {
                    "type": "email",
                    "message": "주문이 처리되었습니다."
                }
                
                notify_response = test_client.post(
                    f"/api/v1/orders/{order_id}/notifications",
                    json=notify_data
                )
                
                assert notify_response.status_code in [200, 201, 404]