"""
상품 가격/재고 알림 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.database import get_db
from app.models.user import User
from app.models.collected_product import CollectedProduct, CollectionStatus
from app.models.collected_product_history import PriceAlert, CollectedProductHistory, ChangeType
from app.services.collection import realtime_stock_monitor
from pydantic import BaseModel, Field


# Request/Response 스키마
class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: str


class PriceAlertCreate(BaseModel):
    """가격 알림 생성 요청"""
    collected_product_id: str = Field(..., description="수집된 상품 ID")
    alert_type: str = Field(..., description="알림 유형: price_drop, price_increase, back_in_stock")
    threshold_percentage: Optional[float] = Field(None, description="가격 변동 임계값 (%)")
    threshold_amount: Optional[float] = Field(None, description="가격 변동 임계값 (금액)")
    target_price: Optional[float] = Field(None, description="목표 가격")
    notification_method: str = Field("email", description="알림 방법: email, push, sms")
    expires_at: Optional[datetime] = Field(None, description="알림 만료일")
    notes: Optional[str] = Field(None, description="메모")


class PriceAlertResponse(BaseModel):
    """가격 알림 응답"""
    id: str
    collected_product_id: str
    product_name: str
    alert_type: str
    threshold_percentage: Optional[float]
    threshold_amount: Optional[float]
    target_price: Optional[float]
    current_price: float
    is_active: bool
    notification_method: str
    last_alerted_at: Optional[datetime]
    alert_count: int
    created_at: datetime
    expires_at: Optional[datetime]


class ProductHistoryResponse(BaseModel):
    """상품 변경 이력 응답"""
    id: str
    change_type: str
    change_timestamp: datetime
    old_price: Optional[float]
    new_price: Optional[float]
    price_change_percentage: Optional[float]
    old_stock_quantity: Optional[int]
    new_stock_quantity: Optional[int]
    old_stock_status: Optional[str]
    new_stock_status: Optional[str]
    changes_summary: Optional[Dict[str, Any]]


router = APIRouter()


@router.post("/alerts", response_model=PriceAlertResponse)
async def create_price_alert(
    alert_data: PriceAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    가격/재고 알림 생성
    
    - price_drop: 가격 하락 알림
    - price_increase: 가격 상승 알림  
    - back_in_stock: 재입고 알림
    """
    # 상품 확인
    product = db.query(CollectedProduct).filter(
        CollectedProduct.id == alert_data.collected_product_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상품을 찾을 수 없습니다"
        )
    
    # 기존 알림 확인
    existing_alert = db.query(PriceAlert).filter(
        and_(
            PriceAlert.user_id == current_user.id,
            PriceAlert.collected_product_id == alert_data.collected_product_id,
            PriceAlert.alert_type == alert_data.alert_type,
            PriceAlert.is_active == True
        )
    ).first()
    
    if existing_alert:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 동일한 알림이 설정되어 있습니다"
        )
    
    # 알림 생성
    new_alert = PriceAlert(
        user_id=current_user.id,
        collected_product_id=alert_data.collected_product_id,
        alert_type=alert_data.alert_type,
        threshold_percentage=alert_data.threshold_percentage,
        threshold_amount=alert_data.threshold_amount,
        target_price=alert_data.target_price,
        notification_method=alert_data.notification_method,
        expires_at=alert_data.expires_at,
        notes=alert_data.notes,
        is_active=True
    )
    
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    # 우선순위 모니터링에 추가
    await realtime_stock_monitor.add_priority_monitoring([product.id])
    
    return PriceAlertResponse(
        id=new_alert.id,
        collected_product_id=new_alert.collected_product_id,
        product_name=product.name,
        alert_type=new_alert.alert_type,
        threshold_percentage=new_alert.threshold_percentage,
        threshold_amount=new_alert.threshold_amount,
        target_price=new_alert.target_price,
        current_price=float(product.price),
        is_active=new_alert.is_active,
        notification_method=new_alert.notification_method,
        last_alerted_at=new_alert.last_alerted_at,
        alert_count=new_alert.alert_count,
        created_at=new_alert.created_at,
        expires_at=new_alert.expires_at
    )


