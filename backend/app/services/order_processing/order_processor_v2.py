"""
Improved OrderProcessor with safe refactoring patterns.
안전한 리팩토링 패턴이 적용된 개선된 OrderProcessor.

이 파일은 기존 order_processor.py와 병행하여 사용할 수 있으며,
점진적으로 기존 코드를 대체할 수 있습니다.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus, Limits, MarginRates
from app.core.exceptions import (
    NotFoundError, 
    ValidationError, 
    ServiceException
)
from app.core.database_utils import safe_transaction, safe_update
from app.core.logging_utils import get_logger, log_execution_time, LogContext
from app.core.validators import SafeValidator
from app.services.base_service import BaseService
from app.models.order_core import Order
from app.models.product import Product


class OrderProcessorV2(BaseService[Order]):
    """
    개선된 주문 처리 서비스.
    기존 OrderProcessor와 동일한 인터페이스를 제공하면서
    안전한 패턴들이 적용되었습니다.
    """
    
    def __init__(self, db: Session):
        super().__init__(db, Order)
        self.logger = get_logger(self.__class__.__name__)
        
    @log_execution_time("validate_order")
    def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """주문 데이터 검증"""
        try:
            # 필수 필드 검증
            user_id = SafeValidator.validate_id(
                order_data.get("user_id"), 
                "user_id"
            )
            
            # 주문 항목 검증
            items = order_data.get("items", [])
            if not items:
                raise ValidationError("Order must have at least one item")
                
            if len(items) > Limits.MAX_ORDER_ITEMS:
                raise ValidationError(
                    f"Order cannot have more than {Limits.MAX_ORDER_ITEMS} items"
                )
            
            # 각 항목 검증
            validated_items = []
            for item in items:
                product_id = SafeValidator.validate_id(
                    item.get("product_id"), 
                    "product_id"
                )
                quantity = int(item.get("quantity", 0))
                
                if quantity <= 0:
                    raise ValidationError(
                        f"Invalid quantity for product {product_id}"
                    )
                
                validated_items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "price": SafeValidator.validate_positive_decimal(
                        item.get("price", 0),
                        "price"
                    ) if "price" in item else None
                })
            
            return {
                "user_id": user_id,
                "items": validated_items,
                "status": OrderStatus.PENDING,
                "created_at": datetime.utcnow()
            }
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error("Order validation failed", error=e)
            raise ServiceException(f"Order validation failed: {str(e)}")
    
    def calculate_order_total(
        self, 
        items: List[Dict[str, Any]], 
        apply_margin: bool = True
    ) -> Dict[str, Decimal]:
        """주문 총액 계산"""
        with LogContext(
            self.logger, 
            operation="calculate_order_total",
            item_count=len(items)
        ):
            subtotal = Decimal("0")
            margin_total = Decimal("0")
            
            for item in items:
                quantity = Decimal(str(item["quantity"]))
                price = item.get("price")
                
                if not price:
                    # 가격이 없으면 DB에서 조회
                    product = self.db.query(Product).filter(
                        Product.id == item["product_id"]
                    ).first()
                    
                    if not product:
                        raise NotFoundError("Product", item["product_id"])
                    
                    price = product.price
                
                item_total = price * quantity
                subtotal += item_total
                
                if apply_margin:
                    # 상수 사용
                    margin = item_total * (MarginRates.DEFAULT / 100)
                    margin_total += margin
            
            total = subtotal + margin_total
            
            return {
                "subtotal": subtotal,
                "margin": margin_total,
                "total": total,
                "margin_rate": MarginRates.DEFAULT if apply_margin else Decimal("0")
            }
    
    @log_execution_time("create_order")
    def create_order(self, order_data: Dict[str, Any]) -> Order:
        """새 주문 생성"""
        # 검증
        validated_data = self.validate_order(order_data)
        
        # 트랜잭션 내에서 주문 생성
        with safe_transaction(self.db, "create_order") as session:
            # 총액 계산
            totals = self.calculate_order_total(validated_data["items"])
            
            # 주문 생성
            order = Order(
                user_id=validated_data["user_id"],
                status=OrderStatus.PENDING.value,
                total_amount=totals["total"],
                subtotal=totals["subtotal"],
                margin_amount=totals["margin"],
                created_at=datetime.utcnow()
            )
            
            session.add(order)
            session.flush()  # ID 생성을 위해
            
            # 주문 항목 추가 (별도 메서드로 분리 가능)
            self._create_order_items(session, order.id, validated_data["items"])
            
            self.logger.info(
                "Order created successfully",
                order_id=order.id,
                user_id=order.user_id,
                total_amount=float(order.total_amount)
            )
            
            return order
    
    def _create_order_items(
        self, 
        session: Session, 
        order_id: str, 
        items: List[Dict[str, Any]]
    ) -> None:
        """주문 항목 생성 (내부 메서드)"""
        # OrderItem 모델이 있다고 가정
        # 실제 구현은 프로젝트 구조에 맞게 조정
        pass
    
    def update_order_status(
        self, 
        order_id: str, 
        new_status: OrderStatus,
        reason: Optional[str] = None
    ) -> Order:
        """주문 상태 업데이트"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise self.handle_not_found("Order", order_id)
        
        # 상태 전환 검증 (비즈니스 로직)
        if not self._is_valid_status_transition(order.status, new_status):
            raise ValidationError(
                f"Cannot transition from {order.status} to {new_status.value}"
            )
        
        # 안전한 업데이트
        updates = {
            "status": new_status.value,
            "updated_at": datetime.utcnow()
        }
        
        if reason:
            updates["status_reason"] = reason
        
        updated_order = safe_update(
            self.db,
            order,
            updates,
            allowed_fields=["status", "updated_at", "status_reason"]
        )
        
        self.logger.info(
            "Order status updated",
            order_id=order_id,
            old_status=order.status,
            new_status=new_status.value,
            reason=reason
        )
        
        return updated_order
    
    def _is_valid_status_transition(
        self, 
        current_status: str, 
        new_status: OrderStatus
    ) -> bool:
        """상태 전환 가능 여부 확인"""
        # 상태 전환 규칙 정의
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.PROCESSING, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.PROCESSING: [
                OrderStatus.CONFIRMED, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.CONFIRMED: [
                OrderStatus.SHIPPED, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.SHIPPED: [
                OrderStatus.DELIVERED, 
                OrderStatus.FAILED
            ],
            OrderStatus.DELIVERED: [
                OrderStatus.REFUNDED
            ],
            OrderStatus.CANCELLED: [],
            OrderStatus.REFUNDED: [],
            OrderStatus.FAILED: [
                OrderStatus.REFUNDED
            ]
        }
        
        current = OrderStatus(current_status)
        return new_status in valid_transitions.get(current, [])


# 기존 코드와의 호환성을 위한 팩토리 함수
def get_order_processor(db: Session, use_v2: bool = False) -> Any:
    """
    OrderProcessor 인스턴스 생성.
    
    Args:
        db: Database session
        use_v2: True면 개선된 버전 사용
    
    Returns:
        OrderProcessor 또는 OrderProcessorV2 인스턴스
    """
    if use_v2:
        return OrderProcessorV2(db)
    else:
        # 기존 OrderProcessor import
        from app.services.order_processing.order_processor import OrderProcessor
        return OrderProcessor(db)