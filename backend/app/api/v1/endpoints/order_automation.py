"""
Order automation API endpoints
주문 처리 자동화 API 엔드포인트
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.services.order_automation import OrderAutomationManager
from app.models.user import User
from app.schemas.order_automation import (
    OrderProcessingRequest,
    OrderProcessingResponse,
    SystemStatusResponse,
    SettlementRequest,
    SettlementResponse,
    ExceptionHandlingRequest,
    ExceptionHandlingResponse
)

router = APIRouter()


@router.post("/start", response_model=Dict[str, Any])
async def start_automation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자동화 시스템 시작"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 백그라운드에서 시작
        background_tasks.add_task(automation_manager.start_automation)
        
        return {
            "success": True,
            "message": "주문 처리 자동화 시스템이 시작되었습니다",
            "started_by": current_user.email,
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동화 시스템 시작 실패: {str(e)}")


@router.post("/stop", response_model=Dict[str, Any])
async def stop_automation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자동화 시스템 중지"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 백그라운드에서 중지
        background_tasks.add_task(automation_manager.stop_automation)
        
        return {
            "success": True,
            "message": "주문 처리 자동화 시스템이 중지되었습니다",
            "stopped_by": current_user.email,
            "stopped_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동화 시스템 중지 실패: {str(e)}")


@router.post("/restart", response_model=Dict[str, Any])
async def restart_automation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자동화 시스템 재시작"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 백그라운드에서 재시작
        background_tasks.add_task(automation_manager.restart_automation)
        
        return {
            "success": True,
            "message": "주문 처리 자동화 시스템이 재시작되었습니다",
            "restarted_by": current_user.email,
            "restarted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동화 시스템 재시작 실패: {str(e)}")


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """시스템 상태 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        status = await automation_manager.get_system_status()
        
        return SystemStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 상태 조회 실패: {str(e)}")


