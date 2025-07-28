"""
Input validation utilities for safe data processing.
안전한 데이터 처리를 위한 입력 검증 유틸리티.
"""
import re
from typing import Optional, List, Any
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pydantic import BaseModel, validator, Field

from app.core.exceptions import ValidationError
from app.core.constants import Limits


class SafeValidator:
    """안전한 검증을 위한 정적 메서드 모음"""
    
    @staticmethod
    def validate_id(value: Any, field_name: str = "id") -> str:
        """ID 검증 (UUID 또는 숫자형 문자열)"""
        if not value:
            raise ValidationError(f"{field_name} is required", code="REQUIRED_FIELD")
        
        str_value = str(value).strip()
        if not str_value:
            raise ValidationError(f"{field_name} cannot be empty", code="EMPTY_FIELD")
        
        # UUID 패턴 또는 숫자 ID 허용
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not (re.match(uuid_pattern, str_value.lower()) or str_value.isdigit()):
            raise ValidationError(
                f"Invalid {field_name} format",
                code="INVALID_FORMAT",
                details={"value": str_value}
            )
        
        return str_value
    
    @staticmethod
    def validate_positive_decimal(value: Any, field_name: str = "value") -> Decimal:
        """양수 decimal 검증"""
        try:
            decimal_value = Decimal(str(value))
            if decimal_value <= 0:
                raise ValidationError(
                    f"{field_name} must be positive",
                    code="INVALID_VALUE",
                    details={"value": str(value)}
                )
            return decimal_value
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(
                f"Invalid decimal value for {field_name}",
                code="INVALID_FORMAT",
                details={"value": str(value), "error": str(e)}
            )
    
    @staticmethod
    def validate_email(email: str) -> str:
        """이메일 형식 검증"""
        if not email:
            raise ValidationError("Email is required", code="REQUIRED_FIELD")
        
        email = email.strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError(
                "Invalid email format",
                code="INVALID_EMAIL",
                details={"email": email}
            )
        
        return email
    
    @staticmethod
    def validate_phone(phone: str) -> str:
        """전화번호 형식 검증 (한국 번호 기준)"""
        if not phone:
            raise ValidationError("Phone number is required", code="REQUIRED_FIELD")
        
        # 숫자만 추출
        numbers_only = re.sub(r'[^0-9]', '', phone)
        
        # 한국 전화번호 패턴 (010, 011, 016, 017, 018, 019로 시작하는 10-11자리)
        if not re.match(r'^01[0-9]{8,9}$', numbers_only):
            raise ValidationError(
                "Invalid phone number format",
                code="INVALID_PHONE",
                details={"phone": phone}
            )
        
        return numbers_only
    
    @staticmethod
    def validate_pagination(page: int = 1, size: int = 20) -> tuple[int, int]:
        """페이지네이션 파라미터 검증"""
        try:
            page = int(page)
            size = int(size)
        except (ValueError, TypeError):
            raise ValidationError(
                "Page and size must be integers",
                code="INVALID_TYPE"
            )
        
        if page < 1:
            raise ValidationError("Page must be >= 1", code="INVALID_PAGE")
        
        if size < 1 or size > Limits.MAX_PRODUCTS_PER_PAGE:
            raise ValidationError(
                f"Size must be between 1 and {Limits.MAX_PRODUCTS_PER_PAGE}",
                code="INVALID_SIZE"
            )
        
        return page, size
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """문자열 안전하게 정리"""
        if not value:
            return ""
        
        # 앞뒤 공백 제거
        sanitized = value.strip()
        
        # 길이 제한
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # 위험한 문자 제거 (기본적인 XSS 방지)
        dangerous_chars = ['<', '>', '&', '"', "'", '\x00']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized


# Pydantic 모델을 사용한 검증 (기존 코드와 호환)
class PaginationParams(BaseModel):
    """페이지네이션 파라미터 검증 모델"""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=Limits.MAX_PRODUCTS_PER_PAGE)


class OrderCreateValidator(BaseModel):
    """주문 생성 검증 모델"""
    user_id: str
    items: List[dict] = Field(..., min_items=1, max_items=Limits.MAX_ORDER_ITEMS)
    shipping_address: dict
    payment_method: str
    
    @validator('user_id')
    def validate_user_id(cls, v):
        return SafeValidator.validate_id(v, "user_id")
    
    @validator('items')
    def validate_items(cls, v):
        for item in v:
            if 'product_id' not in item or 'quantity' not in item:
                raise ValueError("Each item must have product_id and quantity")
            if item['quantity'] <= 0:
                raise ValueError("Quantity must be positive")
        return v


class ProductSearchValidator(BaseModel):
    """상품 검색 검증 모델"""
    keyword: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    
    @validator('keyword')
    def sanitize_keyword(cls, v):
        if v:
            return SafeValidator.sanitize_string(v, max_length=100)
        return v
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v and 'min_price' in values and values['min_price']:
            if v < values['min_price']:
                raise ValueError("max_price must be >= min_price")
        return v