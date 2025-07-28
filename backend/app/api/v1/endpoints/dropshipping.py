"""
드롭쉬핑 API 엔드포인트

품절 모니터링, 재고 관리, 자동화, 예측 등
드롭쉬핑 운영에 필요한 모든 API 제공
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.database import get_db
from app.services.dropshipping.stock_monitor import DropshippingStockMonitor
from app.services.dropshipping.outofstock_manager import OutOfStockManager
from app.services.dropshipping.supplier_reliability import SupplierReliabilityAnalyzer
from app.services.dropshipping.alternative_finder import AlternativeFinder
from app.services.automation.product_status_automation import ProductStatusAutomation
from app.services.automation.restock_detector import RestockDetector
from app.services.automation.profit_protector import ProfitProtector
from app.services.prediction.stockout_predictor import StockoutPredictor
from app.services.prediction.demand_analyzer import DemandAnalyzer


router = APIRouter()
logger = logging.getLogger(__name__)


# 전역 서비스 인스턴스
stock_monitor = DropshippingStockMonitor()
outofstock_manager = OutOfStockManager()
supplier_analyzer = SupplierReliabilityAnalyzer()
alternative_finder = AlternativeFinder()
automation = ProductStatusAutomation()
restock_detector = RestockDetector()
profit_protector = ProfitProtector()
stockout_predictor = StockoutPredictor()
demand_analyzer = DemandAnalyzer()


# ============================================================================
# 재고 모니터링 API
# ============================================================================

@router.get("/stock-status")
async def get_stock_status(
    current_user = Depends(get_current_user)
) -> Dict:
    """전체 재고 상태 조회"""
    try:
        status = await stock_monitor.get_monitoring_status()
        return {
            "success": True,
            "data": status,
            "message": "재고 모니터링 상태 조회 성공"
        }
    except Exception as e:
        logger.error(f"재고 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-stock")
async def check_stock(
    product_ids: List[int],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
) -> Dict:
    """수동 재고 체크"""
    try:
        # 백그라운드에서 재고 체크 실행
        background_tasks.add_task(
            stock_monitor.bulk_stock_check, product_ids
        )
        
        return {
            "success": True,
            "message": f"{len(product_ids)}개 상품의 재고 체크를 시작했습니다",
            "product_ids": product_ids
        }
    except Exception as e:
        logger.error(f"수동 재고 체크 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start")
async def start_monitoring(
    current_user = Depends(get_current_user)
) -> Dict:
    """재고 모니터링 시작"""
    try:
        await stock_monitor.start_monitoring()
        return {
            "success": True,
            "message": "재고 모니터링이 시작되었습니다"
        }
    except Exception as e:
        logger.error(f"모니터링 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user = Depends(get_current_user)
) -> Dict:
    """재고 모니터링 중지"""
    try:
        await stock_monitor.stop_monitoring()
        return {
            "success": True,
            "message": "재고 모니터링이 중지되었습니다"
        }
    except Exception as e:
        logger.error(f"모니터링 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/monitoring/settings")
async def update_monitoring_settings(
    check_interval: Optional[int] = None,
    low_stock_threshold: Optional[int] = None,
    current_user = Depends(get_current_user)
) -> Dict:
    """모니터링 설정 업데이트"""
    try:
        await stock_monitor.update_monitoring_settings(
            check_interval=check_interval,
            low_stock_threshold=low_stock_threshold
        )
        
        return {
            "success": True,
            "message": "모니터링 설정이 업데이트되었습니다",
            "settings": {
                "check_interval": check_interval,
                "low_stock_threshold": low_stock_threshold
            }
        }
    except Exception as e:
        logger.error(f"설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 품절 관리 API
# ============================================================================

@router.get("/outofstock")
async def get_outofstock_products(
    current_user = Depends(get_current_user)
) -> Dict:
    """품절 상품 목록 조회"""
    try:
        products = await outofstock_manager.get_outofstock_products()
        return {
            "success": True,
            "data": {
                "products": products,
                "total_count": len(products)
            },
            "message": "품절 상품 목록 조회 성공"
        }
    except Exception as e:
        logger.error(f"품절 상품 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outofstock/long-term")
async def get_long_term_outofstock(
    current_user = Depends(get_current_user)
) -> Dict:
    """장기 품절 상품 조회"""
    try:
        products = await outofstock_manager.get_long_term_outofstock()
        return {
            "success": True,
            "data": {
                "products": products,
                "total_count": len(products)
            },
            "message": "장기 품절 상품 목록 조회 성공"
        }
    except Exception as e:
        logger.error(f"장기 품절 상품 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outofstock/cleanup")
async def cleanup_long_term_outofstock(
    current_user = Depends(get_current_user)
) -> Dict:
    """장기 품절 상품 정리"""
    try:
        result = await outofstock_manager.cleanup_long_term_outofstock()
        return {
            "success": True,
            "data": result,
            "message": "장기 품절 상품 정리 완료"
        }
    except Exception as e:
        logger.error(f"품절 상품 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reactivate/{product_id}")
async def reactivate_product(
    product_id: int,
    current_user = Depends(get_current_user)
) -> Dict:
    """상품 재활성화"""
    try:
        await outofstock_manager.handle_restock(product_id)
        return {
            "success": True,
            "message": f"상품 {product_id}의 재활성화 처리를 시작했습니다"
        }
    except Exception as e:
        logger.error(f"상품 재활성화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outofstock/statistics")
async def get_outofstock_statistics(
    current_user = Depends(get_current_user)
) -> Dict:
    """품절 통계 조회"""
    try:
        stats = await outofstock_manager.get_outofstock_statistics()
        return {
            "success": True,
            "data": stats,
            "message": "품절 통계 조회 성공"
        }
    except Exception as e:
        logger.error(f"품절 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 공급업체 신뢰도 API
# ============================================================================

@router.get("/supplier-reliability")
async def get_supplier_reliability(
    supplier_id: Optional[int] = None,
    limit: Optional[int] = 20,
    current_user = Depends(get_current_user)
) -> Dict:
    """공급업체 신뢰도 조회"""
    try:
        if supplier_id:
            # 특정 공급업체 분석
            reliability = await supplier_analyzer.analyze_supplier_reliability(supplier_id)
            return {
                "success": True,
                "data": reliability,
                "message": f"공급업체 {supplier_id} 신뢰도 분석 완료"
            }
        else:
            # 전체 공급업체 순위
            ranking = await supplier_analyzer.get_supplier_ranking(limit)
            return {
                "success": True,
                "data": {
                    "ranking": ranking,
                    "total_count": len(ranking)
                },
                "message": "공급업체 신뢰도 순위 조회 성공"
            }
    except Exception as e:
        logger.error(f"공급업체 신뢰도 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supplier-reliability/analyze-all")
async def analyze_all_suppliers(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
) -> Dict:
    """모든 공급업체 신뢰도 분석"""
    try:
        background_tasks.add_task(supplier_analyzer.analyze_all_suppliers)
        return {
            "success": True,
            "message": "모든 공급업체 신뢰도 분석을 시작했습니다"
        }
    except Exception as e:
        logger.error(f"전체 신뢰도 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supplier-reliability/unreliable")
async def get_unreliable_suppliers(
    threshold_score: float = 60.0,
    current_user = Depends(get_current_user)
) -> Dict:
    """불안정한 공급업체 목록"""
    try:
        unreliable = await supplier_analyzer.identify_unreliable_suppliers(threshold_score)
        return {
            "success": True,
            "data": {
                "suppliers": unreliable,
                "total_count": len(unreliable),
                "threshold_score": threshold_score
            },
            "message": "불안정한 공급업체 목록 조회 성공"
        }
    except Exception as e:
        logger.error(f"불안정 공급업체 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 대체 상품 추천 API
# ============================================================================

@router.post("/find-alternatives")
async def find_alternatives(
    product_id: int,
    category: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    current_user = Depends(get_current_user)
) -> Dict:
    """대체 상품 찾기"""
    try:
        # 상품 정보 조회
        from app.models.product import Product
        from sqlalchemy.orm import Session
        
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
                
            # 가격 범위 설정
            if price_min is None:
                price_min = product.selling_price * 0.8
            if price_max is None:
                price_max = product.selling_price * 1.2
                
            # 카테고리 설정
            search_category = category or product.category
            
        finally:
            db.close()
            
        # 대체 상품 검색
        alternatives = await alternative_finder.find_alternatives(
            category=search_category,
            price_range=(price_min, price_max),
            exclude_product_id=product_id,
            original_product_name=product.name
        )
        
        return {
            "success": True,
            "data": {
                "alternatives": [
                    {
                        "product_id": alt.product_id,
                        "name": alt.name,
                        "wholesaler_name": alt.wholesaler_name,
                        "category": alt.category,
                        "selling_price": alt.selling_price,
                        "current_stock": alt.current_stock,
                        "similarity_score": alt.similarity_score,
                        "alternative_type": alt.alternative_type.value,
                        "reliability_score": alt.reliability_score,
                        "profit_margin": alt.profit_margin,
                        "recommendation_reason": alt.recommendation_reason
                    }
                    for alt in alternatives
                ],
                "total_count": len(alternatives),
                "search_criteria": {
                    "category": search_category,
                    "price_range": [price_min, price_max],
                    "excluded_product": product_id
                }
            },
            "message": f"{len(alternatives)}개의 대체 상품을 찾았습니다"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대체 상품 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alternatives/emergency")
async def get_emergency_alternatives(
    category: str,
    max_price: float,
    limit: int = 5,
    current_user = Depends(get_current_user)
) -> Dict:
    """긴급 대체 상품 추천"""
    try:
        alternatives = await alternative_finder.get_emergency_alternatives(
            category=category,
            max_price=max_price,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "alternatives": [
                    {
                        "product_id": alt.product_id,
                        "name": alt.name,
                        "wholesaler_name": alt.wholesaler_name,
                        "selling_price": alt.selling_price,
                        "current_stock": alt.current_stock,
                        "reliability_score": alt.reliability_score,
                        "recommendation_reason": alt.recommendation_reason
                    }
                    for alt in alternatives
                ],
                "total_count": len(alternatives)
            },
            "message": "긴급 대체 상품 추천 완료"
        }
    except Exception as e:
        logger.error(f"긴급 대체 상품 추천 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 자동화 API
# ============================================================================

@router.get("/automation/status")
async def get_automation_status(
    current_user = Depends(get_current_user)
) -> Dict:
    """자동화 상태 조회"""
    try:
        status = automation.get_automation_status()
        restock_stats = restock_detector.get_restock_statistics()
        profit_stats = await profit_protector.get_protection_statistics()
        
        return {
            "success": True,
            "data": {
                "product_automation": status,
                "restock_detection": restock_stats,
                "profit_protection": profit_stats
            },
            "message": "자동화 상태 조회 성공"
        }
    except Exception as e:
        logger.error(f"자동화 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/start")
async def start_automation(
    current_user = Depends(get_current_user)
) -> Dict:
    """자동화 시작"""
    try:
        await automation.start_automation()
        await restock_detector.start_detection()
        await profit_protector.start_protection()
        
        return {
            "success": True,
            "message": "모든 자동화 서비스가 시작되었습니다"
        }
    except Exception as e:
        logger.error(f"자동화 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/stop")
async def stop_automation(
    current_user = Depends(get_current_user)
) -> Dict:
    """자동화 중지"""
    try:
        await automation.stop_automation()
        await restock_detector.stop_detection()
        await profit_protector.stop_protection()
        
        return {
            "success": True,
            "message": "모든 자동화 서비스가 중지되었습니다"
        }
    except Exception as e:
        logger.error(f"자동화 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/manual-review/{product_id}")
async def approve_manual_review(
    product_id: int,
    approved: bool,
    current_user = Depends(get_current_user)
) -> Dict:
    """수동 검토 승인/거부"""
    try:
        await restock_detector.approve_manual_review(product_id, approved)
        
        status = "승인" if approved else "거부"
        return {
            "success": True,
            "message": f"상품 {product_id}의 수동 검토가 {status}되었습니다"
        }
    except Exception as e:
        logger.error(f"수동 검토 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/automation/settings")
async def update_automation_settings(
    min_margin: Optional[float] = None,
    target_margin: Optional[float] = None,
    max_price_adjustment: Optional[float] = None,
    current_user = Depends(get_current_user)
) -> Dict:
    """자동화 설정 업데이트"""
    try:
        profit_protector.update_protection_settings(
            min_margin=min_margin,
            target_margin=target_margin,
            max_adjustment=max_price_adjustment
        )
        
        return {
            "success": True,
            "message": "자동화 설정이 업데이트되었습니다",
            "settings": {
                "min_margin": min_margin,
                "target_margin": target_margin,
                "max_price_adjustment": max_price_adjustment
            }
        }
    except Exception as e:
        logger.error(f"자동화 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 예측 API
# ============================================================================

@router.get("/prediction/stockout/{product_id}")
async def predict_stockout(
    product_id: int,
    current_user = Depends(get_current_user)
) -> Dict:
    """품절 예측"""
    try:
        prediction = await stockout_predictor.predict_stockout(product_id)
        
        return {
            "success": True,
            "data": {
                "product_id": prediction.product_id,
                "current_stock": prediction.current_stock,
                "predicted_stockout_date": prediction.predicted_stockout_date.isoformat() if prediction.predicted_stockout_date else None,
                "days_until_stockout": prediction.days_until_stockout,
                "confidence": prediction.confidence.value,
                "confidence_score": prediction.confidence_score,
                "predicted_by": prediction.predicted_by,
                "factors": prediction.factors,
                "recommendations": prediction.recommendations,
                "risk_level": prediction.risk_level
            },
            "message": "품절 예측 완료"
        }
    except Exception as e:
        logger.error(f"품절 예측 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/high-risk")
async def get_high_risk_products(
    days_threshold: int = Query(7, ge=1, le=30),
    current_user = Depends(get_current_user)
) -> Dict:
    """고위험 상품 조회"""
    try:
        predictions = await stockout_predictor.get_high_risk_products(days_threshold)
        
        return {
            "success": True,
            "data": {
                "predictions": [
                    {
                        "product_id": p.product_id,
                        "days_until_stockout": p.days_until_stockout,
                        "confidence": p.confidence.value,
                        "risk_level": p.risk_level,
                        "recommendations": p.recommendations
                    }
                    for p in predictions
                ],
                "total_count": len(predictions),
                "threshold_days": days_threshold
            },
            "message": f"{len(predictions)}개의 고위험 상품을 발견했습니다"
        }
    except Exception as e:
        logger.error(f"고위험 상품 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/accuracy")
async def get_prediction_accuracy(
    days_back: int = Query(30, ge=7, le=90),
    current_user = Depends(get_current_user)
) -> Dict:
    """예측 정확도 분석"""
    try:
        accuracy = await stockout_predictor.get_prediction_accuracy(days_back)
        
        return {
            "success": True,
            "data": accuracy,
            "message": "예측 정확도 분석 완료"
        }
    except Exception as e:
        logger.error(f"예측 정확도 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/demand/{product_id}")
async def analyze_demand(
    product_id: int,
    current_user = Depends(get_current_user)
) -> Dict:
    """수요 분석"""
    try:
        analysis = await demand_analyzer.analyze_product_demand(product_id)
        
        return {
            "success": True,
            "data": {
                "product_id": analysis.product_id,
                "current_demand_score": analysis.current_demand_score,
                "trend": analysis.trend.value,
                "weekly_pattern": analysis.weekly_pattern,
                "monthly_pattern": analysis.monthly_pattern,
                "seasonal_index": analysis.seasonal_index,
                "price_elasticity": analysis.price_elasticity,
                "peak_demand_period": analysis.peak_demand_period,
                "demand_volatility": analysis.demand_volatility,
                "growth_rate": analysis.growth_rate,
                "recommendations": analysis.recommendations
            },
            "message": "수요 분석 완료"
        }
    except Exception as e:
        logger.error(f"수요 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/demand/forecast/{product_id}")
async def get_demand_forecast(
    product_id: int,
    days_ahead: int = Query(30, ge=7, le=90),
    current_user = Depends(get_current_user)
) -> Dict:
    """수요 예측"""
    try:
        forecast = await demand_analyzer.get_demand_forecast(product_id, days_ahead)
        
        return {
            "success": True,
            "data": forecast,
            "message": "수요 예측 완료"
        }
    except Exception as e:
        logger.error(f"수요 예측 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction/demand/category/{category}")
async def analyze_category_demand(
    category: str,
    current_user = Depends(get_current_user)
) -> Dict:
    """카테고리별 수요 분석"""
    try:
        analysis = await demand_analyzer.analyze_category_demand(category)
        
        return {
            "success": True,
            "data": analysis,
            "message": f"카테고리 '{category}' 수요 분석 완료"
        }
    except Exception as e:
        logger.error(f"카테고리별 수요 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 수익 보호 API
# ============================================================================

@router.get("/profit-loss")
async def get_profit_loss_analysis(
    days_back: int = Query(30, ge=7, le=90),
    current_user = Depends(get_current_user)
) -> Dict:
    """품절 손실 분석"""
    try:
        # 품절로 인한 예상 손실 계산
        outofstock_stats = await outofstock_manager.get_outofstock_statistics()
        profit_trends = await profit_protector.analyze_profit_trends(days_back)
        
        return {
            "success": True,
            "data": {
                "outofstock_statistics": outofstock_stats,
                "profit_trends": profit_trends,
                "analysis_period_days": days_back
            },
            "message": "수익 손실 분석 완료"
        }
    except Exception as e:
        logger.error(f"수익 손실 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 대시보드 API
# ============================================================================

@router.get("/dashboard")
async def get_dropshipping_dashboard(
    current_user = Depends(get_current_user)
) -> Dict:
    """드롭쉬핑 대시보드 데이터"""
    try:
        # 각 서비스의 주요 지표 수집
        monitoring_status = await stock_monitor.get_monitoring_status()
        outofstock_stats = await outofstock_manager.get_outofstock_statistics()
        automation_status = automation.get_automation_status()
        profit_stats = await profit_protector.get_protection_statistics()
        demand_insights = await demand_analyzer.get_demand_insights()
        
        # 고위험 상품 조회
        high_risk_products = await stockout_predictor.get_high_risk_products(7)
        
        return {
            "success": True,
            "data": {
                "monitoring": {
                    "active": monitoring_status["active"],
                    "monitored_products": monitoring_status["monitored_products"],
                    "check_interval": monitoring_status["check_interval"]
                },
                "outofstock": {
                    "current_outofstock": outofstock_stats["current_outofstock_products"],
                    "total_events": outofstock_stats["total_outofstock_events"],
                    "avg_duration": outofstock_stats["average_duration_hours"],
                    "estimated_loss": outofstock_stats["total_estimated_loss"]
                },
                "automation": {
                    "running": automation_status["is_running"],
                    "active_rules": automation_status["active_rules"],
                    "total_rules": automation_status["total_rules"]
                },
                "profit_protection": {
                    "active": profit_stats["protection_running"],
                    "analyzed_24h": profit_stats["analyzed_products_24h"],
                    "actions_taken_24h": profit_stats["actions_taken_24h"],
                    "avg_margin": profit_stats["avg_margin_24h"]
                },
                "demand_insights": demand_insights,
                "high_risk_products": {
                    "count": len(high_risk_products),
                    "products": [
                        {
                            "product_id": p.product_id,
                            "days_until_stockout": p.days_until_stockout,
                            "risk_level": p.risk_level
                        }
                        for p in high_risk_products[:5]  # 상위 5개만
                    ]
                },
                "last_updated": datetime.now().isoformat()
            },
            "message": "드롭쉬핑 대시보드 데이터 조회 성공"
        }
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 드롭쉬핑 주문 처리 API
# ============================================================================

@router.post("/orders/process")
async def process_dropshipping_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """드롭쉬핑 주문 자동 처리"""
    try:
        from app.services.order_processing.order_processor import OrderProcessor
        
        processor = OrderProcessor(db)
        
        # 백그라운드에서 주문 처리 실행
        background_tasks.add_task(processor.process_order, order_id)
        
        return {
            "success": True,
            "message": f"주문 {order_id} 처리를 시작했습니다",
            "order_id": order_id
        }
    except Exception as e:
        logger.error(f"주문 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/status")
async def get_order_processing_status(
    order_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """주문 처리 상태 조회"""
    try:
        from app.services.order_processing.order_processor import OrderProcessor
        
        processor = OrderProcessor(db)
        status = await processor.get_processing_status(order_id)
        
        return {
            "success": True,
            "data": status,
            "message": "주문 상태 조회 성공"
        }
    except Exception as e:
        logger.error(f"주문 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/retry")
async def retry_failed_order(
    order_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """실패한 주문 재처리"""
    try:
        from app.services.order_processing.order_processor import OrderProcessor
        
        processor = OrderProcessor(db)
        result = await processor.retry_failed_order(order_id)
        
        return {
            "success": result['success'],
            "data": result,
            "message": result['message']
        }
    except Exception as e:
        logger.error(f"주문 재처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/failed")
async def get_failed_orders(
    limit: int = Query(50, ge=1, le=100),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """실패한 주문 목록 조회"""
    try:
        from app.services.order_processing.order_processor import OrderProcessor
        
        processor = OrderProcessor(db)
        failed_orders = await processor.get_failed_orders(limit)
        
        return {
            "success": True,
            "data": {
                "orders": failed_orders,
                "total_count": len(failed_orders)
            },
            "message": "실패한 주문 목록 조회 성공"
        }
    except Exception as e:
        logger.error(f"실패한 주문 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/bulk-process")
async def process_bulk_orders(
    order_ids: List[str],
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """대량 주문 일괄 처리"""
    try:
        from app.services.order_processing.order_processor import OrderProcessor
        
        processor = OrderProcessor(db)
        
        # 백그라운드에서 대량 주문 처리 실행
        background_tasks.add_task(processor.process_bulk_orders, order_ids)
        
        return {
            "success": True,
            "message": f"{len(order_ids)}개 주문의 일괄 처리를 시작했습니다",
            "order_count": len(order_ids)
        }
    except Exception as e:
        logger.error(f"대량 주문 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/shipping")
async def get_shipping_tracking(
    order_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """배송 추적 정보 조회"""
    try:
        from app.services.shipping.shipping_tracker import ShippingTracker
        from app.models.order_core import DropshippingOrder, Order
        
        # 드롭쉬핑 주문 조회
        dropshipping_order = db.query(DropshippingOrder).join(Order).filter(
            Order.id == order_id
        ).first()
        
        if not dropshipping_order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        tracker = ShippingTracker(db)
        tracking_result = await tracker.track_order(str(dropshipping_order.id))
        
        return {
            "success": tracking_result['success'],
            "data": tracking_result,
            "message": "배송 추적 정보 조회 완료"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배송 추적 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/delivery-estimate")
async def get_delivery_estimate(
    order_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """배송 예상 시간 조회"""
    try:
        from app.services.shipping.delivery_estimator import DeliveryEstimator
        from app.models.order_core import DropshippingOrder, Order
        
        # 드롭쉬핑 주문 조회
        dropshipping_order = db.query(DropshippingOrder).join(Order).filter(
            Order.id == order_id
        ).first()
        
        if not dropshipping_order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        estimator = DeliveryEstimator(db)
        estimate = await estimator.estimate_delivery_time(dropshipping_order)
        
        return {
            "success": estimate['success'],
            "data": estimate,
            "message": "배송 예상 시간 조회 완료"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배송 예상 시간 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/cancel")
async def cancel_dropshipping_order(
    order_id: str,
    reason: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """드롭쉬핑 주문 취소"""
    try:
        from app.services.ordering.order_manager import OrderManager
        from app.models.order_core import DropshippingOrder, Order
        
        # 드롭쉬핑 주문 조회
        dropshipping_order = db.query(DropshippingOrder).join(Order).filter(
            Order.id == order_id
        ).first()
        
        if not dropshipping_order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        order_manager = OrderManager(db)
        result = await order_manager.cancel_order(dropshipping_order, reason)
        
        return {
            "success": result['success'],
            "data": result,
            "message": result['message']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/margin-analysis")
async def get_margin_analysis(
    days: int = Query(30, ge=1, le=90),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """마진 분석 리포트"""
    try:
        from app.services.order_processing.margin_calculator import MarginCalculator
        from datetime import datetime, timedelta
        
        calculator = MarginCalculator(db)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        analysis = await calculator.get_margin_analysis_report(start_date, end_date)
        
        return {
            "success": analysis['success'],
            "data": analysis,
            "message": "마진 분석 리포트 생성 완료"
        }
    except Exception as e:
        logger.error(f"마진 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/supplier-comparison/{order_id}")
async def compare_suppliers_for_order(
    order_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """주문별 공급업체 비교"""
    try:
        from app.services.order_processing.supplier_selector import SupplierSelector
        
        selector = SupplierSelector(db)
        comparison = await selector.compare_suppliers(order_id)
        
        return {
            "success": comparison['success'],
            "data": comparison,
            "message": "공급업체 비교 분석 완료"
        }
    except Exception as e:
        logger.error(f"공급업체 비교 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/refund")
async def process_refund(
    order_id: str,
    refund_reason: str,
    refund_type: str = "full",
    refund_amount: Optional[float] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """환불 처리"""
    try:
        from app.services.exception_handling.refund_processor import RefundProcessor, RefundReason, RefundType
        from app.models.order_core import DropshippingOrder, Order
        from decimal import Decimal
        
        # 드롭쉬핑 주문 조회
        dropshipping_order = db.query(DropshippingOrder).join(Order).filter(
            Order.id == order_id
        ).first()
        
        if not dropshipping_order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        # Enum 변환
        try:
            reason_enum = RefundReason(refund_reason)
            type_enum = RefundType(refund_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"잘못된 환불 사유 또는 유형: {e}")
        
        processor = RefundProcessor(db)
        result = await processor.process_refund_request(
            dropshipping_order,
            reason_enum,
            type_enum,
            Decimal(str(refund_amount)) if refund_amount else None
        )
        
        return {
            "success": result['success'],
            "data": result,
            "message": result['message']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"환불 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shipping/track-all")
async def track_all_shipments(
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """모든 활성 배송 추적"""
    try:
        from app.services.shipping.shipping_tracker import ShippingTracker
        
        tracker = ShippingTracker(db)
        result = await tracker.track_all_active_orders()
        
        return {
            "success": result['success'],
            "data": result,
            "message": "전체 배송 추적 완료"
        }
    except Exception as e:
        logger.error(f"전체 배송 추적 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shipping/status-summary")
async def get_shipping_status_summary(
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """배송 상태 요약"""
    try:
        from app.services.shipping.shipping_tracker import ShippingTracker
        
        tracker = ShippingTracker(db)
        summary = await tracker.get_delivery_status_summary()
        
        return {
            "success": summary['success'],
            "data": summary,
            "message": "배송 상태 요약 조회 완료"
        }
    except Exception as e:
        logger.error(f"배송 상태 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shipping/performance-report")
async def get_delivery_performance_report(
    days: int = Query(30, ge=7, le=90),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """배송 성과 리포트"""
    try:
        from app.services.shipping.delivery_estimator import DeliveryEstimator
        
        estimator = DeliveryEstimator(db)
        report = await estimator.get_delivery_performance_report(days)
        
        return {
            "success": report['success'],
            "data": report,
            "message": "배송 성과 리포트 생성 완료"
        }
    except Exception as e:
        logger.error(f"배송 성과 리포트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exceptions/statistics")
async def get_exception_statistics(
    days: int = Query(30, ge=7, le=90),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """예외 처리 통계"""
    try:
        from app.services.exception_handling.order_exception_handler import OrderExceptionHandler
        
        handler = OrderExceptionHandler(db)
        stats = await handler.get_exception_statistics(days)
        
        return {
            "success": stats['success'],
            "data": stats,
            "message": "예외 처리 통계 조회 완료"
        }
    except Exception as e:
        logger.error(f"예외 처리 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refunds/statistics")
async def get_refund_statistics(
    days: int = Query(30, ge=7, le=90),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """환불 통계"""
    try:
        from app.services.exception_handling.refund_processor import RefundProcessor
        
        processor = RefundProcessor(db)
        stats = await processor.get_refund_statistics(days)
        
        return {
            "success": stats['success'],
            "data": stats,
            "message": "환불 통계 조회 완료"
        }
    except Exception as e:
        logger.error(f"환불 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refunds/pending")
async def get_pending_refunds(
    limit: int = Query(50, ge=1, le=100),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[Dict]:
    """대기 중인 환불 목록"""
    try:
        from app.services.exception_handling.refund_processor import RefundProcessor
        
        processor = RefundProcessor(db)
        pending_refunds = await processor.get_pending_refunds(limit)
        
        return pending_refunds
    except Exception as e:
        logger.error(f"대기 중인 환불 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refunds/{refund_id}/approve")
async def approve_refund(
    refund_id: str,
    notes: Optional[str] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """환불 승인"""
    try:
        from app.services.exception_handling.refund_processor import RefundProcessor
        
        processor = RefundProcessor(db)
        result = await processor.approve_refund(refund_id, current_user.username, notes)
        
        return {
            "success": result['success'],
            "data": result,
            "message": result['message']
        }
    except Exception as e:
        logger.error(f"환불 승인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refunds/{refund_id}/reject")
async def reject_refund(
    refund_id: str,
    reason: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict:
    """환불 거부"""
    try:
        from app.services.exception_handling.refund_processor import RefundProcessor
        
        processor = RefundProcessor(db)
        result = await processor.reject_refund(refund_id, current_user.username, reason)
        
        return {
            "success": result['success'],
            "data": result,
            "message": result['message']
        }
    except Exception as e:
        logger.error(f"환불 거부 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 헬스체크 API
# ============================================================================

@router.get("/health")
async def health_check() -> Dict:
    """드롭쉬핑 서비스 헬스체크"""
    try:
        services = {
            "stock_monitoring": stock_monitor.monitoring_active,
            "automation": automation.is_running,
            "restock_detection": restock_detector.is_running,
            "profit_protection": profit_protector.is_running
        }
        
        all_healthy = all(services.values())
        
        return {
            "success": True,
            "data": {
                "overall_status": "healthy" if all_healthy else "degraded",
                "services": services,
                "timestamp": datetime.now().isoformat()
            },
            "message": "헬스체크 완료"
        }
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "success": False,
            "data": {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            "message": "헬스체크 실패"
        }