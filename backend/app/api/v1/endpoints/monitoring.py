"""
모니터링 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from datetime import datetime

from app.core.cache import cache_manager
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.services.cache.cache_warmup_service import cache_warmup_service
from app.services.cache.adaptive_ttl_service import adaptive_ttl_service
from app.core.cache_cluster import ClusterCacheManager

router = APIRouter()


@router.get("/cache/stats")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    캐시 통계 정보 조회
    
    Returns:
        캐시 히트율, 요청 수, 압축 통계 등의 정보
    """
    stats = cache_manager.get_stats()
    stats["timestamp"] = datetime.utcnow().isoformat()
    
    # 압축 통계가 있는 경우 포맷팅
    if "compression" in stats:
        compression = stats["compression"]
        if compression["compressed_count"] > 0:
            saved_bytes = compression["total_original_size"] - compression["total_compressed_size"]
            saved_percentage = (saved_bytes / compression["total_original_size"]) * 100
            compression["space_saved_bytes"] = saved_bytes
            compression["space_saved_percentage"] = f"{saved_percentage:.2f}%"
            compression["avg_compression_ratio_percentage"] = f"{compression['avg_compression_ratio'] * 100:.2f}%"
    
    return stats


@router.post("/cache/stats/reset")
async def reset_cache_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    캐시 통계 초기화
    
    Returns:
        초기화 성공 메시지
    """
    # 관리자 권한 체크
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    cache_manager.reset_stats()
    return {
        "message": "Cache statistics reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/cache/warmup")
async def trigger_cache_warmup(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    캐시 워밍업 수동 실행
    
    Returns:
        워밍업 실행 결과
    """
    # 관리자 권한 체크
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        results = await cache_warmup_service.warmup_all()
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache warmup failed: {str(e)}"
        )


@router.get("/health/detailed")
async def get_detailed_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    상세 시스템 헬스 체크
    
    Returns:
        시스템 각 구성 요소의 상태 정보
    """
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "cache": {
            "connected": cache_manager._connected,
            "stats": cache_manager.get_stats()
        },
        "database": {
            "status": "healthy"  # TODO: 실제 DB 헬스체크 구현
        },
        "services": {
            "ai": "operational",
            "platforms": "operational"
        }
    }
    
    return health_status


@router.get("/cache/ttl/patterns")
async def get_ttl_patterns(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    적응형 TTL 패턴 통계 조회
    
    Returns:
        캐시 접근 패턴 및 TTL 조정 정보
    """
    return adaptive_ttl_service.get_all_patterns_summary()


@router.get("/cache/ttl/pattern/{cache_key}")
async def get_specific_ttl_pattern(
    cache_key: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    특정 캐시 키의 TTL 패턴 조회
    
    Args:
        cache_key: 조회할 캐시 키
        
    Returns:
        해당 캐시 키의 접근 패턴 및 TTL 정보
    """
    stats = adaptive_ttl_service.get_pattern_stats(cache_key)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pattern data found for cache key: {cache_key}"
        )
    return stats


@router.post("/cache/ttl/cleanup")
async def cleanup_stale_ttl_patterns(
    days: int = 7,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    오래된 TTL 패턴 데이터 정리
    
    Args:
        days: 정리할 기준 일수 (기본 7일)
        
    Returns:
        정리된 패턴 수
    """
    # 관리자 권한 체크
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    cleaned = adaptive_ttl_service.cleanup_stale_patterns(days)
    return {
        "cleaned_patterns": cleaned,
        "message": f"Cleaned up patterns older than {days} days",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/cache/cluster/info")
async def get_cache_cluster_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Redis Cluster 정보 조회
    
    Returns:
        클러스터 상태, 노드 정보 등
    """
    # 클러스터 매니저인지 확인
    if isinstance(cache_manager, ClusterCacheManager):
        return await cache_manager.get_cluster_info()
    else:
        return {
            "cluster_enabled": False,
            "message": "Cache is not running in cluster mode"
        }