@router.get("/alerts", response_model=List[PriceAlertResponse])
async def get_my_alerts(
    is_active: Optional[bool] = None,
    alert_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 알림 목록 조회"""
    query = db.query(PriceAlert).filter(
        PriceAlert.user_id == current_user.id
    )
    
    if is_active is not None:
        query = query.filter(PriceAlert.is_active == is_active)
    
    if alert_type:
        query = query.filter(PriceAlert.alert_type == alert_type)
    
    alerts = query.all()
    
    # 상품 정보 조회
    product_ids = [alert.collected_product_id for alert in alerts]
    products = db.query(CollectedProduct).filter(
        CollectedProduct.id.in_(product_ids)
    ).all()
    product_map = {p.id: p for p in products}
    
    return [
        PriceAlertResponse(
            id=alert.id,
            collected_product_id=alert.collected_product_id,
            product_name=product_map[alert.collected_product_id].name if alert.collected_product_id in product_map else "Unknown",
            alert_type=alert.alert_type,
            threshold_percentage=alert.threshold_percentage,
            threshold_amount=alert.threshold_amount,
            target_price=alert.target_price,
            current_price=float(product_map[alert.collected_product_id].price) if alert.collected_product_id in product_map else 0,
            is_active=alert.is_active,
            notification_method=alert.notification_method,
            last_alerted_at=alert.last_alerted_at,
            alert_count=alert.alert_count,
            created_at=alert.created_at,
            expires_at=alert.expires_at
        )
        for alert in alerts
    ]


@router.delete("/alerts/{alert_id}", response_model=SuccessResponse)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 삭제"""
    alert = db.query(PriceAlert).filter(
        and_(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == current_user.id
        )
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다"
        )
    
    db.delete(alert)
    db.commit()
    
    return SuccessResponse(message="알림이 삭제되었습니다")


@router.put("/alerts/{alert_id}/toggle", response_model=SuccessResponse)
async def toggle_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 활성화/비활성화 토글"""
    alert = db.query(PriceAlert).filter(
        and_(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == current_user.id
        )
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다"
        )
    
    alert.is_active = not alert.is_active
    db.commit()
    
    return SuccessResponse(
        message=f"알림이 {'활성화' if alert.is_active else '비활성화'}되었습니다"
    )


@router.get("/products/{product_id}/history", response_model=List[ProductHistoryResponse])
async def get_product_history(
    product_id: str,
    change_type: Optional[str] = None,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    상품 변경 이력 조회
    
    - 최근 N일간의 가격/재고 변경 이력
    - 변경 유형별 필터링 가능
    """
    # 상품 확인
    product = db.query(CollectedProduct).filter(
        CollectedProduct.id == product_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상품을 찾을 수 없습니다"
        )
    
    # 변경 이력 조회
    query = db.query(CollectedProductHistory).filter(
        and_(
            CollectedProductHistory.collected_product_id == product_id,
            CollectedProductHistory.change_timestamp >= datetime.utcnow() - timedelta(days=days)
        )
    )
    
    if change_type:
        query = query.filter(
            CollectedProductHistory.change_type == ChangeType[change_type.upper()]
        )
    
    history = query.order_by(
        CollectedProductHistory.change_timestamp.desc()
    ).limit(100).all()
    
    return [
        ProductHistoryResponse(
            id=h.id,
            change_type=h.change_type.value,
            change_timestamp=h.change_timestamp,
            old_price=float(h.old_price) if h.old_price else None,
            new_price=float(h.new_price) if h.new_price else None,
            price_change_percentage=float(h.price_change_percentage) if h.price_change_percentage else None,
            old_stock_quantity=h.old_stock_quantity,
            new_stock_quantity=h.new_stock_quantity,
            old_stock_status=h.old_stock_status,
            new_stock_status=h.new_stock_status,
            changes_summary=h.changes_summary
        )
        for h in history
    ]


@router.get("/monitoring/stats")
async def get_monitoring_stats(
    current_user: User = Depends(get_current_user)
):
    """실시간 모니터링 통계"""
    stats = await realtime_stock_monitor.get_monitoring_stats()
    return stats


@router.get("/changes/recent")
async def get_recent_changes(
    hours: int = 24,
    change_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    최근 변경사항 조회
    
    - 최근 N시간 동안의 주요 변경사항
    - 가격 5% 이상 변동 또는 재입고된 상품
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(CollectedProductHistory).filter(
        CollectedProductHistory.change_timestamp >= cutoff_time
    )
    
    if change_type:
        query = query.filter(
            CollectedProductHistory.change_type == ChangeType[change_type.upper()]
        )
    
    # 중요한 변경사항만 필터링
    significant_changes = []
    
    for history in query.limit(200).all():
        # 중요한 가격 변경 (5% 이상)
        if (history.change_type == ChangeType.PRICE_CHANGE and 
            history.price_change_percentage and 
            abs(history.price_change_percentage) >= 5):
            significant_changes.append(history)
        
        # 재입고
        elif (history.change_type == ChangeType.STOCK_CHANGE and
              history.old_stock_status == "out_of_stock" and
              history.new_stock_status == "available"):
            significant_changes.append(history)
    
    # 상품 정보 조회
    product_ids = list(set(h.collected_product_id for h in significant_changes))
    products = db.query(CollectedProduct).filter(
        CollectedProduct.id.in_(product_ids)
    ).all()
    product_map = {p.id: p for p in products}
    
    return {
        'changes': [
            {
                'product_id': h.collected_product_id,
                'product_name': product_map[h.collected_product_id].name if h.collected_product_id in product_map else "Unknown",
                'change_type': h.change_type.value,
                'timestamp': h.change_timestamp.isoformat(),
                'details': {
                    'old_price': float(h.old_price) if h.old_price else None,
                    'new_price': float(h.new_price) if h.new_price else None,
                    'price_change_pct': float(h.price_change_percentage) if h.price_change_percentage else None,
                    'old_stock': h.old_stock_status,
                    'new_stock': h.new_stock_status
                }
            }
            for h in significant_changes[:50]  # 최대 50개
        ],
        'total_changes': len(significant_changes),
        'period_hours': hours
    }