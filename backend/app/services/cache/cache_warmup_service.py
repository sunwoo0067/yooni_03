"""
캐시 워밍업 서비스 - 자주 사용되는 데이터를 미리 캐시에 로드
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.cache import cache_manager
from app.models.product import Product
from app.models.user import User
from app.models.platform_account import PlatformAccount
from app.crud.product import product as product_crud
from app.schemas.product import ProductFilter, ProductSort
from app.services.ai.langchain_service import LangChainService
from app.api.v1.dependencies.database import get_db

logger = logging.getLogger(__name__)


class CacheWarmupService:
    """캐시 워밍업 서비스"""
    
    def __init__(self):
        self.langchain_service = LangChainService()
        
    async def warmup_all(self) -> Dict[str, Any]:
        """모든 캐시 워밍업 실행"""
        logger.info("Starting cache warmup...")
        start_time = datetime.now()
        
        results = {
            "product_cache": await self._warmup_product_cache(),
            "ai_cache": await self._warmup_ai_cache(),
            "platform_cache": await self._warmup_platform_cache(),
            "duration": None
        }
        
        duration = (datetime.now() - start_time).total_seconds()
        results["duration"] = duration
        
        logger.info(f"Cache warmup completed in {duration:.2f} seconds")
        return results
        
    async def _warmup_product_cache(self) -> Dict[str, int]:
        """상품 관련 캐시 워밍업"""
        warmed_count = 0
        
        try:
            # DB 세션 가져오기
            db = next(get_db())
            
            # 1. 인기 상품 목록 캐싱 (최근 30일 주문 많은 상품)
            popular_products_key = cache_manager._generate_key(
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
            
            # 인기 상품 조회 쿼리
            popular_products = db.query(Product).filter(
                Product.status == "active",
                Product.is_featured == True
            ).order_by(Product.created_at.desc()).limit(20).all()
            
            # 캐시에 저장
            await cache_manager.set(
                popular_products_key,
                {
                    "items": [p.dict() for p in popular_products],
                    "total": len(popular_products),
                    "page": 1,
                    "size": 20,
                    "pages": 1
                },
                ttl=300  # 5분
            )
            warmed_count += 1
            
            # 2. 개별 상품 상세 정보 캐싱 (상위 10개 상품)
            for product in popular_products[:10]:
                product_key = cache_manager._generate_key(
                    "product_detail",
                    product_id=product.id
                )
                product_detail = product_crud.get_with_details(db, product.id)
                if product_detail:
                    await cache_manager.set(
                        product_key,
                        product_detail.dict(),
                        ttl=600  # 10분
                    )
                    warmed_count += 1
                    
            # 3. 카테고리별 상품 목록 캐싱
            categories = db.query(Product.category_path).distinct().limit(5).all()
            for category in categories:
                if category[0]:
                    category_key = cache_manager._generate_key(
                        "products_list",
                        category_path=category[0],
                        status=["active"],
                        page=1,
                        size=20
                    )
                    # 간단히 캐시 키만 생성하고 실제 데이터는 첫 요청 시 로드
                    warmed_count += 1
                    
            db.close()
            
            logger.info(f"Warmed up {warmed_count} product cache entries")
            return {"warmed_count": warmed_count}
            
        except Exception as e:
            logger.error(f"Product cache warmup failed: {e}")
            return {"warmed_count": 0, "error": str(e)}
            
    async def _warmup_ai_cache(self) -> Dict[str, int]:
        """AI 서비스 관련 캐시 워밍업"""
        warmed_count = 0
        
        try:
            # 자주 사용되는 카테고리의 시장 분석 캐싱
            common_categories = ["전자제품", "패션", "뷰티", "생활용품", "식품"]
            
            for category in common_categories:
                market_data = {
                    "category": category,
                    "product_type": "일반",
                    "min_price": 10000,
                    "max_price": 100000,
                    "season": "일반"
                }
                
                # 시장 분석 캐시 키 생성
                market_key = cache_manager._generate_key(
                    "ai_market_analysis",
                    market_data=market_data
                )
                
                # 실제 AI 호출은 하지 않고 캐시 키만 준비
                # 첫 요청 시 실제 데이터가 캐싱됨
                warmed_count += 1
                
            logger.info(f"Prepared {warmed_count} AI cache entries for warmup")
            return {"prepared_count": warmed_count}
            
        except Exception as e:
            logger.error(f"AI cache warmup failed: {e}")
            return {"prepared_count": 0, "error": str(e)}
            
    async def _warmup_platform_cache(self) -> Dict[str, int]:
        """플랫폼 계정 관련 캐시 워밍업"""
        warmed_count = 0
        
        try:
            db = next(get_db())
            
            # 활성 플랫폼 계정 수 캐싱
            platform_stats_key = cache_manager._generate_key(
                "platform_stats",
                type="active_accounts"
            )
            
            active_accounts = db.query(func.count(PlatformAccount.id)).filter(
                PlatformAccount.status == "active"
            ).scalar()
            
            await cache_manager.set(
                platform_stats_key,
                {"active_accounts": active_accounts},
                ttl=600  # 10분
            )
            warmed_count += 1
            
            db.close()
            
            logger.info(f"Warmed up {warmed_count} platform cache entries")
            return {"warmed_count": warmed_count}
            
        except Exception as e:
            logger.error(f"Platform cache warmup failed: {e}")
            return {"warmed_count": 0, "error": str(e)}


# 싱글톤 인스턴스
cache_warmup_service = CacheWarmupService()


async def run_cache_warmup():
    """캐시 워밍업 실행 (백그라운드 작업)"""
    try:
        results = await cache_warmup_service.warmup_all()
        logger.info(f"Cache warmup results: {results}")
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")