"""
최적화된 주문 관리 API 엔드포인트
N+1 쿼리 해결, 고급 캐싱, 배치 처리 적용
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.database import get_async_db
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.models.order_core import Order, OrderStatus, OrderItem
from app.services.performance.database_optimizer import db_optimizer
from app.services.performance.enhanced_cache_manager import enhanced_cache_manager, CacheConfig, enhanced_cached
from app.services.performance.async_batch_processor import wholesaler_batch_processor, performance_monitor
from app.services.order_automation.real_order_processor import real_order_processor
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse

router = APIRouter()


@router.get("/", response_model=OrderListResponse)
@enhanced_cached(
    ttl=300, 
    namespace="orders_optimized",
    compression=True,
    key_func=lambda page, page_size, status, platform, date_from, date_to, **kwargs: 
        f"list:{page}:{page_size}:{status}:{platform}:{date_from}:{date_to}"
)
async def get_orders_optimized(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    platform: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """최적화된 주문 목록 조회 (N+1 쿼리 해결)"""
    
    async with performance_monitor.track_operation("get_orders_optimized"):
        filters = {
            "status": status,
            "platform": platform,
            "date_from": date_from,
            "date_to": date_to
        }
        
        # 최적화된 데이터베이스 쿼리 사용
        result = await db_optimizer.get_orders_optimized(
            db=db,
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        return OrderListResponse(**result)


@router.get("/{order_id}", response_model=OrderResponse)
@enhanced_cached(
    ttl=600,
    namespace="orders_detail",
    compression=True,
    key_func=lambda order_id, **kwargs: f"detail:{order_id}"
)
async def get_order_detail_optimized(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """최적화된 주문 상세 조회"""
    
    async with performance_monitor.track_operation("get_order_detail"):
        # 단일 쿼리로 모든 관련 데이터 조회
        result = await db_optimizer.get_orders_optimized(
            db=db,
            filters={"id": order_id},
            page=1,
            page_size=1
        )
        
        if not result["items"]:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        order_data = result["items"][0]
        
        # OrderResponse 형식으로 변환
        return OrderResponse(
            id=order_data["id"],
            order_number=order_data["order_number"],
            platform=order_data["platform"],
            status=order_data["status"],
            customer={
                "name": order_data["customer_name"],
                "phone": order_data.get("customer_phone", ""),
                "email": order_data.get("customer_email", ""),
                "address": order_data.get("shipping_address", ""),
                "memo": order_data.get("customer_memo", "")
            },
            items=order_data["items"],
            total_amount=order_data["total_amount"],
            shipping_fee=order_data.get("shipping_fee", 0),
            tracking_number=order_data.get("tracking_number"),
            wholesaler_order_id=order_data.get("wholesaler_order_id"),
            created_at=datetime.fromisoformat(order_data["created_at"]),
            updated_at=order_data.get("updated_at"),
            shipped_at=order_data.get("shipped_at"),
            delivered_at=order_data.get("delivered_at"),
            internal_memo=order_data.get("internal_memo")
        )


@router.post("/batch-process")
async def batch_process_orders(
    background_tasks: BackgroundTasks,
    max_orders: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """대량 주문 배치 처리"""
    
    async with performance_monitor.track_operation("batch_process_orders"):
        # 처리 대기 중인 주문 조회
        pending_orders = await db_optimizer.get_orders_optimized(
            db=db,
            filters={"status": OrderStatus.PENDING},
            page=1,
            page_size=max_orders
        )
        
        if not pending_orders["items"]:
            return {
                "success": True,
                "message": "처리할 주문이 없습니다",
                "processed_count": 0
            }
        
        # 배경 작업으로 배치 처리
        background_tasks.add_task(
            _process_orders_batch,
            [order["id"] for order in pending_orders["items"]]
        )
        
        # 캐시 무효화
        enhanced_cache_manager.flush_namespace("orders_optimized")
        enhanced_cache_manager.flush_namespace("orders_detail")
        
        return {
            "success": True,
            "message": f"{len(pending_orders['items'])}개 주문 처리를 시작했습니다",
            "processed_count": len(pending_orders["items"]),
            "estimated_completion": datetime.now() + timedelta(minutes=len(pending_orders["items"]) // 10)
        }


async def _process_orders_batch(order_ids: List[int]):
    """주문 배치 처리 (백그라운드)"""
    try:
        from app.services.database.database import get_async_db_context
        
        async with get_async_db_context() as db:
            results = []
            
            # 배치 단위로 처리
            batch_size = 10
            for i in range(0, len(order_ids), batch_size):
                batch = order_ids[i:i + batch_size]
                
                for order_id in batch:
                    try:
                        result = await real_order_processor.process_single_order(db, order_id)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Order {order_id} processing failed: {e}")
                        results.append({
                            "order_id": order_id,
                            "status": "failed",
                            "error": str(e)
                        })
                
                # 배치 간 짧은 대기
                await asyncio.sleep(0.1)
            
            # 캐시 무효화
            enhanced_cache_manager.flush_namespace("orders_optimized")
            enhanced_cache_manager.flush_namespace("analytics")
            
            logger.info(f"Batch processed {len(results)} orders")
            
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")


@router.post("/sync-external")
async def sync_external_orders(
    platform: Optional[str] = None,
    hours: int = Query(24, description="동기화할 시간 범위"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """외부 플랫폼 주문 동기화 (배치 처리)"""
    
    async with performance_monitor.track_operation("sync_external_orders"):
        try:
            # 동기화 대상 플랫폼 결정
            platforms_to_sync = [platform] if platform else ["coupang", "naver", "11st"]
            
            # 배치 처리 설정
            from app.services.performance.async_batch_processor import BatchConfig, BatchProcessingStrategy
            
            batch_config = BatchConfig(
                batch_size=50,
                max_concurrent=3,
                strategy=BatchProcessingStrategy.PARALLEL,
                timeout_seconds=60,
                retry_attempts=2
            )
            
            # 플랫폼별 동기화 작업 준비
            sync_tasks = []
            for platform_name in platforms_to_sync:
                sync_tasks.append({
                    "platform": platform_name,
                    "since": datetime.now() - timedelta(hours=hours),
                    "batch_size": 100
                })
            
            # 배치 처리기로 동기화 실행
            result = await wholesaler_batch_processor.batch_processor.process_batch(
                items=sync_tasks,
                processor_func=_sync_platform_orders,
                config=batch_config,
                batch_id="platform_sync"
            )
            
            # 캐시 무효화
            enhanced_cache_manager.flush_namespace("orders_optimized")
            enhanced_cache_manager.flush_namespace("analytics")
            
            return {
                "success": result.error_count == 0,
                "message": f"동기화 완료: {result.success_count} 성공, {result.error_count} 실패",
                "synced_platforms": len(platforms_to_sync),
                "execution_time": result.execution_time,
                "throughput": f"{result.throughput:.2f} platforms/sec",
                "errors": result.errors
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"외부 주문 동기화 실패: {str(e)}"
            )


async def _sync_platform_orders(sync_task: Dict[str, Any], connection_manager) -> Dict[str, Any]:
    """단일 플랫폼 주문 동기화"""
    platform = sync_task["platform"]
    since = sync_task["since"]
    
    try:
        # 플랫폼별 동기화 로직
        if platform == "coupang":
            return await _sync_coupang_orders(since, connection_manager)
        elif platform == "naver":
            return await _sync_naver_orders(since, connection_manager)
        elif platform == "11st":
            return await _sync_11st_orders(since, connection_manager)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
            
    except Exception as e:
        logger.error(f"Platform {platform} sync failed: {e}")
        raise


async def _sync_coupang_orders(since: datetime, connection_manager) -> Dict[str, Any]:
    """쿠팡 주문 동기화"""
    session = await connection_manager.get_session("coupang")
    
    # 쿠팡 API 호출 로직
    # 실제 구현은 쿠팡 API 문서에 따라 작성
    
    return {
        "platform": "coupang",
        "synced_orders": 0,
        "new_orders": 0,
        "updated_orders": 0
    }


async def _sync_naver_orders(since: datetime, connection_manager) -> Dict[str, Any]:
    """네이버 주문 동기화"""
    session = await connection_manager.get_session("naver")
    
    # 네이버 API 호출 로직
    
    return {
        "platform": "naver",
        "synced_orders": 0,
        "new_orders": 0,
        "updated_orders": 0
    }


async def _sync_11st_orders(since: datetime, connection_manager) -> Dict[str, Any]:
    """11번가 주문 동기화"""
    session = await connection_manager.get_session("11st")
    
    # 11번가 API 호출 로직
    
    return {
        "platform": "11st",
        "synced_orders": 0,
        "new_orders": 0,
        "updated_orders": 0
    }


@router.get("/analytics/performance")
async def get_order_performance_analytics(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 성능 분석 (최적화됨)"""
    
    cache_config = CacheConfig(
        ttl=300,  # 5분 캐시
        namespace="analytics",
        compression_enabled=True
    )
    
    cache_key = f"order_performance:{days}"
    
    # 캐시 확인
    cached_result = enhanced_cache_manager.get(cache_key, cache_config)
    if cached_result:
        return cached_result
    
    async with performance_monitor.track_operation("order_performance_analytics"):
        date_range = {
            "start_date": datetime.now() - timedelta(days=days),
            "end_date": datetime.now()
        }
        
        # 최적화된 분석 쿼리
        analytics_data = await db_optimizer.get_dashboard_analytics_optimized(
            db=db,
            date_range=date_range
        )
        
        # 성능 메트릭 추가
        performance_data = performance_monitor.get_performance_report()
        cache_stats = enhanced_cache_manager.get_performance_stats()
        
        result = {
            **analytics_data,
            "performance_metrics": {
                "database_performance": db_optimizer.get_performance_stats(),
                "cache_performance": cache_stats,
                "api_performance": performance_data
            },
            "optimization_recommendations": _generate_optimization_recommendations(
                analytics_data, performance_data, cache_stats
            )
        }
        
        # 결과 캐시
        enhanced_cache_manager.set(cache_key, result, cache_config)
        
        return result


