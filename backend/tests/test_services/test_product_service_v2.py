"""
Tests for ProductServiceV2.
ProductServiceV2 테스트.
"""
import pytest
from decimal import Decimal
from app.core.constants import ProductStatus
from app.core.exceptions import NotFoundError, ValidationError


@pytest.mark.asyncio
@pytest.mark.unit
class TestProductServiceV2:
    """ProductServiceV2 단위 테스트"""
    
    async def test_get_product_detail_with_cache(
        self, 
        product_service_v2, 
        integration_helper,
        cache_service
    ):
        """캐시를 사용한 상품 상세 조회 테스트"""
        # Given: 테스트 상품 생성
        product = await integration_helper.create_test_product(
            name="Cache Test Product",
            price=Decimal("150.00")
        )
        
        # When: 첫 번째 조회 (캐시 미스)
        result1 = await product_service_v2.get_product_detail(
            str(product.id),
            use_cache=True
        )
        
        # Then: 결과 검증
        assert result1["name"] == "Cache Test Product"
        assert float(result1["price"]) == 150.00
        
        # When: 두 번째 조회 (캐시 히트)
        result2 = await product_service_v2.get_product_detail(
            str(product.id),
            use_cache=True
        )
        
        # Then: 동일한 결과
        assert result1 == result2
        
        # 캐시 확인
        cached_data = await cache_service.get_product(str(product.id))
        assert cached_data is not None
        assert cached_data["name"] == "Cache Test Product"
        
    async def test_get_product_detail_not_found(
        self,
        product_service_v2
    ):
        """존재하지 않는 상품 조회 테스트"""
        # When/Then: NotFoundError 발생
        with pytest.raises(NotFoundError) as exc_info:
            await product_service_v2.get_product_detail("non-existent-id")
            
        assert "Product not found" in str(exc_info.value)
        
    async def test_search_products_with_filters(
        self,
        product_service_v2,
        integration_helper
    ):
        """필터를 사용한 상품 검색 테스트"""
        # Given: 여러 테스트 상품 생성
        products = []
        for i in range(5):
            product = await integration_helper.create_test_product(
                name=f"Search Test Product {i}",
                category="Electronics" if i < 3 else "Books",
                price=Decimal(f"{100 + i * 10}.00")
            )
            products.append(product)
            
        # When: 카테고리로 검색
        result = await product_service_v2.search_products(
            category="Electronics",
            page=1,
            per_page=10
        )
        
        # Then: 결과 검증
        assert len(result["items"]) == 3
        assert all(
            item["category"] == "Electronics" 
            for item in result["items"]
        )
        assert result["pagination"]["total"] == 3
        
        # When: 가격 범위로 검색
        result2 = await product_service_v2.search_products(
            min_price=Decimal("110.00"),
            max_price=Decimal("130.00"),
            page=1,
            per_page=10
        )
        
        # Then: 가격 범위 검증
        assert len(result2["items"]) == 3
        for item in result2["items"]:
            assert 110.00 <= float(item["price"]) <= 130.00
            
    async def test_create_product_success(
        self,
        product_service_v2,
        test_data_factory
    ):
        """상품 생성 성공 테스트"""
        # Given: 상품 데이터
        product_data = test_data_factory.create_product_data(
            sku="NEW-PRODUCT-001",
            name="New Test Product",
            price="200.00"
        )
        
        # When: 상품 생성
        product = await product_service_v2.create_product(product_data)
        
        # Then: 결과 검증
        assert product.sku == "NEW-PRODUCT-001"
        assert product.name == "New Test Product"
        assert product.price == Decimal("200.00")
        assert product.status == ProductStatus.ACTIVE.value
        
    async def test_create_product_duplicate_sku(
        self,
        product_service_v2,
        integration_helper,
        test_data_factory
    ):
        """중복 SKU로 상품 생성 시 에러 테스트"""
        # Given: 기존 상품
        existing = await integration_helper.create_test_product(
            sku="DUPLICATE-SKU"
        )
        
        # When/Then: 동일 SKU로 생성 시도
        product_data = test_data_factory.create_product_data(
            sku="DUPLICATE-SKU"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await product_service_v2.create_product(product_data)
            
        assert "SKU already exists" in str(exc_info.value)
        
    async def test_update_stock_success(
        self,
        product_service_v2,
        integration_helper
    ):
        """재고 업데이트 성공 테스트"""
        # Given: 초기 재고 10개인 상품
        product = await integration_helper.create_test_product(
            stock_quantity=10
        )
        
        # When: 재고 5개 추가
        updated = await product_service_v2.update_stock(
            str(product.id),
            quantity_change=5,
            reason="restocking"
        )
        
        # Then: 재고 확인
        assert updated.stock_quantity == 15
        
        # When: 재고 3개 차감
        updated2 = await product_service_v2.update_stock(
            str(product.id),
            quantity_change=-3,
            reason="sale"
        )
        
        # Then: 재고 확인
        assert updated2.stock_quantity == 12
        
    async def test_update_stock_insufficient(
        self,
        product_service_v2,
        integration_helper
    ):
        """재고 부족 시 에러 테스트"""
        # Given: 재고 5개인 상품
        product = await integration_helper.create_test_product(
            stock_quantity=5
        )
        
        # When/Then: 10개 차감 시도
        with pytest.raises(ValidationError) as exc_info:
            await product_service_v2.update_stock(
                str(product.id),
                quantity_change=-10,
                reason="oversell"
            )
            
        assert "Insufficient stock" in str(exc_info.value)
        
    async def test_update_stock_auto_status_change(
        self,
        product_service_v2,
        integration_helper
    ):
        """재고에 따른 상태 자동 변경 테스트"""
        # Given: 재고 1개인 상품
        product = await integration_helper.create_test_product(
            stock_quantity=1,
            status=ProductStatus.ACTIVE.value
        )
        
        # When: 재고를 0으로
        updated = await product_service_v2.update_stock(
            str(product.id),
            quantity_change=-1
        )
        
        # Then: 상태가 OUT_OF_STOCK으로 변경
        assert updated.stock_quantity == 0
        assert updated.status == ProductStatus.OUT_OF_STOCK.value
        
        # When: 다시 재고 추가
        updated2 = await product_service_v2.update_stock(
            str(product.id),
            quantity_change=5
        )
        
        # Then: 상태가 ACTIVE로 복원
        assert updated2.stock_quantity == 5
        assert updated2.status == ProductStatus.ACTIVE.value


@pytest.mark.asyncio
@pytest.mark.integration
class TestProductServiceV2Integration:
    """ProductServiceV2 통합 테스트"""
    
    async def test_search_with_pagination_and_cache(
        self,
        product_service_v2,
        integration_helper,
        cache_service
    ):
        """페이지네이션과 캐싱을 포함한 검색 통합 테스트"""
        # Given: 15개의 상품 생성
        for i in range(15):
            await integration_helper.create_test_product(
                name=f"Pagination Test {i}",
                category="TestCategory",
                price=Decimal(f"{100 + i}.00")
            )
            
        # When: 첫 페이지 조회
        page1 = await product_service_v2.search_products(
            category="TestCategory",
            page=1,
            per_page=10
        )
        
        # Then: 페이지네이션 검증
        assert len(page1["items"]) == 10
        assert page1["pagination"]["total"] == 15
        assert page1["pagination"]["pages"] == 2
        
        # When: 두 번째 페이지 조회
        page2 = await product_service_v2.search_products(
            category="TestCategory",
            page=2,
            per_page=10
        )
        
        # Then: 두 번째 페이지 검증
        assert len(page2["items"]) == 5
        
        # 캐시 확인
        cached_page1 = await cache_service.get_category_products(
            "TestCategory", 1
        )
        assert cached_page1 is not None
        assert len(cached_page1["items"]) == 10


@pytest.mark.asyncio
@pytest.mark.performance
class TestProductServiceV2Performance:
    """ProductServiceV2 성능 테스트"""
    
    async def test_bulk_product_search_performance(
        self,
        product_service_v2,
        integration_helper,
        performance_monitor
    ):
        """대량 상품 검색 성능 테스트"""
        # Given: 100개의 상품 생성
        performance_monitor.start("create_products")
        
        for i in range(100):
            await integration_helper.create_test_product(
                name=f"Performance Test {i}",
                category="PerfTest"
            )
            
        performance_monitor.end("create_products")
        
        # When: 검색 수행
        performance_monitor.start("search_products")
        
        result = await product_service_v2.search_products(
            category="PerfTest",
            page=1,
            per_page=50
        )
        
        performance_monitor.end("search_products")
        
        # Then: 성능 검증
        assert len(result["items"]) == 50
        performance_monitor.assert_performance("search_products", 1.0)  # 1초 이내