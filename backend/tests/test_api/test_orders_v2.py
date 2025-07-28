"""
Tests for Orders V2 API endpoints.
Orders V2 API 엔드포인트 테스트.
"""
import pytest
from fastapi import status
from app.core.constants import OrderStatus


@pytest.mark.asyncio
@pytest.mark.unit
class TestOrdersV2API:
    """Orders V2 API 단위 테스트"""
    
    async def test_create_order_success(
        self,
        async_client,
        authenticated_headers,
        test_product
    ):
        """주문 생성 성공 테스트"""
        # Given: 주문 데이터
        order_data = {
            "items": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 2
                }
            ],
            "shipping_address": {
                "street": "123 Test Street",
                "city": "Test City",
                "postal_code": "12345"
            },
            "payment_method": "credit_card",
            "notes": "Please handle with care"
        }
        
        # When: 주문 생성 API 호출
        response = await async_client.post(
            "/api/v1/orders",
            json=order_data,
            headers=authenticated_headers
        )
        
        # Then: 응답 검증
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "id" in data
        assert data["status"] == OrderStatus.PENDING.value
        assert float(data["total_amount"]) > 0
        
    async def test_create_order_invalid_product(
        self,
        async_client,
        authenticated_headers
    ):
        """잘못된 상품 ID로 주문 생성 시 에러 테스트"""
        # Given: 존재하지 않는 상품 ID
        order_data = {
            "items": [
                {
                    "product_id": "non-existent-id",
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "street": "123 Test Street",
                "city": "Test City",
                "postal_code": "12345"
            },
            "payment_method": "credit_card"
        }
        
        # When: 주문 생성 시도
        response = await async_client.post(
            "/api/v1/orders",
            json=order_data,
            headers=authenticated_headers
        )
        
        # Then: 400 에러
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    async def test_create_order_validation_errors(
        self,
        async_client,
        authenticated_headers
    ):
        """입력 검증 에러 테스트"""
        # Given: 잘못된 데이터들
        test_cases = [
            {
                "name": "no items",
                "data": {
                    "items": [],
                    "shipping_address": {"street": "123"},
                    "payment_method": "card"
                }
            },
            {
                "name": "invalid quantity",
                "data": {
                    "items": [{"product_id": "123", "quantity": 0}],
                    "shipping_address": {"street": "123"},
                    "payment_method": "card"
                }
            },
            {
                "name": "too many items",
                "data": {
                    "items": [
                        {"product_id": f"id-{i}", "quantity": 1}
                        for i in range(100)  # 제한 초과
                    ],
                    "shipping_address": {"street": "123"},
                    "payment_method": "card"
                }
            }
        ]
        
        for test_case in test_cases:
            # When: 잘못된 데이터로 요청
            response = await async_client.post(
                "/api/v1/orders",
                json=test_case["data"],
                headers=authenticated_headers
            )
            
            # Then: 422 검증 에러
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
                f"Test case '{test_case['name']}' failed"
            )
            
    async def test_list_orders_with_pagination(
        self,
        async_client,
        authenticated_headers,
        test_orders  # 여러 테스트 주문
    ):
        """페이지네이션을 사용한 주문 목록 조회 테스트"""
        # When: 첫 페이지 조회
        response = await async_client.get(
            "/api/v1/orders?page=1&size=5",
            headers=authenticated_headers
        )
        
        # Then: 응답 검증
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data) <= 5
        
        # When: 상태 필터링
        response2 = await async_client.get(
            f"/api/v1/orders?status={OrderStatus.PENDING.value}",
            headers=authenticated_headers
        )
        
        # Then: 필터링된 결과 검증
        assert response2.status_code == status.HTTP_200_OK
        
        filtered_data = response2.json()
        assert all(
            order["status"] == OrderStatus.PENDING.value
            for order in filtered_data
        )
        
    async def test_get_order_by_id(
        self,
        async_client,
        authenticated_headers,
        test_order
    ):
        """ID로 주문 조회 테스트"""
        # When: 주문 조회
        response = await async_client.get(
            f"/api/v1/orders/{test_order.id}",
            headers=authenticated_headers
        )
        
        # Then: 응답 검증
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == str(test_order.id)
        
    async def test_get_order_unauthorized(
        self,
        async_client,
        authenticated_headers,
        other_user_order  # 다른 사용자의 주문
    ):
        """권한 없는 주문 조회 시 에러 테스트"""
        # When: 다른 사용자의 주문 조회 시도
        response = await async_client.get(
            f"/api/v1/orders/{other_user_order.id}",
            headers=authenticated_headers
        )
        
        # Then: 404 (보안상 403 대신 404 반환)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    async def test_update_order_status_success(
        self,
        async_client,
        authenticated_headers,
        test_order
    ):
        """주문 상태 업데이트 성공 테스트"""
        # Given: 상태 업데이트 데이터
        update_data = {
            "status": OrderStatus.PROCESSING.value,
            "reason": "Payment confirmed"
        }
        
        # When: 상태 업데이트
        response = await async_client.patch(
            f"/api/v1/orders/{test_order.id}/status",
            json=update_data,
            headers=authenticated_headers
        )
        
        # Then: 응답 검증
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["status"] == OrderStatus.PROCESSING.value
        
    async def test_update_order_invalid_transition(
        self,
        async_client,
        authenticated_headers,
        completed_order  # 완료된 주문
    ):
        """잘못된 상태 전환 시 에러 테스트"""
        # Given: 완료된 주문을 다시 처리중으로 변경 시도
        update_data = {
            "status": OrderStatus.PROCESSING.value,
            "reason": "Invalid transition"
        }
        
        # When: 상태 업데이트 시도
        response = await async_client.patch(
            f"/api/v1/orders/{completed_order.id}/status",
            json=update_data,
            headers=authenticated_headers
        )
        
        # Then: 400 에러
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.integration
class TestOrdersV2APIIntegration:
    """Orders V2 API 통합 테스트"""
    
    async def test_order_lifecycle(
        self,
        async_client,
        authenticated_headers,
        test_product
    ):
        """주문 전체 라이프사이클 테스트"""
        # Step 1: 주문 생성
        order_data = {
            "items": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 3
                }
            ],
            "shipping_address": {
                "street": "456 Integration St",
                "city": "Test City",
                "postal_code": "54321"
            },
            "payment_method": "bank_transfer"
        }
        
        create_response = await async_client.post(
            "/api/v1/orders",
            json=order_data,
            headers=authenticated_headers
        )
        
        assert create_response.status_code == status.HTTP_200_OK
        order_id = create_response.json()["id"]
        
        # Step 2: 주문 조회
        get_response = await async_client.get(
            f"/api/v1/orders/{order_id}",
            headers=authenticated_headers
        )
        
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["status"] == OrderStatus.PENDING.value
        
        # Step 3: 상태 업데이트 (PENDING → PROCESSING)
        update1 = await async_client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={
                "status": OrderStatus.PROCESSING.value,
                "reason": "Payment received"
            },
            headers=authenticated_headers
        )
        
        assert update1.status_code == status.HTTP_200_OK
        
        # Step 4: 상태 업데이트 (PROCESSING → CONFIRMED)
        update2 = await async_client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={
                "status": OrderStatus.CONFIRMED.value,
                "reason": "Ready for shipping"
            },
            headers=authenticated_headers
        )
        
        assert update2.status_code == status.HTTP_200_OK
        
        # Step 5: 최종 상태 확인
        final_response = await async_client.get(
            f"/api/v1/orders/{order_id}",
            headers=authenticated_headers
        )
        
        assert final_response.status_code == status.HTTP_200_OK
        assert final_response.json()["status"] == OrderStatus.CONFIRMED.value


# 테스트용 픽스처들
@pytest.fixture
async def async_client(app):
    """비동기 테스트 클라이언트"""
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_headers(test_user, auth_service):
    """인증된 헤더"""
    token = await auth_service.create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_order(async_session, test_user, test_product):
    """테스트 주문"""
    from app.models.order_core import Order
    
    order = Order(
        user_id=test_user.id,
        status=OrderStatus.PENDING.value,
        total_amount=200.00
    )
    async_session.add(order)
    await async_session.commit()
    
    return order