"""
백그라운드 캐시 갱신 서비스
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.cache import cache_manager
from app.api.v1.dependencies.database import get_db
from app.crud.product import product as product_crud
from app.schemas.product import ProductFilter, ProductSort
from app.models.product import Product

logger = logging.getLogger(__name__)


class CacheRefreshService:
    """백그라운드 캐시 갱신 서비스"""
    
    def __init__(self):
        self.refresh_interval = 300  # 5분마다 갱신
        self.is_running = False
        self._task = None
        
    async def start(self):
        """캐시 갱신 서비스 시작"""
        if self.is_running:
            logger.warning("Cache refresh service is already running")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("Cache refresh service started")
        
    async def stop(self):
        """캐시 갱신 서비스 중지"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cache refresh service stopped")
        
    async def _refresh_loop(self):
        """캐시 갱신 루프"""
        while self.is_running:
            try:
                await self._refresh_critical_caches()
                await asyncio.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"Cache refresh error: {e}")
                await asyncio.sleep(60)  # 에러 시 1분 후 재시도
                
    async def _refresh_critical_caches(self):
        """중요한 캐시들 갱신"""
        logger.info("Starting cache refresh cycle")
        refresh_count = 0
        
        try:
            db = next(get_db())
            
            # 1. 인기 상품 목록 갱신
            await self._refresh_popular_products(db)
            refresh_count += 1
            
            # 2. 최신 상품 목록 갱신
            await self._refresh_latest_products(db)
            refresh_count += 1
            
            # 3. 재고 부족 상품 갱신
            await self._refresh_low_stock_products(db)
            refresh_count += 1
            
            db.close()
            
            logger.info(f"Cache refresh completed. Refreshed {refresh_count} caches")
            
        except Exception as e:
            logger.error(f"Critical cache refresh failed: {e}")
            
    async def _refresh_popular_products(self, db: Session):
        """인기 상품 캐시 갱신"""
        try:
            # 인기 상품 쿼리 (featured 상품)
            filter_params = ProductFilter(
                status=["active"],
                is_featured=True,
                out_of_stock=False
            )
            
            products, total = product_crud.get_multi_filtered(
                db,
                filter_params=filter_params,
                sort=ProductSort.CREATED_DESC,
                skip=0,
                limit=20
            )
            
            # 캐시 키 생성
            cache_key = cache_manager._generate_key(
                "products_list",
                search=None,
                sku=None,
                status=["active"],
                product_type=None,
                brand=None,
                category_path=None,
                tags=None,
                platform_account_id=None,
                min_price=None,
                max_price=None,
                low_stock=None,
                out_of_stock=False,
                is_featured=True,
                sort=ProductSort.CREATED_DESC,
                page=1,
                size=20
            )
            
            # 캐시 갱신
            cache_data = {
                "items": [p.dict() for p in products],
                "total": total,
                "page": 1,
                "size": 20,
                "pages": (total + 19) // 20
            }
            
            await cache_manager.set(cache_key, cache_data, ttl=300)
            logger.debug("Popular products cache refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh popular products cache: {e}")
            
    async def _refresh_latest_products(self, db: Session):
        """최신 상품 캐시 갱신"""
        try:
            # 최신 상품 쿼리
            filter_params = ProductFilter(
                status=["active"],
                created_after=datetime.now() - timedelta(days=7)  # 최근 7일
            )
            
            products, total = product_crud.get_multi_filtered(
                db,
                filter_params=filter_params,
                sort=ProductSort.CREATED_DESC,
                skip=0,
                limit=20
            )
            
            # 캐시 키 생성 및 갱신
            cache_key = cache_manager._generate_key(
                "products_latest",
                days=7
            )
            
            cache_data = {
                "items": [p.dict() for p in products],
                "total": total,
                "timestamp": datetime.now().isoformat()
            }
            
            await cache_manager.set(cache_key, cache_data, ttl=300)
            logger.debug("Latest products cache refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh latest products cache: {e}")
            
    async def _refresh_low_stock_products(self, db: Session):
        """재고 부족 상품 캐시 갱신"""
        try:
            # 재고 부족 상품 쿼리
            filter_params = ProductFilter(
                status=["active"],
                low_stock=True
            )
            
            products, total = product_crud.get_multi_filtered(
                db,
                filter_params=filter_params,
                sort=ProductSort.STOCK_ASC,
                skip=0,
                limit=50
            )
            
            # 캐시 키 생성 및 갱신
            cache_key = cache_manager._generate_key(
                "products_low_stock",
                threshold=10
            )
            
            cache_data = {
                "items": [p.dict() for p in products],
                "total": total,
                "timestamp": datetime.now().isoformat()
            }
            
            await cache_manager.set(cache_key, cache_data, ttl=180)  # 3분
            logger.debug("Low stock products cache refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh low stock products cache: {e}")
            
    async def refresh_specific_cache(self, cache_type: str, params: Dict[str, Any] = None):
        """특정 캐시 즉시 갱신"""
        try:
            db = next(get_db())
            
            if cache_type == "popular_products":
                await self._refresh_popular_products(db)
            elif cache_type == "latest_products":
                await self._refresh_latest_products(db)
            elif cache_type == "low_stock_products":
                await self._refresh_low_stock_products(db)
            else:
                raise ValueError(f"Unknown cache type: {cache_type}")
                
            db.close()
            logger.info(f"Successfully refreshed {cache_type} cache")
            
        except Exception as e:
            logger.error(f"Failed to refresh {cache_type} cache: {e}")
            raise


# 싱글톤 인스턴스
cache_refresh_service = CacheRefreshService()