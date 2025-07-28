"""
실제 재고 동기화 서비스

도매처와 마켓플레이스 간의 재고를 실시간으로 동기화
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.product import Product
from app.models.inventory import Inventory, InventoryHistory
from app.models.collected_product import CollectedProduct
from app.services.wholesalers.wholesaler_manager import WholesalerManager
from app.services.platforms.platform_manager import PlatformManager
from app.core.exceptions import AppException


@dataclass
class InventorySyncResult:
    """재고 동기화 결과"""
    product_id: int
    wholesaler_stock: int
    platform_stock: int
    updated: bool
    error: Optional[str] = None


class RealInventorySync:
    """실제 재고 동기화 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wholesaler_manager = WholesalerManager()
        self.platform_manager = PlatformManager()
        self.sync_interval = 300  # 5분마다 동기화
        
    async def sync_all_inventory(self, db: AsyncSession) -> Dict:
        """전체 재고 동기화"""
        self.logger.info("전체 재고 동기화 시작")
        
        try:
            # 활성 상품 조회
            active_products = await self._get_active_products(db)
            
            if not active_products:
                self.logger.info("동기화할 활성 상품이 없습니다")
                return {
                    "synced": 0,
                    "failed": 0,
                    "errors": []
                }
                
            # 동기화 실행
            results = []
            for product in active_products:
                result = await self._sync_product_inventory(db, product)
                results.append(result)
                
            # 결과 집계
            synced_count = sum(1 for r in results if r.updated)
            failed_count = sum(1 for r in results if r.error)
            
            return {
                "synced": synced_count,
                "failed": failed_count,
                "errors": [
                    {"product_id": r.product_id, "error": r.error}
                    for r in results if r.error
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"전체 재고 동기화 실패: {e}")
            raise
            
    async def _get_active_products(self, db: AsyncSession) -> List[Product]:
        """활성 상품 조회"""
        query = select(Product).where(
            Product.is_active == True,
            Product.deleted_at.is_(None)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
        
    async def _sync_product_inventory(
        self, 
        db: AsyncSession, 
        product: Product
    ) -> InventorySyncResult:
        """개별 상품 재고 동기화"""
        result = InventorySyncResult(
            product_id=product.id,
            wholesaler_stock=0,
            platform_stock=product.stock,
            updated=False
        )
        
        try:
            # 1. 도매처 재고 조회
            wholesaler_stock = await self._get_wholesaler_stock(product)
            result.wholesaler_stock = wholesaler_stock
            
            # 2. 재고 변경 확인
            if wholesaler_stock != product.stock:
                # 재고 이력 저장
                await self._save_inventory_history(
                    db,
                    product_id=product.id,
                    old_stock=product.stock,
                    new_stock=wholesaler_stock,
                    source="wholesaler_sync"
                )
                
                # 상품 재고 업데이트
                product.stock = wholesaler_stock
                product.updated_at = datetime.now()
                
                # 3. 마켓플레이스 재고 업데이트
                await self._update_platform_inventory(product, wholesaler_stock)
                
                result.updated = True
                
            await db.commit()
            
        except Exception as e:
            self.logger.error(f"상품 재고 동기화 실패 - {product.id}: {e}")
            result.error = str(e)
            await db.rollback()
            
        return result
        
    async def _get_wholesaler_stock(self, product: Product) -> int:
        """도매처 재고 조회"""
        try:
            # CollectedProduct에서 도매처 정보 가져오기
            if hasattr(product, 'collected_product') and product.collected_product:
                wholesaler_name = product.collected_product.wholesaler_name
                wholesaler_product_id = product.collected_product.wholesaler_product_id
                
                # 도매처 API 호출
                wholesaler = self.wholesaler_manager.get_wholesaler(wholesaler_name)
                if wholesaler:
                    product_info = await wholesaler.get_product_info(wholesaler_product_id)
                    return product_info.get('stock', 0)
                    
            return product.stock  # 도매처 정보가 없으면 현재 재고 반환
            
        except Exception as e:
            self.logger.warning(f"도매처 재고 조회 실패 - {product.id}: {e}")
            return product.stock
            
    async def _update_platform_inventory(self, product: Product, new_stock: int):
        """마켓플레이스 재고 업데이트"""
        # 플랫폼별 재고 업데이트
        for platform_listing in product.platform_listings:
            if platform_listing.is_active:
                try:
                    platform = self.platform_manager.get_platform(
                        platform_listing.platform_type
                    )
                    
                    await platform.update_inventory(
                        platform_listing.platform_product_id,
                        new_stock
                    )
                    
                    self.logger.info(
                        f"플랫폼 재고 업데이트 - {platform_listing.platform_type}: "
                        f"{platform_listing.platform_product_id} -> {new_stock}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"플랫폼 재고 업데이트 실패 - {platform_listing.platform_type}: {e}"
                    )
                    
    async def _save_inventory_history(
        self,
        db: AsyncSession,
        product_id: int,
        old_stock: int,
        new_stock: int,
        source: str
    ):
        """재고 변경 이력 저장"""
        history = InventoryHistory(
            product_id=product_id,
            old_stock=old_stock,
            new_stock=new_stock,
            change_quantity=new_stock - old_stock,
            change_source=source,
            created_at=datetime.now()
        )
        
        db.add(history)
        
    async def sync_critical_inventory(self, db: AsyncSession) -> Dict:
        """임계 재고 상품 우선 동기화"""
        self.logger.info("임계 재고 상품 동기화 시작")
        
        # 재고가 10개 이하인 상품 조회
        query = select(Product).where(
            Product.is_active == True,
            Product.stock <= 10,
            Product.deleted_at.is_(None)
        )
        
        result = await db.execute(query)
        critical_products = result.scalars().all()
        
        if not critical_products:
            return {
                "message": "임계 재고 상품이 없습니다",
                "synced": 0
            }
            
        # 동기화 실행
        results = []
        for product in critical_products:
            sync_result = await self._sync_product_inventory(db, product)
            results.append(sync_result)
            
        synced = sum(1 for r in results if r.updated)
        
        return {
            "message": f"{len(critical_products)}개 임계 재고 상품 동기화 완료",
            "synced": synced,
            "products": [
                {
                    "product_id": r.product_id,
                    "new_stock": r.wholesaler_stock,
                    "updated": r.updated
                }
                for r in results
            ]
        }
        
    async def start_auto_sync(self, db: AsyncSession):
        """자동 재고 동기화 시작"""
        self.logger.info("자동 재고 동기화 서비스 시작")
        
        while True:
            try:
                # 전체 재고 동기화
                await self.sync_all_inventory(db)
                
                # 대기
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                self.logger.error(f"자동 재고 동기화 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
                
    async def check_stock_discrepancy(self, db: AsyncSession) -> List[Dict]:
        """재고 불일치 확인"""
        discrepancies = []
        
        products = await self._get_active_products(db)
        
        for product in products:
            try:
                # 도매처 재고 조회
                wholesaler_stock = await self._get_wholesaler_stock(product)
                
                # 불일치 확인
                if abs(wholesaler_stock - product.stock) > 0:
                    discrepancies.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "system_stock": product.stock,
                        "wholesaler_stock": wholesaler_stock,
                        "difference": wholesaler_stock - product.stock
                    })
                    
            except Exception as e:
                self.logger.error(f"재고 불일치 확인 실패 - {product.id}: {e}")
                
        return discrepancies
        
    async def force_sync_product(self, db: AsyncSession, product_id: int) -> Dict:
        """특정 상품 강제 동기화"""
        product = await db.get(Product, product_id)
        if not product:
            raise AppException("상품을 찾을 수 없습니다", status_code=404)
            
        result = await self._sync_product_inventory(db, product)
        
        return {
            "product_id": result.product_id,
            "old_stock": result.platform_stock,
            "new_stock": result.wholesaler_stock,
            "updated": result.updated,
            "error": result.error
        }


# 싱글톤 인스턴스
real_inventory_sync = RealInventorySync()