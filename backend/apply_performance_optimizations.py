#!/usr/bin/env python3
"""
드롭쉬핑 시스템 성능 최적화 적용 스크립트
데이터베이스 인덱스, 캐시 설정, API 최적화를 자동으로 적용
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List

# 프로젝트 모듈 import
sys.path.append('.')

from app.core.config import settings
from app.services.database.database import engine, async_engine, db_manager
from app.models.performance_indexes import create_performance_indexes
from app.services.performance.enhanced_cache_manager import enhanced_cache_manager
from app.services.performance.database_optimizer import db_optimizer
from app.services.performance.async_batch_processor import wholesaler_batch_processor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('performance_optimization.log')
    ]
)
logger = logging.getLogger(__name__)


class PerformanceOptimizationMigrator:
    """성능 최적화 마이그레이션"""
    
    def __init__(self):
        self.optimization_steps = [
            ("데이터베이스 인덱스 생성", self.create_database_indexes),
            ("캐시 시스템 초기화", self.initialize_cache_system),
            ("연결 풀 최적화", self.optimize_connection_pools),
            ("성능 모니터링 설정", self.setup_performance_monitoring),
            ("기본 캐시 데이터 로딩", self.warm_up_cache),
            ("최적화 검증", self.verify_optimizations)
        ]
        
        self.results = {
            "started_at": datetime.now().isoformat(),
            "steps": {},
            "overall_success": False,
            "errors": [],
            "warnings": []
        }
    
    async def run_optimization(self) -> Dict[str, Any]:
        """전체 최적화 프로세스 실행"""
        logger.info("=== 드롭쉬핑 시스템 성능 최적화 시작 ===")
        
        try:
            for step_name, step_func in self.optimization_steps:
                logger.info(f"단계 실행: {step_name}")
                
                try:
                    step_result = await step_func()
                    self.results["steps"][step_name] = {
                        "success": True,
                        "result": step_result,
                        "completed_at": datetime.now().isoformat()
                    }
                    logger.info(f"✅ {step_name} 완료")
                    
                except Exception as e:
                    error_msg = f"{step_name} 실패: {str(e)}"
                    logger.error(error_msg)
                    self.results["steps"][step_name] = {
                        "success": False,
                        "error": str(e),
                        "completed_at": datetime.now().isoformat()
                    }
                    self.results["errors"].append(error_msg)
            
            # 전체 성공 여부 결정
            successful_steps = sum(1 for step in self.results["steps"].values() if step["success"])
            total_steps = len(self.optimization_steps)
            
            self.results["overall_success"] = successful_steps == total_steps
            self.results["success_rate"] = successful_steps / total_steps * 100
            
            logger.info(f"=== 최적화 완료: {successful_steps}/{total_steps} 단계 성공 ===")
            
        except Exception as e:
            logger.error(f"최적화 프로세스 중 치명적 오류: {e}")
            self.results["fatal_error"] = str(e)
        
        finally:
            self.results["completed_at"] = datetime.now().isoformat()
            await self.cleanup()
        
        return self.results
    
    async def create_database_indexes(self) -> Dict[str, Any]:
        """데이터베이스 성능 인덱스 생성"""
        logger.info("데이터베이스 인덱스 생성 중...")
        
        try:
            # 동기 엔진으로 인덱스 생성
            result = create_performance_indexes(engine)
            
            # 인덱스 사용량 통계 활성화 (PostgreSQL)
            if 'postgresql' in str(engine.url):
                with engine.connect() as conn:
                    try:
                        # pg_stat_statements 확장 활성화
                        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
                        logger.info("pg_stat_statements 확장 활성화됨")
                    except Exception as e:
                        logger.warning(f"pg_stat_statements 활성화 실패: {e}")
            
            return {
                "created_indexes": result["created_count"],
                "total_indexes": result["total_indexes"],
                "errors": result["errors"],
                "database_type": str(engine.url).split(':')[0]
            }
            
        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")
            raise
    
    async def initialize_cache_system(self) -> Dict[str, Any]:
        """캐시 시스템 초기화"""
        logger.info("캐시 시스템 초기화 중...")
        
        try:
            # Redis 연결 테스트
            test_key = "optimization_test"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            
            success = enhanced_cache_manager.set(test_key, test_value)
            if not success:
                raise Exception("Redis 연결 실패")
            
            retrieved = enhanced_cache_manager.get(test_key)
            if not retrieved:
                raise Exception("Redis 읽기 실패")
            
            # 테스트 키 삭제
            enhanced_cache_manager.delete(test_key)
            
            # 기본 의존성 규칙 확인
            from app.services.performance.enhanced_cache_manager import setup_default_dependency_rules
            setup_default_dependency_rules()
            
            # 네임스페이스별 TTL 최적화
            namespace_configs = {
                "products": {"ttl": 600},      # 10분
                "orders": {"ttl": 300},        # 5분
                "analytics": {"ttl": 1800},    # 30분
                "users": {"ttl": 3600},        # 1시간
                "inventory": {"ttl": 180},     # 3분
                "search": {"ttl": 900}         # 15분
            }
            
            return {
                "redis_connection": "success",
                "compression_enabled": enhanced_cache_manager.compression_enabled,
                "cluster_mode": enhanced_cache_manager.is_cluster if hasattr(enhanced_cache_manager, 'is_cluster') else False,
                "namespace_configs": namespace_configs,
                "dependency_rules": len(enhanced_cache_manager._dependency_graph)
            }
            
        except Exception as e:
            logger.error(f"캐시 시스템 초기화 실패: {e}")
            raise
    
    async def optimize_connection_pools(self) -> Dict[str, Any]:
        """연결 풀 최적화"""
        logger.info("연결 풀 최적화 중...")
        
        try:
            # 도매처 API 연결 풀 설정
            wholesaler_batch_processor._setup_connection_pools()
            
            # 각 풀 테스트
            pool_results = {}
            for pool_name in ["ownerclan", "zentrade", "domeggook"]:
                try:
                    session = await wholesaler_batch_processor.connection_manager.get_session(pool_name)
                    pool_results[pool_name] = {
                        "status": "configured",
                        "connector_limit": session.connector.limit,
                        "connector_limit_per_host": session.connector.limit_per_host
                    }
                except Exception as e:
                    pool_results[pool_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # 데이터베이스 연결 풀 확인
            db_pool_info = {
                "sync_pool_size": engine.pool.size(),
                "sync_pool_checked_in": engine.pool.checkedin(),
                "sync_pool_checked_out": engine.pool.checkedout(),
            }
            
            if async_engine:
                db_pool_info.update({
                    "async_pool_available": True,
                    "async_pool_size": async_engine.pool.size(),
                })
            
            return {
                "wholesaler_pools": pool_results,
                "database_pool": db_pool_info,
                "optimization_applied": True
            }
            
        except Exception as e:
            logger.error(f"연결 풀 최적화 실패: {e}")
            raise
    
    async def setup_performance_monitoring(self) -> Dict[str, Any]:
        """성능 모니터링 설정"""
        logger.info("성능 모니터링 설정 중...")
        
        try:
            # 모니터링 시스템 초기화
            from app.services.performance.async_batch_processor import performance_monitor
            
            # 초기 성능 기준선 설정
            baseline_metrics = {
                "api_response_time_target": 0.2,  # 200ms
                "database_query_time_target": 0.05,  # 50ms
                "cache_hit_rate_target": 0.8,  # 80%
                "error_rate_threshold": 0.05  # 5%
            }
            
            # 성능 지표 수집 시작
            performance_monitor.clear_metrics()
            
            # 데이터베이스 옵티마이저 초기화
            db_optimizer.clear_stats()
            
            return {
                "monitoring_enabled": True,
                "baseline_metrics": baseline_metrics,
                "performance_targets": {
                    "api_response_time": "< 200ms",
                    "database_query_time": "< 50ms",
                    "cache_hit_rate": "> 80%",
                    "concurrent_users": 100
                }
            }
            
        except Exception as e:
            logger.error(f"성능 모니터링 설정 실패: {e}")
            raise
    
    async def warm_up_cache(self) -> Dict[str, Any]:
        """캐시 워밍업"""
        logger.info("캐시 워밍업 중...")
        
        try:
            # 주요 캐시 데이터 사전 로딩
            cache_configs = {
                "categories": {
                    "data_loader": self._load_product_categories,
                    "ttl": 3600
                },
                "user_settings": {
                    "data_loader": self._load_user_settings,
                    "ttl": 1800
                },
                "system_config": {
                    "data_loader": self._load_system_config,
                    "ttl": 7200
                }
            }
            
            warmed_counts = enhanced_cache_manager.warm_up_cache(cache_configs)
            
            return {
                "warmed_namespaces": list(warmed_counts.keys()),
                "warmed_counts": warmed_counts,
                "total_warmed": sum(warmed_counts.values())
            }
            
        except Exception as e:
            logger.error(f"캐시 워밍업 실패: {e}")
            raise
    
    async def verify_optimizations(self) -> Dict[str, Any]:
        """최적화 검증"""
        logger.info("최적화 결과 검증 중...")
        
        try:
            verification_results = {}
            
            # 1. 데이터베이스 연결 테스트
            db_test = db_manager.check_connection()
            verification_results["database_connection"] = db_test
            
            if async_engine:
                async_db_test = await db_manager.check_connection_async()
                verification_results["async_database_connection"] = async_db_test
            
            # 2. 캐시 성능 테스트
            cache_stats = enhanced_cache_manager.get_performance_stats()
            verification_results["cache_system"] = {
                "operational": cache_stats.get("redis_memory_usage") != "Unknown",
                "l1_cache_size": cache_stats.get("l1_cache_size", 0),
                "compression_enabled": cache_stats.get("compression_efficiency") != "N/A"
            }
            
            # 3. API 연결 풀 테스트
            pool_tests = {}
            for pool_name in ["ownerclan", "zentrade", "domeggook"]:
                try:
                    session = await wholesaler_batch_processor.connection_manager.get_session(pool_name)
                    pool_tests[pool_name] = True
                except:
                    pool_tests[pool_name] = False
            
            verification_results["api_connection_pools"] = pool_tests
            
            # 4. 성능 기준 확인
            performance_check = {
                "database_optimizer": hasattr(db_optimizer, 'query_stats'),
                "cache_manager": hasattr(enhanced_cache_manager, '_memory_cache'),
                "performance_monitor": hasattr(performance_monitor, 'metrics')
            }
            verification_results["performance_systems"] = performance_check
            
            # 전체 성공 여부
            all_systems_ok = (
                verification_results["database_connection"] and
                verification_results["cache_system"]["operational"] and
                all(pool_tests.values()) and
                all(performance_check.values())
            )
            
            verification_results["overall_status"] = "success" if all_systems_ok else "partial"
            
            return verification_results
            
        except Exception as e:
            logger.error(f"최적화 검증 실패: {e}")
            raise
    
    def _load_product_categories(self) -> Dict[str, Any]:
        """상품 카테고리 데이터 로더"""
        return {
            "electronics": {"name": "전자제품", "priority": 1},
            "fashion": {"name": "패션", "priority": 2},
            "home": {"name": "홈&리빙", "priority": 3},
            "beauty": {"name": "뷰티", "priority": 4},
            "sports": {"name": "스포츠", "priority": 5}
        }
    
    def _load_user_settings(self) -> Dict[str, Any]:
        """사용자 설정 데이터 로더"""
        return {
            "default_margin": 30,
            "auto_price_update": True,
            "notification_enabled": True,
            "sync_interval": 3600
        }
    
    def _load_system_config(self) -> Dict[str, Any]:
        """시스템 설정 데이터 로더"""
        return {
            "maintenance_mode": False,
            "api_rate_limits": {
                "ownerclan": 60,
                "zentrade": 30,
                "domeggook": 100
            },
            "cache_ttl_defaults": {
                "products": 600,
                "orders": 300,
                "analytics": 1800
            }
        }
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            await wholesaler_batch_processor.cleanup()
            logger.info("리소스 정리 완료")
        except Exception as e:
            logger.warning(f"리소스 정리 중 오류: {e}")
    
    def generate_report(self) -> str:
        """최적화 보고서 생성"""
        report = []
        report.append("=" * 60)
        report.append("드롭쉬핑 시스템 성능 최적화 보고서")
        report.append("=" * 60)
        report.append(f"시작 시간: {self.results['started_at']}")
        report.append(f"완료 시간: {self.results.get('completed_at', 'N/A')}")
        report.append(f"전체 성공: {'✅' if self.results['overall_success'] else '❌'}")
        report.append(f"성공률: {self.results.get('success_rate', 0):.1f}%")
        report.append("")
        
        # 단계별 결과
        report.append("단계별 실행 결과:")
        report.append("-" * 40)
        for step_name, step_result in self.results["steps"].items():
            status = "✅" if step_result["success"] else "❌"
            report.append(f"{status} {step_name}")
            if not step_result["success"]:
                report.append(f"   오류: {step_result.get('error', 'Unknown')}")
        
        report.append("")
        
        # 성능 개선 사항
        report.append("적용된 성능 최적화:")
        report.append("-" * 40)
        report.append("• 데이터베이스 인덱스 최적화 (N+1 쿼리 해결)")
        report.append("• Redis 기반 2단계 캐싱 (L1 메모리 + L2 Redis)")
        report.append("• 압축 기반 캐시 저장 (메모리 절약)")
        report.append("• 비동기 배치 처리 (외부 API 최적화)")
        report.append("• 연결 풀링 (데이터베이스 + API)")
        report.append("• 실시간 성능 모니터링")
        report.append("")
        
        # 기대 효과
        report.append("기대 성능 개선 효과:")
        report.append("-" * 40)
        report.append("• API 응답 시간: 50-70% 향상 (< 200ms 목표)")
        report.append("• 데이터베이스 쿼리: 80-90% 향상 (< 50ms 목표)")
        report.append("• 캐시 히트율: > 80% 달성")
        report.append("• 동시 사용자: 100명 지원")
        report.append("• 메모리 사용량: 30-50% 절약")
        report.append("")
        
        # 에러 및 경고
        if self.results["errors"]:
            report.append("발생한 오류:")
            report.append("-" * 40)
            for error in self.results["errors"]:
                report.append(f"• {error}")
            report.append("")
        
        if self.results["warnings"]:
            report.append("경고 사항:")
            report.append("-" * 40)
            for warning in self.results["warnings"]:
                report.append(f"• {warning}")
            report.append("")
        
        # 다음 단계 권장사항
        report.append("다음 단계 권장사항:")
        report.append("-" * 40)
        report.append("1. 성능 모니터링 대시보드 확인")
        report.append("   → GET /api/v1/performance/overview")
        report.append("2. 실제 워크로드로 성능 테스트 실행")
        report.append("   → POST /api/v1/performance/benchmark")
        report.append("3. 정기적인 성능 리포트 검토")
        report.append("4. 필요시 추가 인덱스 또는 캐시 정책 조정")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


async def main():
    """메인 실행 함수"""
    print("🚀 드롭쉬핑 시스템 성능 최적화를 시작합니다...")
    print()
    
    migrator = PerformanceOptimizationMigrator()
    
    try:
        # 최적화 실행
        results = await migrator.run_optimization()
        
        # 보고서 생성 및 출력
        report = migrator.generate_report()
        print(report)
        
        # 파일로 저장
        report_filename = f"performance_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 상세 보고서가 저장되었습니다: {report_filename}")
        
        # 성공/실패에 따른 exit code
        if results["overall_success"]:
            print("\n🎉 성능 최적화가 성공적으로 완료되었습니다!")
            print("\n다음 명령어로 성능 상태를 확인할 수 있습니다:")
            print("curl http://localhost:8000/api/v1/performance/overview")
            return 0
        else:
            print("\n⚠️ 일부 최적화 단계에서 오류가 발생했습니다.")
            print("보고서를 확인하고 필요한 조치를 취하세요.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단되었습니다.")
        return 130
    except Exception as e:
        print(f"\n\n💥 치명적 오류 발생: {e}")
        logger.exception("Fatal error during optimization")
        return 1


if __name__ == "__main__":
    # 최적화 스크립트 실행
    exit_code = asyncio.run(main())
    sys.exit(exit_code)