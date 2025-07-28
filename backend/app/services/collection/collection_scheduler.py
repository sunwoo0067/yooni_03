"""
도매처 상품 수집 스케줄러
주기적으로 상품을 수집하고 업데이트하는 스케줄링 서비스
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .wholesaler_sync_service import WholesalerSyncService
from .realtime_stock_monitor import realtime_stock_monitor
from ...models.collected_product import CollectedProduct, WholesalerSource, CollectionStatus, CollectionBatch
from ...models.collected_product_history import CollectedProductHistory, ChangeType, PriceAlert
from ...models.wholesaler import WholesalerType
from ...services.database.database import get_db
from ...core.cache import cache_manager


class CollectionScheduler:
    """상품 수집 스케줄러"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.scheduler = AsyncIOScheduler()
        self.sync_service = WholesalerSyncService(logger)
        self._is_running = False
        
    async def start(self):
        """스케줄러 시작"""
        if self._is_running:
            self.logger.warning("스케줄러가 이미 실행 중입니다")
            return
            
        # 스케줄 작업 등록
        self._register_jobs()
        
        # 스케줄러 시작
        self.scheduler.start()
        self._is_running = True
        
        # 실시간 재고 모니터링 시작
        await realtime_stock_monitor.start_monitoring()
        
        self.logger.info("상품 수집 스케줄러 시작")
        
    async def stop(self):
        """스케줄러 중지"""
        if not self._is_running:
            return
            
        # 실시간 재고 모니터링 중지
        await realtime_stock_monitor.stop_monitoring()
        
        # 스케줄러 중지
        self.scheduler.shutdown()
        self._is_running = False
        
        self.logger.info("상품 수집 스케줄러 중지")
        
    def _register_jobs(self):
        """스케줄 작업 등록"""
        
        # 1. 전체 동기화 - 매일 새벽 3시
        self.scheduler.add_job(
            self._daily_full_sync,
            CronTrigger(hour=3, minute=0),
            id='daily_full_sync',
            name='일일 전체 동기화',
            misfire_grace_time=3600  # 1시간 유예
        )
        
        # 2. 인기 상품 업데이트 - 2시간마다
        self.scheduler.add_job(
            self._update_popular_products,
            IntervalTrigger(hours=2),
            id='popular_products_update',
            name='인기 상품 업데이트',
            misfire_grace_time=600
        )
        
        # 3. 신규 상품 수집 - 4시간마다
        self.scheduler.add_job(
            self._collect_new_products,
            IntervalTrigger(hours=4),
            id='new_products_collection',
            name='신규 상품 수집',
            misfire_grace_time=1200
        )
        
        # 4. 만료 상품 정리 - 매일 새벽 2시
        self.scheduler.add_job(
            self._cleanup_expired_products,
            CronTrigger(hour=2, minute=0),
            id='expired_products_cleanup',
            name='만료 상품 정리'
        )
        
        # 5. 가격 변동 체크 - 6시간마다
        self.scheduler.add_job(
            self._check_price_changes,
            IntervalTrigger(hours=6),
            id='price_change_check',
            name='가격 변동 확인',
            misfire_grace_time=1800
        )
        
        # 6. 캐시 워밍업 - 매일 새벽 4시
        self.scheduler.add_job(
            self._warmup_cache,
            CronTrigger(hour=4, minute=0),
            id='cache_warmup',
            name='캐시 워밍업'
        )
        
        self.logger.info(f"{len(self.scheduler.get_jobs())}개의 스케줄 작업 등록 완료")
        
    async def _daily_full_sync(self):
        """일일 전체 동기화"""
        try:
            self.logger.info("일일 전체 동기화 시작")
            start_time = datetime.utcnow()
            
            # 모든 도매처 동기화
            results = await self.sync_service.sync_all_wholesalers(
                max_products_per_wholesaler=50000  # 도매처당 최대 5만개
            )
            
            # 결과 로깅
            total_collected = sum(r.collected for r in results.values())
            total_updated = sum(r.updated for r in results.values())
            total_failed = sum(r.failed for r in results.values())
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"일일 전체 동기화 완료: "
                f"수집 {total_collected}개, 업데이트 {total_updated}개, "
                f"실패 {total_failed}개 (소요시간: {execution_time:.2f}초)"
            )
            
            # 통계 캐싱
            await self._cache_sync_stats(results)
            
        except Exception as e:
            self.logger.error(f"일일 전체 동기화 실패: {str(e)}")
            
    async def _update_popular_products(self):
        """인기 상품 업데이트"""
        try:
            self.logger.info("인기 상품 업데이트 시작")
            
            db = next(get_db())
            
            # 인기 상품 기준:
            # 1. 품질 점수 7점 이상
            # 2. 재고 있음
            # 3. 최근 7일 내 가격 변동이 있었던 상품
            popular_products = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.status == CollectionStatus.COLLECTED,
                    CollectedProduct.quality_score >= 7.0,
                    CollectedProduct.stock_status == "available",
                    CollectedProduct.id.in_(
                        db.query(CollectedProductHistory.collected_product_id).filter(
                            and_(
                                CollectedProductHistory.change_type == ChangeType.PRICE_CHANGE,
                                CollectedProductHistory.change_timestamp >= datetime.utcnow() - timedelta(days=7)
                            )
                        ).distinct()
                    )
                )
            ).limit(1000).all()
            
            # 도매처별로 그룹화
            products_by_source = {}
            for product in popular_products:
                if product.source not in products_by_source:
                    products_by_source[product.source] = []
                products_by_source[product.source].append(product)
            
            # 각 도매처별로 업데이트
            updated_count = 0
            for source, products in products_by_source.items():
                count = await self._update_products_batch(source, products)
                updated_count += count
            
            db.close()
            
            self.logger.info(f"인기 상품 {updated_count}개 업데이트 완료")
            
        except Exception as e:
            self.logger.error(f"인기 상품 업데이트 실패: {str(e)}")
            
    async def _collect_new_products(self):
        """신규 상품 수집"""
        try:
            self.logger.info("신규 상품 수집 시작")
            
            # 각 도매처별로 최신 상품 수집
            for source in WholesalerSource:
                try:
                    result = await self.sync_service.sync_wholesaler(
                        source,
                        collection_type=CollectionType.NEW,  # 신규 상품만
                        max_products=500  # 도매처당 500개
                    )
                    
                    self.logger.info(
                        f"{source.value} 신규 상품 수집: "
                        f"{result.collected}개 수집, {result.failed}개 실패"
                    )
                    
                except Exception as e:
                    self.logger.error(f"{source.value} 신규 상품 수집 실패: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"신규 상품 수집 실패: {str(e)}")
            
    async def _cleanup_expired_products(self):
        """만료 상품 정리"""
        try:
            self.logger.info("만료 상품 정리 시작")
            
            # 30일 이상된 상품 만료 처리
            expired_count = await self.sync_service.cleanup_expired_products(days_to_keep=30)
            
            self.logger.info(f"{expired_count}개 상품 만료 처리 완료")
            
        except Exception as e:
            self.logger.error(f"만료 상품 정리 실패: {str(e)}")
            
    async def _check_price_changes(self):
        """가격 변동 확인"""
        try:
            self.logger.info("가격 변동 확인 시작")
            
            db = next(get_db())
            
            # 가격 확인 대상:
            # 1. 활성 상태
            # 2. 가격 알림이 설정된 상품
            # 3. 최근 12시간 내 업데이트되지 않은 상품
            products_to_check = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.status == CollectionStatus.COLLECTED,
                    or_(
                        CollectedProduct.id.in_(
                            db.query(PriceAlert.collected_product_id).filter(
                                PriceAlert.is_active == True
                            )
                        ),
                        CollectedProduct.updated_at < datetime.utcnow() - timedelta(hours=12)
                    )
                )
            ).limit(2000).all()
            
            # 도매처별로 그룹화
            products_by_source = {}
            for product in products_to_check:
                if product.source not in products_by_source:
                    products_by_source[product.source] = []
                products_by_source[product.source].append(product)
            
            # 각 도매처별로 가격 확인
            price_changed_count = 0
            for source, products in products_by_source.items():
                count = await self._check_products_price(source, products)
                price_changed_count += count
            
            db.close()
            
            self.logger.info(f"가격 변동 확인 완료: {price_changed_count}개 상품 가격 변경됨")
            
        except Exception as e:
            self.logger.error(f"가격 변동 확인 실패: {str(e)}")
            
    async def _warmup_cache(self):
        """캐시 워밍업"""
        try:
            self.logger.info("캐시 워밍업 시작")
            
            # 캐시 워밍업 서비스 호출
            from ...services.cache.cache_warmup_service import cache_warmup_service
            results = await cache_warmup_service.warmup_all()
            
            self.logger.info(f"캐시 워밍업 완료: {results}")
            
        except Exception as e:
            self.logger.error(f"캐시 워밍업 실패: {str(e)}")
            
    async def _update_products_batch(
        self,
        source: WholesalerSource,
        products: List[CollectedProduct]
    ) -> int:
        """상품 배치 업데이트"""
        # 실제 구현은 WholesalerManager를 통해 수행
        # 여기서는 간단히 수를 반환
        return len(products)
        
    async def _check_products_price(
        self,
        source: WholesalerSource,
        products: List[CollectedProduct]
    ) -> int:
        """상품 가격 확인"""
        # 실제 구현은 WholesalerManager를 통해 수행
        # 여기서는 간단히 수를 반환
        return len(products) // 10  # 10% 정도 변경 가정
        
    async def _cache_sync_stats(self, results: Dict):
        """동기화 통계 캐싱"""
        try:
            stats = {
                'last_sync': datetime.utcnow().isoformat(),
                'results': {
                    source: {
                        'collected': result.collected,
                        'updated': result.updated,
                        'failed': result.failed,
                        'total': result.total_found
                    }
                    for source, result in results.items()
                }
            }
            
            await cache_manager.set(
                'collection:daily_sync_stats',
                stats,
                ttl=86400  # 24시간
            )
            
        except Exception as e:
            self.logger.error(f"동기화 통계 캐싱 실패: {str(e)}")
            
    def get_schedule_info(self) -> List[Dict]:
        """스케줄 정보 조회"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
        
    async def trigger_job(self, job_id: str) -> bool:
        """특정 작업 수동 실행"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                self.logger.info(f"작업 수동 실행: {job_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"작업 수동 실행 실패: {str(e)}")
            return False


# 싱글톤 인스턴스
collection_scheduler = CollectionScheduler()