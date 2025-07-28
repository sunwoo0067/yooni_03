"""
적응형 TTL 서비스 - 사용 패턴에 따라 캐시 TTL을 자동 조정
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import math

from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class AdaptiveTTLService:
    """사용 패턴 기반 적응형 TTL 관리 서비스"""
    
    def __init__(self):
        # 캐시 키별 접근 패턴 추적
        self.access_patterns = defaultdict(lambda: {
            "access_count": 0,
            "last_access": None,
            "access_intervals": [],  # 접근 간격 리스트
            "current_ttl": 300,      # 기본 TTL 5분
            "recommended_ttl": 300
        })
        
        # TTL 범위 설정
        self.min_ttl = 60        # 최소 1분
        self.max_ttl = 3600      # 최대 1시간
        self.ttl_step = 60       # TTL 조정 단위 (1분)
        
        # 패턴 분석 설정
        self.pattern_window = 20  # 최근 20개 접근 패턴 분석
        self.adjustment_threshold = 0.3  # 30% 이상 차이날 때 조정
        
    def record_access(self, cache_key: str):
        """캐시 접근 기록"""
        pattern = self.access_patterns[cache_key]
        now = datetime.now()
        
        # 이전 접근 시간이 있으면 간격 계산
        if pattern["last_access"]:
            interval = (now - pattern["last_access"]).total_seconds()
            pattern["access_intervals"].append(interval)
            
            # 윈도우 크기 유지
            if len(pattern["access_intervals"]) > self.pattern_window:
                pattern["access_intervals"].pop(0)
        
        pattern["access_count"] += 1
        pattern["last_access"] = now
        
        # TTL 재계산
        self._recalculate_ttl(cache_key)
        
    def _recalculate_ttl(self, cache_key: str):
        """접근 패턴 기반 TTL 재계산"""
        pattern = self.access_patterns[cache_key]
        
        if len(pattern["access_intervals"]) < 3:
            # 충분한 데이터가 없으면 기본 TTL 유지
            return
            
        # 평균 접근 간격 계산
        avg_interval = sum(pattern["access_intervals"]) / len(pattern["access_intervals"])
        
        # 표준편차 계산 (접근 패턴의 일관성 확인)
        variance = sum((x - avg_interval) ** 2 for x in pattern["access_intervals"]) / len(pattern["access_intervals"])
        std_dev = math.sqrt(variance)
        
        # 변동계수 (Coefficient of Variation) 계산
        cv = std_dev / avg_interval if avg_interval > 0 else 1.0
        
        # 새로운 TTL 계산
        if cv < 0.5:  # 일관된 접근 패턴
            # 평균 간격의 1.5배로 설정 (여유 마진)
            new_ttl = int(avg_interval * 1.5)
        else:  # 불규칙한 접근 패턴
            # 평균 간격의 2배로 설정 (더 큰 여유)
            new_ttl = int(avg_interval * 2.0)
        
        # TTL 범위 제한
        new_ttl = max(self.min_ttl, min(self.max_ttl, new_ttl))
        
        # 단계별 조정 (급격한 변화 방지)
        new_ttl = round(new_ttl / self.ttl_step) * self.ttl_step
        
        # 임계값 확인 후 업데이트
        current_ttl = pattern["current_ttl"]
        if abs(new_ttl - current_ttl) / current_ttl > self.adjustment_threshold:
            pattern["recommended_ttl"] = new_ttl
            logger.info(f"TTL adjustment recommended for {cache_key}: {current_ttl}s -> {new_ttl}s")
            
    def get_recommended_ttl(self, cache_key: str) -> int:
        """캐시 키에 대한 권장 TTL 반환"""
        pattern = self.access_patterns.get(cache_key)
        if not pattern:
            return 300  # 기본값
            
        return pattern["recommended_ttl"]
        
    def apply_ttl_adjustment(self, cache_key: str) -> bool:
        """권장 TTL을 실제로 적용"""
        pattern = self.access_patterns.get(cache_key)
        if not pattern:
            return False
            
        if pattern["current_ttl"] != pattern["recommended_ttl"]:
            pattern["current_ttl"] = pattern["recommended_ttl"]
            return True
        return False
        
    def get_pattern_stats(self, cache_key: str) -> Dict[str, Any]:
        """특정 캐시 키의 패턴 통계 반환"""
        pattern = self.access_patterns.get(cache_key)
        if not pattern:
            return {}
            
        stats = {
            "access_count": pattern["access_count"],
            "last_access": pattern["last_access"].isoformat() if pattern["last_access"] else None,
            "current_ttl": pattern["current_ttl"],
            "recommended_ttl": pattern["recommended_ttl"],
            "avg_access_interval": None,
            "access_pattern_consistency": None
        }
        
        if pattern["access_intervals"]:
            avg_interval = sum(pattern["access_intervals"]) / len(pattern["access_intervals"])
            stats["avg_access_interval"] = round(avg_interval, 2)
            
            # 일관성 점수 (0-1, 높을수록 일관됨)
            if avg_interval > 0:
                variance = sum((x - avg_interval) ** 2 for x in pattern["access_intervals"]) / len(pattern["access_intervals"])
                cv = math.sqrt(variance) / avg_interval
                stats["access_pattern_consistency"] = round(1 / (1 + cv), 2)
                
        return stats
        
    def get_all_patterns_summary(self) -> Dict[str, Any]:
        """모든 캐시 패턴 요약 정보"""
        total_keys = len(self.access_patterns)
        total_accesses = sum(p["access_count"] for p in self.access_patterns.values())
        
        ttl_distribution = defaultdict(int)
        for pattern in self.access_patterns.values():
            ttl_bucket = (pattern["current_ttl"] // 300) * 300  # 5분 단위로 그룹화
            ttl_distribution[ttl_bucket] += 1
            
        return {
            "total_tracked_keys": total_keys,
            "total_accesses": total_accesses,
            "ttl_distribution": dict(ttl_distribution),
            "adjustment_pending": sum(
                1 for p in self.access_patterns.values() 
                if p["current_ttl"] != p["recommended_ttl"]
            )
        }
        
    def cleanup_stale_patterns(self, days: int = 7):
        """오래된 패턴 데이터 정리"""
        cutoff_time = datetime.now() - timedelta(days=days)
        keys_to_remove = []
        
        for key, pattern in self.access_patterns.items():
            if pattern["last_access"] and pattern["last_access"] < cutoff_time:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.access_patterns[key]
            
        logger.info(f"Cleaned up {len(keys_to_remove)} stale cache patterns")
        return len(keys_to_remove)


# 싱글톤 인스턴스
adaptive_ttl_service = AdaptiveTTLService()


# 캐시 데코레이터 수정을 위한 래퍼
def cache_result_with_adaptive_ttl(prefix: str, initial_ttl: int = 300):
    """적응형 TTL을 사용하는 캐시 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # 접근 기록
            adaptive_ttl_service.record_access(cache_key)
            
            # 캐시 조회
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
                
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 적응형 TTL 가져오기
            ttl = adaptive_ttl_service.get_recommended_ttl(cache_key)
            
            # 결과 캐싱
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator