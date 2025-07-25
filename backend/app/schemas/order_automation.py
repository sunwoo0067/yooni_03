"""
Order automation schemas
주문 처리 자동화 스키마
"""
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class OrderProcessingRequest(BaseModel):
    """주문 처리 요청"""
    platform_data: Dict[str, Any] = Field(..., description="플랫폼 주문 데이터")
    account: Dict[str, Any] = Field(..., description="계정 정보")
    platform: str = Field(..., description="플랫폼명")
    priority: Optional[str] = Field("normal", description="처리 우선순위")
    
    class Config:
        schema_extra = {
            "example": {
                "platform_data": {
                    "orderId": "ORDER123456",
                    "orderDate": "2024-01-01T10:00:00Z",
                    "customerName": "김철수",
                    "totalAmount": 50000
                },
                "account": {
                    "platform_account_id": "account_123",
                    "credentials": {}
                },
                "platform": "coupang",
                "priority": "high"
            }
        }


class OrderProcessingResponse(BaseModel):
    """주문 처리 응답"""
    success: bool
    process_id: Optional[str] = None
    order_id: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    stages: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "process_id": "order_process_20240101_100000",
                "order_id": "order_uuid_123",
                "processing_time_seconds": 45.2,
                "stages": {
                    "monitoring": {"success": True},
                    "auto_ordering": [{"success": True}],
                    "tracking_setup": [{"success": True}],
                    "settlement": {"success": True}
                },
                "summary": {
                    "total_items": 3,
                    "successful_orders": 3,
                    "failed_orders": 0,
                    "tracking_enabled": 3,
                    "settlement_ready": True
                }
            }
        }


class SystemStatusResponse(BaseModel):
    """시스템 상태 응답"""
    system_running: bool
    uptime_seconds: Optional[int] = None
    uptime_formatted: Optional[str] = None
    modules: Optional[Dict[str, Dict[str, Any]]] = None
    statistics: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    last_health_check: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "system_running": True,
                "uptime_seconds": 3600,
                "uptime_formatted": "01:00:00",
                "modules": {
                    "order_monitor": {
                        "healthy": True,
                        "active": True,
                        "tasks_count": 4
                    }
                },
                "statistics": {
                    "orders_processed": 150,
                    "automatic_orders_placed": 147,
                    "tracking_updates": 89,
                    "settlements_generated": 120
                }
            }
        }


class SettlementRequest(BaseModel):
    """정산 요청"""
    order_id: str = Field(..., description="주문 ID")
    force_recalculate: Optional[bool] = Field(False, description="강제 재계산")
    
    class Config:
        schema_extra = {
            "example": {
                "order_id": "order_uuid_123",
                "force_recalculate": False
            }
        }


class SettlementResponse(BaseModel):
    """정산 응답"""
    success: bool
    settlement_id: Optional[str] = None
    order_id: Optional[str] = None
    gross_revenue: Optional[float] = None
    total_costs: Optional[float] = None
    net_profit: Optional[float] = None
    profit_margin: Optional[float] = None
    status: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "settlement_id": "settlement_uuid_123",
                "order_id": "order_uuid_123",
                "gross_revenue": 45000.0,
                "total_costs": 30000.0,
                "net_profit": 15000.0,
                "profit_margin": 33.33,
                "status": "calculated"
            }
        }


class ExceptionTypeEnum(str, Enum):
    """예외 유형"""
    ORDER_CANCELLATION = "order_cancellation"
    EXCHANGE_REQUEST = "exchange_request"
    RETURN_REQUEST = "return_request"
    STOCKOUT = "stockout"
    PRICE_CHANGE = "price_change"
    DELIVERY_ISSUE = "delivery_issue"
    SYSTEM_ERROR = "system_error"


class ExceptionHandlingRequest(BaseModel):
    """예외 처리 요청"""
    exception_type: ExceptionTypeEnum = Field(..., description="예외 유형")
    order_id: Optional[str] = Field(None, description="주문 ID")
    product_sku: Optional[str] = Field(None, description="상품 SKU")
    wholesaler_id: Optional[str] = Field(None, description="도매업체 ID")
    reason: Optional[str] = Field(None, description="사유")
    items: Optional[List[Dict[str, Any]]] = Field(None, description="관련 아이템")
    context: Optional[Dict[str, Any]] = Field(None, description="추가 컨텍스트")
    
    @validator('order_id')
    def validate_order_id(cls, v, values):
        exception_type = values.get('exception_type')
        if exception_type in [ExceptionTypeEnum.ORDER_CANCELLATION, 
                            ExceptionTypeEnum.EXCHANGE_REQUEST, 
                            ExceptionTypeEnum.RETURN_REQUEST] and not v:
            raise ValueError(f"{exception_type}에는 order_id가 필수입니다")
        return v
    
    @validator('product_sku')
    def validate_product_sku(cls, v, values):
        exception_type = values.get('exception_type')
        if exception_type == ExceptionTypeEnum.STOCKOUT and not v:
            raise ValueError("stockout에는 product_sku가 필수입니다")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "exception_type": "order_cancellation",
                "order_id": "order_uuid_123",
                "reason": "고객 요청에 의한 취소"
            }
        }