@router.post("/process-order", response_model=OrderProcessingResponse)
async def process_order_manual(
    request: OrderProcessingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """수동 주문 처리"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 주문 처리 실행
        result = await automation_manager.process_order_end_to_end(request.dict())
        
        if result['success']:
            return OrderProcessingResponse(**result)
        else:
            raise HTTPException(status_code=400, detail=result.get('error', '주문 처리 실패'))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주문 처리 실패: {str(e)}")


@router.get("/orders/{order_id}/status")
async def get_order_status(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """주문 상태 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 주문 상태 조회 로직 (실제 구현에서 완성 필요)
        order_status = await automation_manager._get_order_status(order_id)
        
        return {
            "success": True,
            "order_id": order_id,
            "status": order_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주문 상태 조회 실패: {str(e)}")


@router.post("/settlements/generate", response_model=SettlementResponse)
async def generate_settlement(
    request: SettlementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """정산 생성"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        result = await automation_manager.auto_settlement.generate_settlement(request.order_id)
        
        if result['success']:
            return SettlementResponse(**result)
        else:
            raise HTTPException(status_code=400, detail=result.get('error', '정산 생성 실패'))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정산 생성 실패: {str(e)}")


@router.get("/settlements/report")
async def get_profit_report(
    start_date: datetime = Query(..., description="시작일"),
    end_date: datetime = Query(..., description="종료일"),
    format_type: str = Query("json", description="응답 형식 (json, excel, csv)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """수익 보고서 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        if format_type.lower() == "json":
            # JSON 형식 보고서
            report = await automation_manager.auto_settlement.generate_profit_report(
                start_date, end_date
            )
            return report
        
        elif format_type.lower() in ["excel", "csv"]:
            # 파일 다운로드
            export_result = await automation_manager.auto_settlement.export_accounting_data(
                start_date, end_date, format_type
            )
            
            if export_result['success']:
                file_data = io.BytesIO(export_result['file_data'])
                
                return StreamingResponse(
                    io.BytesIO(export_result['file_data']),
                    media_type=export_result['content_type'],
                    headers={
                        "Content-Disposition": f"attachment; filename={export_result['filename']}"
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=export_result['error'])
        
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 형식입니다")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 조회 실패: {str(e)}")


@router.post("/exceptions/handle", response_model=ExceptionHandlingResponse)
async def handle_exception(
    request: ExceptionHandlingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """예외 상황 처리"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        if request.exception_type == "order_cancellation":
            result = await automation_manager.exception_handler.handle_order_cancellation(
                request.order_id, request.reason
            )
        elif request.exception_type == "exchange_request":
            result = await automation_manager.exception_handler.process_exchange_request(
                request.order_id, request.items, request.reason
            )
        elif request.exception_type == "return_request":
            result = await automation_manager.exception_handler.manage_return_process(
                request.order_id, request.items, request.reason
            )
        elif request.exception_type == "stockout":
            result = await automation_manager.exception_handler.handle_stockout(
                request.product_sku, request.wholesaler_id
            )
        else:
            result = await automation_manager.handle_system_exception(
                request.exception_type, request.context or {}
            )
        
        if result['success']:
            return ExceptionHandlingResponse(**result)
        else:
            raise HTTPException(status_code=400, detail=result.get('error', '예외 처리 실패'))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예외 처리 실패: {str(e)}")


@router.get("/tracking/{tracking_number}")
async def get_tracking_info(
    tracking_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """배송 추적 정보 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 추적 정보 조회 (실제 구현에서 완성 필요)
        tracking_info = await automation_manager.shipping_tracker._get_tracking_info(tracking_number)
        
        return {
            "success": True,
            "tracking_number": tracking_number,
            "tracking_info": tracking_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배송 추적 조회 실패: {str(e)}")


@router.post("/inventory/sync")
async def sync_inventory(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """재고 동기화"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 백그라운드에서 동기화 실행
        background_tasks.add_task(automation_manager.exception_handler.sync_inventory)
        
        return {
            "success": True,
            "message": "재고 동기화가 시작되었습니다",
            "started_by": current_user.email,
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재고 동기화 실패: {str(e)}")


@router.get("/alternatives/{product_sku}")
async def find_alternatives(
    product_sku: str,
    order_id: Optional[str] = Query(None, description="주문 ID (선택사항)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대체 상품 찾기"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        result = await automation_manager.exception_handler.find_alternatives(
            product_sku, order_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대체 상품 찾기 실패: {str(e)}")


@router.get("/statistics")
async def get_automation_statistics(
    period: str = Query("today", description="기간 (today, week, month, year)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자동화 통계 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 기간별 통계 조회 (실제 구현에서 완성 필요)
        statistics = await automation_manager._get_period_statistics(period)
        
        return {
            "success": True,
            "period": period,
            "statistics": statistics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.get("/logs")
async def get_processing_logs(
    order_id: Optional[str] = Query(None, description="주문 ID"),
    start_date: Optional[datetime] = Query(None, description="시작일"),
    end_date: Optional[datetime] = Query(None, description="종료일"),
    limit: int = Query(100, description="조회 개수"),
    offset: int = Query(0, description="시작 위치"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """처리 로그 조회"""
    try:
        automation_manager = OrderAutomationManager(db)
        
        # 로그 조회 (실제 구현에서 완성 필요)
        logs = await automation_manager._get_processing_logs(
            order_id, start_date, end_date, limit, offset
        )
        
        return {
            "success": True,
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """헬스체크"""
    try:
        automation_manager = OrderAutomationManager(db)
        status = await automation_manager.get_system_status()
        
        if status.get('system_running'):
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": status.get('uptime_formatted', '00:00:00'),
                "modules": status.get('modules', {})
            }
        else:
            return {
                "status": "unhealthy", 
                "timestamp": datetime.utcnow().isoformat(),
                "error": status.get('error', '시스템이 실행 중이지 않습니다')
            }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }