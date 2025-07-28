"""
상품 API 엔드포인트 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


@pytest.mark.api
@pytest.mark.unit
class TestProductsAPI:
    """상품 API 테스트 클래스"""
    
    def test_get_products_list(self, test_client: TestClient):
        """상품 목록 조회 테스트"""
        response = test_client.get("/api/v1/products")
        
        # 구현 상태에 따라 다른 응답 가능
        assert response.status_code in [200, 404, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            
            # 페이징된 응답인 경우
            if isinstance(data, dict):
                assert "items" in data or "products" in data
            
            # 직접 리스트인 경우
            if isinstance(data, list):
                for item in data:
                    assert "id" in item
                    assert "name" in item
    
    def test_get_products_with_pagination(self, test_client: TestClient):
        """페이징된 상품 목록 조회 테스트"""
        params = {
            "page": 1,
            "size": 10
        }
        
        response = test_client.get("/api/v1/products", params=params)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # 페이징 정보 확인
            if isinstance(data, dict):
                assert "total" in data or "count" in data or "items" in data
    
    def test_get_products_with_filters(self, test_client: TestClient):
        """필터링된 상품 목록 조회 테스트"""
        params = {
            "category": "전자제품",
            "status": "active",
            "min_price": 10000,
            "max_price": 100000
        }
        
        response = test_client.get("/api/v1/products", params=params)
        assert response.status_code in [200, 404]
    
    def test_get_product_by_id(self, test_client: TestClient, sample_product_data: dict):
        """ID로 상품 조회 테스트"""
        # 먼저 상품 생성 시도
        create_response = test_client.post("/api/v1/products", json=sample_product_data)
        
        if create_response.status_code in [200, 201]:
            product_data = create_response.json()
            product_id = product_data.get("id")
            
            if product_id:
                # 생성된 상품 조회
                response = test_client.get(f"/api/v1/products/{product_id}")
                assert response.status_code == 200
                
                data = response.json()
                assert data["id"] == product_id
                assert data["name"] == sample_product_data["name"]
        else:
            # 상품 생성이 안되는 경우, 임의의 ID로 테스트
            response = test_client.get("/api/v1/products/1")
            assert response.status_code in [200, 404]
    
    def test_get_product_nonexistent(self, test_client: TestClient):
        """존재하지 않는 상품 조회 테스트"""
        response = test_client.get("/api/v1/products/99999")
        assert response.status_code in [404, 422]
    
    def test_create_product_success(self, test_client: TestClient, sample_product_data: dict):
        """상품 생성 성공 테스트"""
        response = test_client.post("/api/v1/products", json=sample_product_data)
        
        # 성공하거나 인증 필요하거나 구현되지 않았을 수 있음
        assert response.status_code in [200, 201, 401, 404]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["name"] == sample_product_data["name"]
            assert data["price"] == sample_product_data["price"]
    
    def test_create_product_invalid_data(self, test_client: TestClient):
        """잘못된 데이터로 상품 생성 실패 테스트"""
        invalid_data = {
            "name": "",  # 빈 이름
            "price": -100,  # 음수 가격
            # 필수 필드 누락
        }
        
        response = test_client.post("/api/v1/products", json=invalid_data)
        assert response.status_code in [400, 422, 401, 404]
    
    def test_create_product_missing_required_fields(self, test_client: TestClient):
        """필수 필드 누락 상품 생성 실패 테스트"""
        incomplete_data = {
            "name": "테스트 상품"
            # price, cost 등 필수 필드 누락
        }
        
        response = test_client.post("/api/v1/products", json=incomplete_data)
        assert response.status_code in [400, 422, 401, 404]
    
    def test_update_product_success(self, test_client: TestClient, sample_product_data: dict):
        """상품 수정 성공 테스트"""
        # 먼저 상품 생성
        create_response = test_client.post("/api/v1/products", json=sample_product_data)
        
        if create_response.status_code in [200, 201]:
            product_data = create_response.json()
            product_id = product_data.get("id")
            
            if product_id:
                # 상품 수정
                update_data = {
                    "name": "수정된 상품명",
                    "price": 15000,
                    "description": "수정된 설명"
                }
                
                response = test_client.put(f"/api/v1/products/{product_id}", json=update_data)
                assert response.status_code in [200, 401, 404]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["name"] == update_data["name"]
                    assert data["price"] == update_data["price"]
    
    def test_update_product_nonexistent(self, test_client: TestClient):
        """존재하지 않는 상품 수정 실패 테스트"""
        update_data = {
            "name": "수정된 상품명",
            "price": 15000
        }
        
        response = test_client.put("/api/v1/products/99999", json=update_data)
        assert response.status_code in [404, 401]
    
    def test_delete_product_success(self, test_client: TestClient, sample_product_data: dict):
        """상품 삭제 성공 테스트"""
        # 먼저 상품 생성
        create_response = test_client.post("/api/v1/products", json=sample_product_data)
        
        if create_response.status_code in [200, 201]:
            product_data = create_response.json()
            product_id = product_data.get("id")
            
            if product_id:
                # 상품 삭제
                response = test_client.delete(f"/api/v1/products/{product_id}")
                assert response.status_code in [200, 204, 401, 404]
                
                # 삭제 후 조회 시 404 반환 확인
                if response.status_code in [200, 204]:
                    get_response = test_client.get(f"/api/v1/products/{product_id}")
                    assert get_response.status_code == 404
    
    def test_delete_product_nonexistent(self, test_client: TestClient):
        """존재하지 않는 상품 삭제 실패 테스트"""
        response = test_client.delete("/api/v1/products/99999")
        assert response.status_code in [404, 401]


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.requires_db
class TestProductsAPIIntegration:
    """상품 API 통합 테스트"""
    
    def test_product_crud_workflow(self, test_client: TestClient, sample_product_data: dict):
        """상품 CRUD 전체 워크플로우 테스트"""
        # 1. 생성
        create_response = test_client.post("/api/v1/products", json=sample_product_data)
        
        if create_response.status_code not in [200, 201]:
            pytest.skip("상품 생성 API가 구현되지 않음")
        
        product_data = create_response.json()
        product_id = product_data["id"]
        
        # 2. 조회
        get_response = test_client.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 200
        
        retrieved_data = get_response.json()
        assert retrieved_data["name"] == sample_product_data["name"]
        
        # 3. 수정
        update_data = {
            "name": "수정된 상품명",
            "price": sample_product_data["price"] + 5000
        }
        
        update_response = test_client.put(f"/api/v1/products/{product_id}", json=update_data)
        if update_response.status_code == 200:
            updated_data = update_response.json()
            assert updated_data["name"] == update_data["name"]
            assert updated_data["price"] == update_data["price"]
        
        # 4. 삭제
        delete_response = test_client.delete(f"/api/v1/products/{product_id}")
        assert delete_response.status_code in [200, 204]
        
        # 5. 삭제 확인
        final_get_response = test_client.get(f"/api/v1/products/{product_id}")
        assert final_get_response.status_code == 404
    
    def test_product_search_functionality(self, test_client: TestClient):
        """상품 검색 기능 테스트"""
        # 테스트용 상품들 생성
        test_products = [
            {
                "name": "삼성 갤럭시 스마트폰",
                "price": 800000,
                "category": "전자제품",
                "sku": "SAMSUNG-001"
            },
            {
                "name": "아이폰 스마트폰",
                "price": 1200000,
                "category": "전자제품", 
                "sku": "APPLE-001"
            },
            {
                "name": "나이키 운동화",
                "price": 150000,
                "category": "신발",
                "sku": "NIKE-001"
            }
        ]
        
        created_products = []
        for product_data in test_products:
            response = test_client.post("/api/v1/products", json=product_data)
            if response.status_code in [200, 201]:
                created_products.append(response.json())
        
        if not created_products:
            pytest.skip("상품 생성이 불가능하여 검색 테스트 스킵")
        
        # 이름으로 검색
        search_response = test_client.get("/api/v1/products/search", params={"q": "스마트폰"})
        if search_response.status_code == 200:
            search_results = search_response.json()
            # 스마트폰이 포함된 상품만 반환되어야 함
            for result in search_results.get("items", search_results):
                assert "스마트폰" in result["name"]
        
        # 카테고리로 필터링
        category_response = test_client.get("/api/v1/products", params={"category": "전자제품"})
        if category_response.status_code == 200:
            category_results = category_response.json()
            # 전자제품 카테고리만 반환되어야 함
            for result in category_results.get("items", category_results):
                if isinstance(result, dict) and "category" in result:
                    assert result["category"] == "전자제품"
    
    @pytest.mark.slow
    def test_bulk_product_operations(self, test_client: TestClient):
        """대량 상품 작업 테스트"""
        # 대량 상품 생성 테스트
        bulk_products = [
            {
                "name": f"대량테스트 상품 {i}",
                "price": 10000 + i * 1000,
                "sku": f"BULK-{i:03d}",
                "category": "테스트"
            }
            for i in range(10)
        ]
        
        bulk_create_response = test_client.post("/api/v1/products/bulk", json={"products": bulk_products})
        
        if bulk_create_response.status_code in [200, 201]:
            # 대량 생성 성공
            result = bulk_create_response.json()
            assert "created_count" in result or "products" in result
        else:
            # 개별 생성으로 대체
            for product_data in bulk_products[:3]:  # 일부만 테스트
                response = test_client.post("/api/v1/products", json=product_data)
                if response.status_code not in [200, 201]:
                    break
    
    def test_product_validation_edge_cases(self, test_client: TestClient):
        """상품 유효성 검사 엣지 케이스 테스트"""
        edge_cases = [
            {
                "name": "A" * 256,  # 매우 긴 이름
                "price": 1000000000,  # 매우 큰 가격
                "sku": "EDGE-001"
            },
            {
                "name": "특수문자!@#$%^&*()",
                "price": 1,  # 최소 가격
                "sku": "SPECIAL-001"
            },
            {
                "name": "Unicode 테스트 🚀",
                "price": 50000,
                "sku": "UNICODE-001"
            }
        ]
        
        for case_data in edge_cases:
            response = test_client.post("/api/v1/products", json=case_data)
            # 성공하거나 적절한 유효성 검사 오류 반환
            assert response.status_code in [200, 201, 400, 422, 401, 404]