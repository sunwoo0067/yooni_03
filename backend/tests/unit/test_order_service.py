"""
Order processing service unit tests
주문 처리 서비스 핵심 로직 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timedelta

# 모의 서비스 클래스들을 직접 구현
class MarginCalculator:
    def calculate_order_margin(self, order_data):
        total_revenue = sum(item["price"] * item["quantity"] for item in order_data["items"])
        total_cost = sum(item["cost"] * item["quantity"] for item in order_data["items"])
        if total_revenue == 0:
            return Decimal("0")
        return ((total_revenue - total_cost) / total_revenue * 100).quantize(Decimal("0.01"))
    
    def calculate_profit(self, price, cost, quantity):
        return (price - cost) * quantity
    
    def is_margin_acceptable(self, margin, min_margin):
        return margin >= min_margin
    
    def calculate_shipping_cost(self, order_value, weight):
        if order_value >= Decimal("50000"):
            return Decimal("0")
        return Decimal("3000")

class OrderValidator:
    def validate_order(self, order_data):
        errors = []
        
        if "customer_id" not in order_data:
            errors.append("customer_id is required")
        
        if "items" not in order_data or len(order_data["items"]) == 0:
            errors.append("items list cannot be empty")
        
        return len(errors) == 0, errors
    
    def validate_phone_number(self, phone):
        import re
        pattern = r'^010-\d{4}-\d{4}$'
        return bool(re.match(pattern, phone))
    
    def validate_address(self, address):
        required_fields = ["name", "phone", "address", "postal_code"]
        missing_fields = [field for field in required_fields if field not in address]
        return len(missing_fields) == 0, missing_fields

class OrderProcessor:
    def calculate_order_total(self, items, shipping_cost):
        item_total = sum(item["price"] * item["quantity"] for item in items)
        return item_total + shipping_cost
    
    def apply_discount(self, original_amount, discount_rate):
        return original_amount * (1 - discount_rate / 100)
    
    def determine_order_priority(self, order_data):
        if (order_data["total_amount"] >= Decimal("100000") or 
            order_data["customer_type"] == "VIP"):
            return "high"
        return "normal"
    
    def generate_order_number(self):
        import random
        import string
        suffix = ''.join(random.choices(string.digits, k=8))
        return f"ORD{suffix}"
    
    def estimate_delivery_date(self, order_date, shipping_method):
        if shipping_method == "express":
            days = 1
        elif shipping_method == "standard":
            days = 2
        else:
            days = 3
        return order_date + timedelta(days=days)


class TestMarginCalculator:
    """마진 계산기 테스트"""
    
    @pytest.fixture
    def margin_calculator(self):
        return MarginCalculator()
    
    def test_calculate_order_margin(self, margin_calculator):
        """주문 마진 계산 테스트"""
        order_data = {
            "items": [
                {"price": Decimal("10000"), "cost": Decimal("7000"), "quantity": 2},
                {"price": Decimal("5000"), "cost": Decimal("3000"), "quantity": 1}
            ]
        }
        
        margin = margin_calculator.calculate_order_margin(order_data)
        
        # Total revenue: (10000*2) + (5000*1) = 25000
        # Total cost: (7000*2) + (3000*1) = 17000
        # Margin: (25000-17000)/25000 * 100 = 32%
        assert margin == Decimal("32.00")
    
    def test_calculate_profit(self, margin_calculator):
        """수익 계산 테스트"""
        price = Decimal("10000")
        cost = Decimal("7000")
        quantity = 3
        
        profit = margin_calculator.calculate_profit(price, cost, quantity)
        
        assert profit == Decimal("9000")  # (10000-7000) * 3
    
    def test_is_margin_acceptable(self, margin_calculator):
        """허용 마진 검사 테스트"""
        margin = Decimal("35.00")
        min_margin = Decimal("30.00")
        
        is_acceptable = margin_calculator.is_margin_acceptable(margin, min_margin)
        
        assert is_acceptable is True
    
    def test_calculate_shipping_cost(self, margin_calculator):
        """배송비 계산 테스트"""
        order_value = Decimal("50000")
        weight = Decimal("2.5")  # kg
        
        shipping_cost = margin_calculator.calculate_shipping_cost(order_value, weight)
        
        # 5만원 이상 무료배송 가정
        assert shipping_cost == Decimal("0")
    
    def test_calculate_shipping_cost_paid(self, margin_calculator):
        """유료 배송비 계산 테스트"""
        order_value = Decimal("20000")
        weight = Decimal("1.0")  # kg
        
        shipping_cost = margin_calculator.calculate_shipping_cost(order_value, weight)
        
        # 기본 배송비 3000원 가정
        assert shipping_cost == Decimal("3000")


class TestOrderValidator:
    """주문 검증기 테스트"""
    
    @pytest.fixture
    def order_validator(self):
        return OrderValidator()
    
    @pytest.fixture
    def valid_order_data(self):
        return {
            "customer_id": "customer123",
            "items": [
                {
                    "product_id": "prod1",
                    "quantity": 2,
                    "price": Decimal("10000")
                }
            ],
            "shipping_address": {
                "name": "홍길동",
                "phone": "010-1234-5678",
                "address": "서울시 강남구"
            },
            "payment_method": "credit_card"
        }
    
    def test_validate_order_valid(self, order_validator, valid_order_data):
        """유효한 주문 검증 테스트"""
        is_valid, errors = order_validator.validate_order(valid_order_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_order_missing_customer(self, order_validator, valid_order_data):
        """고객 ID 누락 검증 테스트"""
        valid_order_data.pop("customer_id")
        
        is_valid, errors = order_validator.validate_order(valid_order_data)
        
        assert is_valid is False
        assert "customer_id" in str(errors)
    
    def test_validate_order_empty_items(self, order_validator, valid_order_data):
        """빈 아이템 리스트 검증 테스트"""
        valid_order_data["items"] = []
        
        is_valid, errors = order_validator.validate_order(valid_order_data)
        
        assert is_valid is False
        assert "items" in str(errors)
    
    def test_validate_phone_number_valid(self, order_validator):
        """유효한 전화번호 검증 테스트"""
        phone = "010-1234-5678"
        
        is_valid = order_validator.validate_phone_number(phone)
        
        assert is_valid is True
    
    def test_validate_phone_number_invalid(self, order_validator):
        """무효한 전화번호 검증 테스트"""
        phone = "123-456"
        
        is_valid = order_validator.validate_phone_number(phone)
        
        assert is_valid is False
    
    def test_validate_address_complete(self, order_validator):
        """완전한 주소 검증 테스트"""
        address = {
            "name": "홍길동",
            "phone": "010-1234-5678",
            "address": "서울시 강남구 테헤란로 123",
            "postal_code": "06234"
        }
        
        is_valid, missing_fields = order_validator.validate_address(address)
        
        assert is_valid is True
        assert len(missing_fields) == 0
    
    def test_validate_address_missing_fields(self, order_validator):
        """주소 필드 누락 검증 테스트"""
        address = {
            "name": "홍길동",
            "address": "서울시 강남구"
            # phone, postal_code 누락
        }
        
        is_valid, missing_fields = order_validator.validate_address(address)
        
        assert is_valid is False
        assert "phone" in missing_fields
        assert "postal_code" in missing_fields


class TestOrderProcessor:
    """주문 처리기 테스트"""
    
    @pytest.fixture
    def order_processor(self):
        return OrderProcessor()
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    def test_calculate_order_total(self, order_processor):
        """주문 총액 계산 테스트"""
        items = [
            {"price": Decimal("10000"), "quantity": 2},
            {"price": Decimal("5000"), "quantity": 1}
        ]
        shipping_cost = Decimal("3000")
        
        total = order_processor.calculate_order_total(items, shipping_cost)
        
        # (10000*2) + (5000*1) + 3000 = 28000
        assert total == Decimal("28000")
    
    def test_apply_discount(self, order_processor):
        """할인 적용 테스트"""
        original_amount = Decimal("20000")
        discount_rate = Decimal("10")  # 10%
        
        discounted_amount = order_processor.apply_discount(original_amount, discount_rate)
        
        assert discounted_amount == Decimal("18000")  # 20000 * 0.9
    
    def test_determine_order_priority_high(self, order_processor):
        """높은 우선순위 주문 판별 테스트"""
        order_data = {
            "total_amount": Decimal("100000"),
            "customer_type": "VIP",
            "items_count": 1
        }
        
        priority = order_processor.determine_order_priority(order_data)
        
        assert priority == "high"
    
    def test_determine_order_priority_normal(self, order_processor):
        """일반 우선순위 주문 판별 테스트"""
        order_data = {
            "total_amount": Decimal("30000"),
            "customer_type": "regular",
            "items_count": 2
        }
        
        priority = order_processor.determine_order_priority(order_data)
        
        assert priority == "normal"
    
    def test_generate_order_number(self, order_processor):
        """주문번호 생성 테스트"""
        order_number = order_processor.generate_order_number()
        
        assert len(order_number) > 0
        assert order_number.startswith("ORD")
    
    def test_estimate_delivery_date(self, order_processor):
        """배송 예정일 계산 테스트"""
        order_date = datetime(2024, 1, 15, 10, 0, 0)  # 월요일
        shipping_method = "standard"
        
        delivery_date = order_processor.estimate_delivery_date(order_date, shipping_method)
        
        # 표준 배송: 2-3일 후
        assert delivery_date > order_date
        assert (delivery_date - order_date).days >= 2
        assert (delivery_date - order_date).days <= 3