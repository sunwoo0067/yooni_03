"""
Product service unit tests
상품 서비스 핵심 로직 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime

# 모의 상품 서비스 클래스
class ProductService:
    def calculate_margin(self, price, cost):
        if price == 0:
            return Decimal("0")
        return ((price - cost) / price * 100).quantize(Decimal("0.01"))
    
    def validate_product_data(self, data):
        errors = []
        
        if "name" not in data or not data["name"]:
            errors.append("name is required")
        
        if "price" in data and data["price"] < 0:
            errors.append("price must be positive")
        
        return len(errors) == 0, errors
    
    def format_product_name(self, name):
        return name.strip()
    
    def extract_keywords_from_name(self, name):
        # 간단한 키워드 추출
        words = name.split()
        return [word for word in words if len(word) > 1]
    
    def calculate_suggested_price(self, cost, target_margin):
        return cost / (1 - Decimal(str(target_margin)) / 100)
    
    def is_profitable(self, price, cost, min_margin):
        margin = self.calculate_margin(price, cost)
        return margin >= min_margin
    
    def process_raw_product_data(self, raw_data):
        processed = {}
        processed["name"] = self.format_product_name(raw_data["name"])
        processed["price"] = Decimal(str(raw_data["price"]))
        processed["cost"] = Decimal(str(raw_data["cost"]))
        processed["margin"] = self.calculate_margin(processed["price"], processed["cost"])
        processed["keywords"] = self.extract_keywords_from_name(processed["name"])
        return processed


class TestProductService:
    """상품 서비스 테스트"""
    
    @pytest.fixture
    def product_service(self):
        return ProductService()
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_product_data(self):
        return {
            "name": "테스트 상품",
            "price": Decimal("10000"),
            "cost": Decimal("7000"),
            "description": "테스트용 상품입니다",
            "category": "테스트카테고리"
        }
    
    def test_calculate_margin(self, product_service):
        """마진 계산 테스트"""
        price = Decimal("10000")
        cost = Decimal("7000")
        
        margin = product_service.calculate_margin(price, cost)
        
        assert margin == Decimal("30.00")  # (10000-7000)/10000 * 100
    
    def test_calculate_margin_zero_price(self, product_service):
        """가격이 0일 때 마진 계산 테스트"""
        price = Decimal("0")
        cost = Decimal("7000")
        
        margin = product_service.calculate_margin(price, cost)
        
        assert margin == Decimal("0")
    
    def test_validate_product_data_valid(self, product_service, sample_product_data):
        """유효한 상품 데이터 검증 테스트"""
        is_valid, errors = product_service.validate_product_data(sample_product_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_product_data_missing_name(self, product_service, sample_product_data):
        """상품명 누락 시 검증 테스트"""
        sample_product_data.pop("name")
        
        is_valid, errors = product_service.validate_product_data(sample_product_data)
        
        assert is_valid is False
        assert "name" in str(errors)
    
    def test_validate_product_data_negative_price(self, product_service, sample_product_data):
        """음수 가격 검증 테스트"""
        sample_product_data["price"] = Decimal("-1000")
        
        is_valid, errors = product_service.validate_product_data(sample_product_data)
        
        assert is_valid is False
        assert "price" in str(errors)
    
    def test_format_product_name(self, product_service):
        """상품명 포맷팅 테스트"""
        raw_name = "  테스트 상품   "
        
        formatted_name = product_service.format_product_name(raw_name)
        
        assert formatted_name == "테스트 상품"
    
    def test_extract_keywords_from_name(self, product_service):
        """상품명에서 키워드 추출 테스트"""
        product_name = "남성 반팔 티셔츠 100% 면 블랙"
        
        keywords = product_service.extract_keywords_from_name(product_name)
        
        assert "남성" in keywords
        assert "반팔" in keywords
        assert "티셔츠" in keywords
        assert "100%" in keywords
        assert "블랙" in keywords
    
    def test_calculate_suggested_price(self, product_service):
        """추천 가격 계산 테스트"""
        cost = Decimal("7000")
        target_margin = 30  # 30%
        
        suggested_price = product_service.calculate_suggested_price(cost, target_margin)
        
        # cost / (1 - margin/100) = 7000 / 0.7 = 10000
        assert suggested_price == Decimal("10000.00")
    
    def test_is_profitable(self, product_service):
        """수익성 검사 테스트"""
        price = Decimal("10000")
        cost = Decimal("7000")
        min_margin = 25
        
        is_profitable = product_service.is_profitable(price, cost, min_margin)
        
        assert is_profitable is True
    
    def test_is_not_profitable(self, product_service):
        """비수익성 검사 테스트"""
        price = Decimal("10000")
        cost = Decimal("8500")  # 15% 마진
        min_margin = 25
        
        is_profitable = product_service.is_profitable(price, cost, min_margin)
        
        assert is_profitable is False


class TestProductServiceIntegration:
    """상품 서비스 통합 테스트"""
    
    @pytest.fixture
    def product_service(self):
        return ProductService()
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    def test_product_workflow(self, product_service):
        """상품 처리 워크플로우 테스트"""
        # Given
        raw_data = {
            "name": "  남성 반팔 티셔츠  ",
            "price": "10000",
            "cost": "7000",
            "description": "100% 면 소재"
        }
        
        # When
        processed_data = product_service.process_raw_product_data(raw_data)
        
        # Then
        assert processed_data["name"] == "남성 반팔 티셔츠"
        assert processed_data["price"] == Decimal("10000")
        assert processed_data["cost"] == Decimal("7000")
        assert processed_data["margin"] == Decimal("30.00")
        assert "keywords" in processed_data
        assert len(processed_data["keywords"]) > 0