def _generate_optimization_recommendations(
    analytics_data: Dict[str, Any],
    performance_data: Dict[str, Any],
    cache_stats: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """최적화 추천 생성"""
    recommendations = []
    
    # 히트율 기반 추천
    hit_rate = cache_stats.get("hit_rate_percent", 0)
    if hit_rate < 80:
        recommendations.append({
            "type": "cache_optimization",
            "priority": "high",
            "message": f"캐시 히트율이 {hit_rate:.1f}%로 낮습니다. TTL 조정이나 캐시 워밍업을 고려하세요.",
            "action": "increase_cache_ttl"
        })
    
    # 응답 시간 기반 추천
    avg_response_time = performance_data.get("get_orders_optimized", {}).get("avg_time", 0)
    if avg_response_time > 0.2:  # 200ms
        recommendations.append({
            "type": "query_optimization",
            "priority": "high",
            "message": f"주문 조회 응답 시간이 {avg_response_time:.3f}초로 느립니다. 인덱스 추가를 고려하세요.",
            "action": "add_database_indexes"
        })
    
    # 데이터 볼륨 기반 추천
    total_orders = analytics_data.get("order_stats", {}).get("total_orders", 0)
    if total_orders > 10000:
        recommendations.append({
            "type": "scaling",
            "priority": "medium",
            "message": "주문 데이터가 대량입니다. 파티셔닝이나 아카이빙을 고려하세요.",
            "action": "implement_data_partitioning"
        })
    
    return recommendations


@router.get("/health/performance")
async def get_orders_performance_health():
    """주문 API 성능 상태 확인"""
    
    # 각 시스템의 성능 지표 수집
    db_stats = db_optimizer.get_performance_stats()
    cache_stats = enhanced_cache_manager.get_performance_stats()
    api_stats = performance_monitor.get_performance_report()
    
    # 전체 성능 점수 계산
    overall_score = (
        db_stats.get("performance_score", 5) * 0.4 +
        cache_stats.get("performance_score", 5) * 0.4 +
        min(10, max(1, 10 - (api_stats.get("get_orders_optimized", {}).get("avg_time", 0.1) * 50))) * 0.2
    )
    
    # 상태 결정
    if overall_score >= 8:
        status = "excellent"
    elif overall_score >= 6:
        status = "good"
    elif overall_score >= 4:
        status = "fair"
    else:
        status = "poor"
    
    return {
        "status": status,
        "overall_score": round(overall_score, 2),
        "component_scores": {
            "database": db_stats.get("performance_score", 5),
            "cache": cache_stats.get("performance_score", 5),
            "api_response": min(10, max(1, 10 - (api_stats.get("get_orders_optimized", {}).get("avg_time", 0.1) * 50)))
        },
        "detailed_metrics": {
            "database": db_stats,
            "cache": cache_stats,
            "api": api_stats
        },
        "timestamp": datetime.now().isoformat()
    }


import asyncio
import logging

logger = logging.getLogger(__name__)