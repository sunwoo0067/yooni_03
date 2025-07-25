"""
성능 최적화 및 모니터링 API 엔드포인트
시스템 성능 관리, 캐시 관리, 모니터링 대시보드
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime

from ....services.database.database import get_db
from ....services.performance.performance_optimizer import PerformanceOptimizer
from ....services.performance.cache_manager import CacheManager, cache_invalidator
from ....services.performance.monitoring_service import get_monitoring_service

router = APIRouter()

# ==== 성능 최적화 API ====

@router.get("/optimize/system", tags=["성능 최적화"])
async def optimize_system_performance(
    include_database: bool = Query(True, description="데이터베이스 최적화 포함"),
    include_memory: bool = Query(True, description="메모리 최적화 포함"),
    include_cache: bool = Query(True, description="캐시 최적화 포함"),
    db: Session = Depends(get_db)
):
    """종합 시스템 성능 최적화 실행"""
    try:
        optimizer = PerformanceOptimizer(db)
        
        optimization_results = {
            "start_time": datetime.now().isoformat(),
            "optimizations_performed": []
        }
        
        if include_database:
            db_result = optimizer.optimize_database_queries()
            optimization_results["database_optimization"] = db_result
            optimization_results["optimizations_performed"].append("database")
        
        if include_memory:
            memory_result = optimizer.optimize_memory_usage()
            optimization_results["memory_optimization"] = memory_result
            optimization_results["optimizations_performed"].append("memory")
        
        if include_cache:
            cache_result = optimizer.setup_caching_strategy()
            optimization_results["cache_optimization"] = cache_result
            optimization_results["optimizations_performed"].append("cache")
        
        # API 최적화는 항상 실행
        api_result = optimizer.optimize_api_performance()
        optimization_results["api_optimization"] = api_result
        optimization_results["optimizations_performed"].append("api")
        
        # 비동기 최적화
        async_result = await optimizer.optimize_async_operations()
        optimization_results["async_optimization"] = async_result
        optimization_results["optimizations_performed"].append("async")
        
        optimization_results["end_time"] = datetime.now().isoformat()
        optimization_results["status"] = "completed"
        
        return optimization_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최적화 실행 중 오류가 발생했습니다: {str(e)}")

@router.get("/metrics/system", tags=["성능 최적화"])
def get_system_metrics(db: Session = Depends(get_db)):
    """현재 시스템 성능 메트릭 조회"""
    try:
        optimizer = PerformanceOptimizer(db)
        metrics = optimizer.get_system_metrics()
        
        return {
            "timestamp": metrics.timestamp.isoformat(),
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "database_connections": metrics.database_connections,
            "redis_connections": metrics.redis_connections,
            "disk_io": metrics.disk_io,
            "network_io": metrics.network_io
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/performance/report", tags=["성능 최적화"])
def get_performance_report(
    hours: int = Query(24, ge=1, le=168, description="분석 기간 (시간)"),
    db: Session = Depends(get_db)
):
    """성능 분석 보고서 생성"""
    try:
        optimizer = PerformanceOptimizer(db)
        report = optimizer.generate_performance_report(hours)
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/performance/alerts", tags=["성능 최적화"])
def check_performance_alerts(db: Session = Depends(get_db)):
    """성능 알림 체크"""
    try:
        optimizer = PerformanceOptimizer(db)
        alerts = optimizer.monitor_performance_alerts()
        
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 체크 중 오류가 발생했습니다: {str(e)}")

# ==== 캐시 관리 API ====

@router.get("/cache/stats", tags=["캐시 관리"])
def get_cache_statistics():
    """캐시 통계 조회"""
    try:
        cache_manager = CacheManager()
        stats = cache_manager.get_cache_stats()
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 통계 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/cache/warm-up", tags=["캐시 관리"])
def warm_up_cache(
    cache_config: Dict[str, Any] = Body(..., description="캐시 워밍업 설정"),
):
    """캐시 워밍업 실행"""
    try:
        cache_manager = CacheManager()
        
        # 기본 워밍업 데이터 로더 함수들
        def load_products_cache():
            return {"sample_product": {"name": "테스트 상품", "price": 10000}}
        
        def load_categories_cache():
            return {"electronics": "전자제품", "fashion": "패션"}
        
        # 기본 설정이 없으면 기본값 사용
        if not cache_config:
            cache_config = {
                "products": {"data_loader": load_products_cache, "ttl": 3600},
                "categories": {"data_loader": load_categories_cache, "ttl": 7200}
            }
        
        warmed_counts = cache_manager.warm_up_cache(cache_config)
        
        return {
            "status": "completed",
            "warmed_namespaces": warmed_counts,
            "total_keys_warmed": sum(warmed_counts.values()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 워밍업 중 오류가 발생했습니다: {str(e)}")

@router.delete("/cache/namespace/{namespace}", tags=["캐시 관리"])
def flush_cache_namespace(namespace: str):
    """특정 네임스페이스 캐시 삭제"""
    try:
        cache_manager = CacheManager()
        deleted_count = cache_manager.flush_namespace(namespace)
        
        return {
            "namespace": namespace,
            "deleted_keys": deleted_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 삭제 중 오류가 발생했습니다: {str(e)}")

@router.post("/cache/invalidate", tags=["캐시 관리"])
def invalidate_cache_by_trigger(trigger: str = Body(..., embed=True)):
    """트리거에 의한 캐시 무효화"""
    try:
        invalidated_counts = cache_invalidator.invalidate_by_trigger(trigger)
        
        return {
            "trigger": trigger,
            "invalidated_namespaces": invalidated_counts,
            "total_keys_invalidated": sum(invalidated_counts.values()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 무효화 중 오류가 발생했습니다: {str(e)}")

@router.get("/cache/key/{namespace}/{key}", tags=["캐시 관리"])
def get_cache_value(namespace: str, key: str):
    """특정 캐시 값 조회"""
    try:
        cache_manager = CacheManager()
        value = cache_manager.get(key, namespace)
        
        if value is None:
            raise HTTPException(status_code=404, detail="캐시 키를 찾을 수 없습니다")
        
        return {
            "namespace": namespace,
            "key": key,
            "value": value,
            "ttl": cache_manager.get_ttl(key, namespace),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 조회 중 오류가 발생했습니다: {str(e)}")

@router.put("/cache/key/{namespace}/{key}", tags=["캐시 관리"])
def set_cache_value(
    namespace: str,
    key: str,
    value: Any = Body(...),
    ttl: Optional[int] = Body(None, description="TTL (초)")
):
    """캐시 값 설정"""
    try:
        cache_manager = CacheManager()
        success = cache_manager.set(key, value, ttl, namespace)
        
        if not success:
            raise HTTPException(status_code=500, detail="캐시 설정에 실패했습니다")
        
        return {
            "namespace": namespace,
            "key": key,
            "value": value,
            "ttl": ttl or cache_manager.default_ttl,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 설정 중 오류가 발생했습니다: {str(e)}")

@router.delete("/cache/key/{namespace}/{key}", tags=["캐시 관리"])
def delete_cache_value(namespace: str, key: str):
    """특정 캐시 키 삭제"""
    try:
        cache_manager = CacheManager()
        success = cache_manager.delete(key, namespace)
        
        return {
            "namespace": namespace,
            "key": key,
            "deleted": success,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 삭제 중 오류가 발생했습니다: {str(e)}")

# ==== 모니터링 API ====

@router.get("/monitoring/dashboard", tags=["모니터링"])
def get_monitoring_dashboard(db: Session = Depends(get_db)):
    """모니터링 대시보드 데이터 조회"""
    try:
        monitoring_service = get_monitoring_service(db)
        dashboard_data = monitoring_service.get_monitoring_dashboard()
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/monitoring/alerts/{alert_id}/acknowledge", tags=["모니터링"])
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    """알림 확인 처리"""
    try:
        monitoring_service = get_monitoring_service(db)
        success = monitoring_service.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        return {
            "alert_id": alert_id,
            "acknowledged": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 확인 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/monitoring/alerts/{alert_id}/resolve", tags=["모니터링"])
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    """알림 해결 처리"""
    try:
        monitoring_service = get_monitoring_service(db)
        success = monitoring_service.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        return {
            "alert_id": alert_id,
            "resolved": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 해결 처리 중 오류가 발생했습니다: {str(e)}")

# ==== 헬스체크 API ====

@router.get("/health", tags=["헬스체크"])
def health_check():
    """기본 헬스체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "yooni_dropshipping_system"
    }

@router.get("/health/detailed", tags=["헬스체크"])
def detailed_health_check(db: Session = Depends(get_db)):
    """상세 헬스체크"""
    try:
        health_status = {
            "overall_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # 데이터베이스 체크
        try:
            db.execute("SELECT 1")
            health_status["services"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0  # 실제로는 측정해야 함
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Redis 체크
        try:
            cache_manager = CacheManager()
            cache_manager.redis_client.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "response_time_ms": 0
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# ==== 시스템 정보 API ====

@router.get("/system/info", tags=["시스템 정보"])
def get_system_info():
    """시스템 정보 조회"""
    try:
        import psutil
        import platform
        
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
                "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percentage": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percentage": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/system/gc", tags=["시스템 정보"])
def force_garbage_collection():
    """가비지 컬렉션 강제 실행"""
    try:
        import gc
        
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        return {
            "objects_before": before_count,
            "objects_after": after_count,
            "objects_collected": collected,
            "objects_freed": before_count - after_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가비지 컬렉션 실행 중 오류가 발생했습니다: {str(e)}")