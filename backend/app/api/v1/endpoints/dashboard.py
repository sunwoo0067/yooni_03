"""
대시보드 API 엔드포인트
실시간 대시보드 데이터 및 분석 제공
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.dashboard.dashboard_service import DashboardService
from app.services.dashboard.analytics_service import AnalyticsService
from app.services.dashboard.notification_service import NotificationService
from app.services.dashboard.report_service import ReportService
from app.services.realtime.websocket_manager import connection_manager
from app.services.realtime.event_processor import event_processor, EventType
from app.core.logging import logger

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# 서비스 인스턴스
dashboard_service = DashboardService()
analytics_service = AnalyticsService()
notification_service = NotificationService()
report_service = ReportService()


# Request/Response 모델
class DateRangeQuery(BaseModel):
    """날짜 범위 쿼리"""
    start_date: Optional[datetime] = Field(None, description="시작 날짜")
    end_date: Optional[datetime] = Field(None, description="종료 날짜")
    
    def to_dict(self) -> Optional[Dict[str, datetime]]:
        if self.start_date and self.end_date:
            return {"start": self.start_date, "end": self.end_date}
        return None


class PlatformFilter(BaseModel):
    """플랫폼 필터"""
    platform_ids: Optional[List[int]] = Field(None, description="플랫폼 ID 목록")


class NotificationRequest(BaseModel):
    """알림 요청"""
    notification_ids: List[int] = Field(..., description="알림 ID 목록")


class NotificationSettingsUpdate(BaseModel):
    """알림 설정 업데이트"""
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    notification_types: Optional[Dict[str, bool]] = None
    quiet_hours: Optional[Dict[str, Any]] = None
    priority_filter: Optional[Dict[str, bool]] = None


# 대시보드 개요
@router.get("/overview", summary="대시보드 개요 조회")
async def get_dashboard_overview(
    date_range: DateRangeQuery = Depends(),
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    대시보드 개요 데이터를 조회합니다.
    
    - 실시간 매출 현황
    - 주문 관리 현황
    - 재고 모니터링
    - 베스트셀러 상품
    - 플랫폼별 성과
    """
    try:
        overview = await dashboard_service.get_overview(
            db,
            current_user.id,
            platform_filter.platform_ids,
            date_range.to_dict()
        )
        
        return {
            "status": "success",
            "data": overview
        }
        
    except Exception as e:
        logger.error(f"대시보드 개요 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 매출 현황
@router.get("/sales", summary="매출 현황 조회")
async def get_sales_data(
    date_range: DateRangeQuery = Depends(),
    platform_filter: PlatformFilter = Depends(),
    group_by: str = Query("hour", description="집계 단위 (hour, day, week, month)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    매출 현황 데이터를 조회합니다.
    
    - 시간대별/일별/주별/월별 매출 추이
    - 매출 통계 및 요약
    """
    try:
        sales_data = await dashboard_service.get_sales_analytics(
            db,
            current_user.id,
            platform_filter.platform_ids,
            date_range.to_dict(),
            group_by
        )
        
        return {
            "status": "success",
            "data": sales_data
        }
        
    except Exception as e:
        logger.error(f"매출 현황 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 주문 현황
@router.get("/orders", summary="주문 현황 조회")
async def get_order_data(
    date_range: DateRangeQuery = Depends(),
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    주문 현황 데이터를 조회합니다.
    
    - 주문 상태별 분류
    - 시간대별/요일별 주문 패턴
    - 평균 배송 시간
    """
    try:
        order_data = await dashboard_service.get_order_analytics(
            db,
            current_user.id,
            platform_filter.platform_ids,
            date_range.to_dict()
        )
        
        return {
            "status": "success",
            "data": order_data
        }
        
    except Exception as e:
        logger.error(f"주문 현황 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 재고 현황
@router.get("/inventory", summary="재고 현황 조회")
async def get_inventory_data(
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    재고 현황 데이터를 조회합니다.
    
    - 실시간 재고 현황
    - 품절 임박 상품
    - 재고 회전율
    - 재고 건전성 점수
    """
    try:
        inventory_data = await dashboard_service._get_inventory_summary(
            db,
            current_user.id,
            platform_filter.platform_ids
        )
        
        # 품절 임박 상품 상세
        low_stock_products = await analytics_service._find_low_stock_products(
            db,
            current_user.id,
            platform_filter.platform_ids
        )
        
        return {
            "status": "success",
            "data": {
                "summary": inventory_data,
                "low_stock_products": low_stock_products
            }
        }
        
    except Exception as e:
        logger.error(f"재고 현황 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 상품 성과
@router.get("/products/performance", summary="상품 성과 조회")
async def get_product_performance(
    date_range: DateRangeQuery = Depends(),
    platform_filter: PlatformFilter = Depends(),
    limit: int = Query(20, description="조회할 상품 수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    상품 성과 데이터를 조회합니다.
    
    - 베스트셀러 상품
    - 카테고리별 성과
    - 상품별 전환율
    - ABC 분석
    """
    try:
        product_data = await dashboard_service.get_product_performance(
            db,
            current_user.id,
            platform_filter.platform_ids,
            date_range.to_dict(),
            limit
        )
        
        return {
            "status": "success",
            "data": product_data
        }
        
    except Exception as e:
        logger.error(f"상품 성과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# AI 분석
@router.get("/analytics", summary="AI 분석 데이터 조회")
async def get_analytics_data(
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    AI 기반 분석 데이터를 조회합니다.
    
    - 비즈니스 인사이트
    - 실행 가능한 액션 아이템
    - 시장 트렌드
    - 경쟁사 분석
    """
    try:
        analytics_data = await analytics_service.get_ai_insights(
            db,
            current_user.id,
            platform_filter.platform_ids
        )
        
        return {
            "status": "success",
            "data": analytics_data
        }
        
    except Exception as e:
        logger.error(f"AI 분석 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 매출 예측
@router.get("/analytics/forecast", summary="매출 예측 조회")
async def get_sales_forecast(
    platform_filter: PlatformFilter = Depends(),
    days_ahead: int = Query(7, description="예측 일수 (최대 30일)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    AI 기반 매출 예측을 조회합니다.
    
    - 일별 매출 예측
    - 신뢰 구간
    - 예측 정확도
    """
    try:
        if days_ahead > 30:
            raise HTTPException(status_code=400, detail="예측 일수는 최대 30일까지 가능합니다.")
            
        forecast_data = await analytics_service.predict_sales(
            db,
            current_user.id,
            platform_filter.platform_ids,
            days_ahead
        )
        
        return {
            "status": "success",
            "data": forecast_data
        }
        
    except Exception as e:
        logger.error(f"매출 예측 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 알림 목록
@router.get("/notifications", summary="알림 목록 조회")
async def get_notifications(
    unread_only: bool = Query(False, description="미읽음만 조회"),
    limit: int = Query(20, description="조회할 알림 수"),
    offset: int = Query(0, description="시작 위치"),
    priority: Optional[str] = Query(None, description="우선순위 필터"),
    notification_type: Optional[str] = Query(None, description="알림 타입 필터"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    알림 목록을 조회합니다.
    
    - 미읽음/전체 알림
    - 우선순위별 필터링
    - 타입별 필터링
    """
    try:
        notifications = await notification_service.get_notifications(
            db,
            current_user.id,
            unread_only,
            limit,
            offset,
            priority,
            notification_type
        )
        
        return {
            "status": "success",
            "data": notifications
        }
        
    except Exception as e:
        logger.error(f"알림 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 알림 읽음 처리
@router.post("/notifications/read", summary="알림 읽음 처리")
async def mark_notifications_read(
    request: NotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """선택한 알림을 읽음 처리합니다."""
    try:
        updated_count = await notification_service.mark_as_read(
            db,
            current_user.id,
            request.notification_ids
        )
        
        return {
            "status": "success",
            "data": {
                "updated_count": updated_count
            }
        }
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 모든 알림 읽음 처리
@router.post("/notifications/read-all", summary="모든 알림 읽음 처리")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """모든 미읽음 알림을 읽음 처리합니다."""
    try:
        updated_count = await notification_service.mark_all_as_read(
            db,
            current_user.id
        )
        
        return {
            "status": "success",
            "data": {
                "updated_count": updated_count
            }
        }
        
    except Exception as e:
        logger.error(f"모든 알림 읽음 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 알림 삭제
@router.delete("/notifications", summary="알림 삭제")
async def delete_notifications(
    request: NotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """선택한 알림을 삭제합니다."""
    try:
        deleted_count = await notification_service.delete_notifications(
            db,
            current_user.id,
            request.notification_ids
        )
        
        return {
            "status": "success",
            "data": {
                "deleted_count": deleted_count
            }
        }
        
    except Exception as e:
        logger.error(f"알림 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 알림 설정
@router.get("/notifications/settings", summary="알림 설정 조회")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """사용자의 알림 설정을 조회합니다."""
    try:
        settings = await notification_service.get_notification_settings(
            db,
            current_user.id
        )
        
        return {
            "status": "success",
            "data": settings
        }
        
    except Exception as e:
        logger.error(f"알림 설정 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/settings", summary="알림 설정 업데이트")
async def update_notification_settings(
    settings: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """사용자의 알림 설정을 업데이트합니다."""
    try:
        # 현재 설정 조회
        current_settings = await notification_service.get_notification_settings(
            db,
            current_user.id
        )
        
        # 업데이트할 설정만 변경
        update_data = settings.dict(exclude_unset=True)
        updated_settings = {**current_settings, **update_data}
        
        # 설정 저장
        result = await notification_service.update_notification_settings(
            db,
            current_user.id,
            updated_settings
        )
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"알림 설정 업데이트 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 리포트 생성
@router.get("/reports/daily", summary="일일 리포트 생성")
async def generate_daily_report(
    date: Optional[datetime] = Query(None, description="리포트 날짜"),
    platform_filter: PlatformFilter = Depends(),
    format: str = Query("json", description="출력 형식 (json, pdf)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """일일 판매 리포트를 생성합니다."""
    try:
        report_data = await report_service.generate_daily_report(
            db,
            current_user.id,
            date,
            platform_filter.platform_ids
        )
        
        if format == "pdf":
            # PDF 생성
            pdf_bytes = await report_service.generate_pdf_report(
                report_data,
                current_user.name
            )
            
            # Base64 인코딩하여 반환
            import base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            return {
                "status": "success",
                "data": {
                    "format": "pdf",
                    "content": pdf_base64,
                    "filename": f"daily_report_{report_data['date']}.pdf"
                }
            }
        else:
            return {
                "status": "success",
                "data": report_data
            }
            
    except Exception as e:
        logger.error(f"일일 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/weekly", summary="주간 리포트 생성")
async def generate_weekly_report(
    week_start: Optional[datetime] = Query(None, description="주 시작일"),
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """주간 판매 리포트를 생성합니다."""
    try:
        report_data = await report_service.generate_weekly_report(
            db,
            current_user.id,
            week_start,
            platform_filter.platform_ids
        )
        
        return {
            "status": "success",
            "data": report_data
        }
        
    except Exception as e:
        logger.error(f"주간 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/monthly", summary="월간 리포트 생성")
async def generate_monthly_report(
    year: Optional[int] = Query(None, description="년도"),
    month: Optional[int] = Query(None, description="월"),
    platform_filter: PlatformFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """월간 판매 리포트를 생성합니다."""
    try:
        report_data = await report_service.generate_monthly_report(
            db,
            current_user.id,
            year,
            month,
            platform_filter.platform_ids
        )
        
        return {
            "status": "success",
            "data": report_data
        }
        
    except Exception as e:
        logger.error(f"월간 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket 엔드포인트
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="인증 토큰"),
    db: Session = Depends(get_db)
):
    """
    실시간 대시보드 데이터 스트림
    
    WebSocket 연결을 통해 실시간으로 대시보드 데이터를 수신합니다.
    
    메시지 타입:
    - connection: 연결 상태
    - dashboard_update: 대시보드 업데이트
    - notification: 실시간 알림
    - data: 채널별 데이터
    
    클라이언트 메시지:
    - {"type": "ping"}: 연결 확인
    - {"type": "subscribe", "channels": ["dashboard:123"]}: 채널 구독
    - {"type": "unsubscribe", "channels": ["dashboard:123"]}: 구독 해제
    - {"type": "refresh", "channels": ["dashboard:123"]}: 데이터 새로고침
    """
    try:
        # 토큰 검증
        from app.core.auth import verify_token
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
            
        # 연결 ID 생성
        connection_id = str(uuid.uuid4())
        
        # 연결 수락
        await connection_manager.connect(websocket, int(user_id), connection_id)
        
        # 기본 채널 구독
        default_channels = [
            f"dashboard:{user_id}",
            f"notifications:{user_id}"
        ]
        await connection_manager.subscribe(connection_id, default_channels)
        
        try:
            # 메시지 처리
            await connection_manager.handle_message(websocket, connection_id)
            
        except WebSocketDisconnect:
            await connection_manager.disconnect(connection_id)
            
    except Exception as e:
        logger.error(f"WebSocket 에러: {str(e)}")
        await websocket.close(code=4000, reason=str(e))


# 테스트용 이벤트 트리거 (개발 환경에서만 사용)
@router.post("/test/trigger-event", summary="테스트 이벤트 트리거", include_in_schema=False)
async def trigger_test_event(
    event_type: str,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """테스트용 이벤트를 트리거합니다."""
    try:
        # 이벤트 타입 변환
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
            
        # 이벤트 처리
        await event_processor.process_event(
            event_type_enum,
            current_user.id,
            data,
            db
        )
        
        return {
            "status": "success",
            "message": f"Event {event_type} triggered successfully"
        }
        
    except Exception as e:
        logger.error(f"테스트 이벤트 트리거 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))