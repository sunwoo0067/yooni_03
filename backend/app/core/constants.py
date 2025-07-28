"""
Application constants to avoid magic numbers and strings.
매직 넘버와 문자열을 제거하기 위한 상수 정의.
"""
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    """주문 상태 상수"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    """결제 상태 상수"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class ProductStatus(str, Enum):
    """상품 상태 상수"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class MarginRates:
    """마진율 상수"""
    DEFAULT = Decimal("10.0")
    MINIMUM = Decimal("5.0")
    MAXIMUM = Decimal("50.0")
    VIP_DISCOUNT = Decimal("5.0")


class Limits:
    """시스템 제한 상수"""
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 5
    MAX_PRODUCTS_PER_PAGE = 100
    DEFAULT_PAGE_SIZE = 20
    MAX_ORDER_ITEMS = 50
    SESSION_TIMEOUT_MINUTES = 30
    CACHE_TTL_SECONDS = 3600  # 1 hour


class ErrorCodes:
    """에러 코드 상수"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SERVICE_ERROR = "SERVICE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


class CacheKeys:
    """캐시 키 템플릿"""
    PRODUCT_DETAIL = "product:detail:{product_id}"
    USER_SESSION = "user:session:{user_id}"
    ORDER_STATUS = "order:status:{order_id}"
    INVENTORY_COUNT = "inventory:count:{product_id}"
    
    @staticmethod
    def product_detail(product_id: str) -> str:
        return CacheKeys.PRODUCT_DETAIL.format(product_id=product_id)
    
    @staticmethod
    def user_session(user_id: str) -> str:
        return CacheKeys.USER_SESSION.format(user_id=user_id)
    
    @staticmethod
    def order_status(order_id: str) -> str:
        return CacheKeys.ORDER_STATUS.format(order_id=order_id)
    
    @staticmethod
    def inventory_count(product_id: str) -> str:
        return CacheKeys.INVENTORY_COUNT.format(product_id=product_id)