"""
상품가공 API 엔드포인트

RESTful API를 통해 상품가공 서비스 제공
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.v1.dependencies.database import get_db
from app.services.processing.product_processing_service import ProductProcessingService
from app.services.processing.cost_optimizer import ProcessingPriority
from app.models.product import Product


router = APIRouter()


# Pydantic 모델들
class ProcessingOptionsRequest(BaseModel):
    process_name: bool = Field(True, description="상품명 가공 여부")
    process_images: bool = Field(True, description="이미지 가공 여부") 
    process_purpose: bool = Field(True, description="용도 분석 여부")
    apply_guidelines: bool = Field(True, description="가이드라인 적용 여부")


class SingleProcessingRequest(BaseModel):
    product_id: int = Field(..., description="상품 ID")
    marketplace: str = Field(..., description="마켓플레이스", regex="^(coupang|naver|11st)$")
    priority: str = Field("medium", description="처리 우선순위", regex="^(high|medium|low)$")
    processing_options: Optional[ProcessingOptionsRequest] = None


class BatchProcessingRequest(BaseModel):
    product_ids: List[int] = Field(..., description="상품 ID 목록", min_items=1, max_items=100)
    marketplace: str = Field(..., description="마켓플레이스", regex="^(coupang|naver|11st)$")
    priority: str = Field("low", description="처리 우선순위", regex="^(high|medium|low)$")
    processing_options: Optional[ProcessingOptionsRequest] = None


class ProcessingResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    total_count: int
    history: List[Dict[str, Any]]


@router.post("/process/single", response_model=ProcessingResponse)
async def process_single_product(
    request: SingleProcessingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """단일 상품 가공"""
    
    try:
        # 상품 존재 확인
        product = db.query(Product).filter(Product.id == request.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        # 서비스 초기화
        processing_service = ProductProcessingService(db)
        
        # 우선순위 변환
        priority = ProcessingPriority(request.priority)
        
        # 처리 옵션 변환
        processing_options = None
        if request.processing_options:
            processing_options = request.processing_options.dict()
        
        # 처리 실행
        result = await processing_service.process_product_complete(
            product_id=request.product_id,
            marketplace=request.marketplace,
            priority=priority,
            processing_options=processing_options
        )
        
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ProcessingResponse(
            success=result.get("success", False),
            message="상품 가공이 완료되었습니다" if result.get("success") else "상품 가공 중 일부 문제가 발생했습니다",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/process/batch", response_model=ProcessingResponse)
async def process_batch_products(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """배치 상품 가공"""
    
    try:
        # 상품들 존재 확인
        existing_products = db.query(Product).filter(
            Product.id.in_(request.product_ids)
        ).all()
        
        existing_ids = [p.id for p in existing_products]
        missing_ids = set(request.product_ids) - set(existing_ids)
        
        if missing_ids:
            raise HTTPException(
                status_code=404, 
                detail=f"다음 상품들을 찾을 수 없습니다: {list(missing_ids)}"
            )
        
        # 서비스 초기화
        processing_service = ProductProcessingService(db)
        
        # 우선순위 변환
        priority = ProcessingPriority(request.priority)
        
        # 처리 옵션 변환
        processing_options = None
        if request.processing_options:
            processing_options = request.processing_options.dict()
        
        # 배치 처리 실행
        result = await processing_service.process_product_batch(
            product_ids=request.product_ids,
            marketplace=request.marketplace,
            priority=priority,
            processing_options=processing_options
        )
        
        return ProcessingResponse(
            success=result["success_count"] > 0,
            message=f"배치 처리 완료: 성공 {result['success_count']}개, 실패 {result['error_count']}개",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 처리 중 오류가 발생했습니다: {str(e)}")


@router.get("/history", response_model=HistoryResponse)
async def get_processing_history(
    product_id: Optional[int] = Query(None, description="특정 상품의 이력만 조회"),
    marketplace: Optional[str] = Query(None, description="특정 마켓플레이스의 이력만 조회"),
    limit: int = Query(50, ge=1, le=200, description="조회할 이력 수"),
    db: Session = Depends(get_db)
):
    """상품 가공 이력 조회"""
    
    try:
        processing_service = ProductProcessingService(db)
        
        history = processing_service.get_processing_history(
            product_id=product_id,
            marketplace=marketplace,
            limit=limit
        )
        
        return HistoryResponse(
            total_count=len(history),
            history=history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이력 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/cost/analytics")
async def get_cost_analytics(
    days: int = Query(30, ge=1, le=365, description="분석할 일수"),
    db: Session = Depends(get_db)
):
    """비용 분석"""
    
    try:
        from app.services.processing.cost_optimizer import CostOptimizer
        
        cost_optimizer = CostOptimizer(db)
        analytics = cost_optimizer.get_cost_analytics(days=days)
        
        return ProcessingResponse(
            success=True,
            message=f"{days}일간 비용 분석 결과",
            data=analytics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"비용 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/guidelines/{marketplace}")
async def get_market_guidelines(
    marketplace: str,
    db: Session = Depends(get_db)
):
    """마켓플레이스 가이드라인 조회"""
    
    try:
        from app.services.processing.market_guideline_manager import MarketGuidelineManager
        
        if marketplace not in ["coupang", "naver", "11st"]:
            raise HTTPException(status_code=400, detail="지원되지 않는 마켓플레이스입니다")
        
        guideline_manager = MarketGuidelineManager(db)
        guidelines = guideline_manager.get_guidelines(marketplace)
        
        if not guidelines:
            raise HTTPException(status_code=404, detail="가이드라인을 찾을 수 없습니다")
        
        return ProcessingResponse(
            success=True,
            message=f"{marketplace} 가이드라인 조회 완료",
            data=guidelines
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가이드라인 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/validate/name")
async def validate_product_name(
    name: str,
    marketplace: str,
    db: Session = Depends(get_db)
):
    """상품명 가이드라인 검증"""
    
    try:
        from app.services.processing.market_guideline_manager import MarketGuidelineManager
        
        if marketplace not in ["coupang", "naver", "11st"]:
            raise HTTPException(status_code=400, detail="지원되지 않는 마켓플레이스입니다")
        
        guideline_manager = MarketGuidelineManager(db)
        validation_result = guideline_manager.validate_product_name(name, marketplace)
        
        return ProcessingResponse(
            success=validation_result["valid"],
            message="검증 완료",
            data=validation_result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상품명 검증 중 오류가 발생했습니다: {str(e)}")


@router.post("/validate/description")
async def validate_product_description(
    description: str,
    marketplace: str,
    db: Session = Depends(get_db)
):
    """상품 설명 가이드라인 검증"""
    
    try:
        from app.services.processing.market_guideline_manager import MarketGuidelineManager
        
        if marketplace not in ["coupang", "naver", "11st"]:
            raise HTTPException(status_code=400, detail="지원되지 않는 마켓플레이스입니다")
        
        guideline_manager = MarketGuidelineManager(db)
        validation_result = guideline_manager.validate_product_description(description, marketplace)
        
        return ProcessingResponse(
            success=validation_result["valid"],
            message="검증 완료",
            data=validation_result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상품 설명 검증 중 오류가 발생했습니다: {str(e)}")


@router.post("/validate/image")
async def validate_image_specs(
    image_info: Dict[str, Any],
    marketplace: str,
    db: Session = Depends(get_db)
):
    """이미지 규격 검증"""
    
    try:
        from app.services.processing.market_guideline_manager import MarketGuidelineManager
        
        if marketplace not in ["coupang", "naver", "11st"]:
            raise HTTPException(status_code=400, detail="지원되지 않는 마켓플레이스입니다")
        
        # 필수 필드 확인
        required_fields = ["width", "height", "file_size_mb", "format"]
        missing_fields = [field for field in required_fields if field not in image_info]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"필수 필드가 누락되었습니다: {missing_fields}"
            )
        
        guideline_manager = MarketGuidelineManager(db)
        validation_result = guideline_manager.validate_image_specs(image_info, marketplace)
        
        return ProcessingResponse(
            success=validation_result["valid"],
            message="검증 완료",
            data=validation_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 검증 중 오류가 발생했습니다: {str(e)}")


@router.get("/status/{product_id}")
async def get_processing_status(
    product_id: int,
    db: Session = Depends(get_db)
):
    """특정 상품의 최신 가공 상태 조회"""
    
    try:
        # 상품 존재 확인
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        processing_service = ProductProcessingService(db)
        
        # 최신 이력 1개만 조회
        history = processing_service.get_processing_history(
            product_id=product_id, 
            limit=1
        )
        
        if not history:
            return ProcessingResponse(
                success=True,
                message="가공 이력이 없습니다",
                data={"status": "not_processed"}
            )
        
        latest = history[0]
        
        status_data = {
            "status": "completed" if latest["success"] else "failed",
            "last_processing": latest["created_at"],
            "processing_time_ms": latest["processing_time_ms"],
            "quality_score": latest["results_summary"]["quality_score"],
            "successful_steps": latest["results_summary"]["successful_steps"],
            "total_steps": latest["results_summary"]["total_steps"]
        }
        
        return ProcessingResponse(
            success=True,
            message="상품 가공 상태 조회 완료",
            data=status_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/performance/summary")
async def get_performance_summary(
    days: int = Query(7, ge=1, le=90, description="분석할 일수"),
    db: Session = Depends(get_db)
):
    """성능 요약 정보"""
    
    try:
        from app.models.product_processing import ProductProcessingHistory
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 기본 통계
        total_processed = db.query(ProductProcessingHistory).filter(
            ProductProcessingHistory.created_at >= start_date
        ).count()
        
        successful_processed = db.query(ProductProcessingHistory).filter(
            and_(
                ProductProcessingHistory.created_at >= start_date,
                ProductProcessingHistory.success == True
            )
        ).count()
        
        # 평균 처리 시간
        avg_processing_time = db.query(
            func.avg(ProductProcessingHistory.processing_time_ms)
        ).filter(
            ProductProcessingHistory.created_at >= start_date
        ).scalar() or 0
        
        success_rate = (successful_processed / total_processed * 100) if total_processed > 0 else 0
        
        summary = {
            "period_days": days,
            "total_processed": total_processed,
            "successful_processed": successful_processed,
            "success_rate": round(success_rate, 2),
            "average_processing_time_ms": round(avg_processing_time, 2),
            "average_processing_time_seconds": round(avg_processing_time / 1000, 2)
        }
        
        return ProcessingResponse(
            success=True,
            message=f"{days}일간 성능 요약",
            data=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성능 요약 조회 중 오류가 발생했습니다: {str(e)}")