class ExceptionHandlingResponse(BaseModel):
    """예외 처리 응답"""
    success: bool
    exception_type: Optional[str] = None
    action_taken: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    requires_manual_intervention: Optional[bool] = None
    customer_notified: Optional[bool] = None
    error: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "exception_type": "order_cancellation",
                "action_taken": "automatic_cancellation",
                "result": {
                    "order_cancelled": True,
                    "refund_processed": True,
                    "wholesale_orders_cancelled": 2
                },
                "customer_notified": True
            }
        }


class TrackingUpdateRequest(BaseModel):
    """배송 추적 업데이트 요청"""
    tracking_number: str = Field(..., description="송장번호")
    carrier: Optional[str] = Field(None, description="택배사")
    force_update: Optional[bool] = Field(False, description="강제 업데이트")
    
    class Config:
        schema_extra = {
            "example": {
                "tracking_number": "1234567890",
                "carrier": "cj",
                "force_update": False
            }
        }


class InventorySyncRequest(BaseModel):
    """재고 동기화 요청"""
    wholesaler_ids: Optional[List[str]] = Field(None, description="특정 도매업체 ID 목록")
    product_skus: Optional[List[str]] = Field(None, description="특정 상품 SKU 목록")
    force_sync: Optional[bool] = Field(False, description="강제 동기화")
    
    class Config:
        schema_extra = {
            "example": {
                "wholesaler_ids": ["wholesaler_1", "wholesaler_2"],
                "product_skus": ["SKU001", "SKU002"],
                "force_sync": False
            }
        }


class AlternativeSearchRequest(BaseModel):
    """대체 상품 검색 요청"""
    product_sku: str = Field(..., description="원본 상품 SKU")
    order_id: Optional[str] = Field(None, description="주문 ID")
    search_strategies: Optional[List[str]] = Field(None, description="검색 전략")
    min_similarity_score: Optional[float] = Field(0.7, description="최소 유사도 점수")
    
    class Config:
        schema_extra = {
            "example": {
                "product_sku": "SKU001",
                "order_id": "order_uuid_123",
                "search_strategies": ["same_brand_similar_model", "similar_features"],
                "min_similarity_score": 0.8
            }
        }


class WebSocketMessage(BaseModel):
    """웹소켓 메시지"""
    type: str = Field(..., description="메시지 타입")
    channel: str = Field(..., description="채널명")
    timestamp: str = Field(..., description="타임스탬프")
    data: Dict[str, Any] = Field(..., description="메시지 데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "order_received",
                "channel": "order_monitoring",
                "timestamp": "2024-01-01T10:00:00Z",
                "data": {
                    "order_id": "order_uuid_123",
                    "platform": "coupang",
                    "total_amount": 50000
                }
            }
        }


class NotificationRequest(BaseModel):
    """알림 요청"""
    notification_type: str = Field(..., description="알림 유형")
    recipient: str = Field(..., description="수신자")
    title: str = Field(..., description="제목")
    message: str = Field(..., description="메시지 내용")
    data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터")
    channels: Optional[List[str]] = Field(["email"], description="알림 채널")
    priority: Optional[str] = Field("normal", description="우선순위")
    
    class Config:
        schema_extra = {
            "example": {
                "notification_type": "order_exception",
                "recipient": "admin@example.com",
                "title": "주문 처리 예외 발생",
                "message": "주문 ORDER123에서 재고 부족 예외가 발생했습니다.",
                "data": {
                    "order_id": "ORDER123",
                    "exception_type": "stockout"
                },
                "channels": ["email", "slack"],
                "priority": "high"
            }
        }


class ProfitReportRequest(BaseModel):
    """수익 보고서 요청"""
    start_date: datetime = Field(..., description="시작일")
    end_date: datetime = Field(..., description="종료일")
    group_by: Optional[str] = Field("day", description="그룹핑 기준")
    include_details: Optional[bool] = Field(True, description="상세 정보 포함")
    platforms: Optional[List[str]] = Field(None, description="특정 플랫폼 필터")
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "group_by": "week",
                "include_details": True,
                "platforms": ["coupang", "naver"]
            }
        }


class AutomationRuleRequest(BaseModel):
    """자동화 규칙 요청"""
    rule_name: str = Field(..., description="규칙명")
    rule_type: str = Field(..., description="규칙 유형")
    conditions: Dict[str, Any] = Field(..., description="적용 조건")
    actions: Dict[str, Any] = Field(..., description="실행 액션")
    priority: Optional[int] = Field(0, description="우선순위")
    is_active: Optional[bool] = Field(True, description="활성화 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "rule_name": "고마진 상품 우선 발주",
                "rule_type": "auto_order_priority",
                "conditions": {
                    "min_margin_rate": 20,
                    "product_categories": ["electronics", "fashion"]
                },
                "actions": {
                    "priority_boost": 10,
                    "auto_order_enabled": True
                },
                "priority": 5,
                "is_active": True
            }
        }


class PerformanceMetrics(BaseModel):
    """성능 메트릭"""
    orders_per_hour: Optional[float] = None
    average_processing_time: Optional[float] = None
    success_rate: Optional[float] = None
    error_rate: Optional[float] = None
    system_load: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "orders_per_hour": 25.5,
                "average_processing_time": 45.2,
                "success_rate": 98.5,
                "error_rate": 1.5,
                "system_load": {
                    "cpu_percent": 35.2,
                    "memory_percent": 68.5,
                    "active_tasks": 12
                }
            }
        }