"""
드롭쉬핑 품절 관리 서비스

품절 상품의 자동 비활성화, 재입고 감지, 대체 상품 관리
드롭쉬핑의 핵심: "품절 = 매출 손실" 최소화
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.services.database.database import get_db
from app.models.product import Product, ProductStatus
from app.models.inventory import Inventory


class OutOfStockAction(Enum):
    """품절 시 수행할 액션"""
    DEACTIVATE = "deactivate"  # 비활성화
    HIDE = "hide"  # 숨김 처리
    DELETE = "delete"  # 삭제
    REPLACE = "replace"  # 대체 상품으로 교체


@dataclass
class OutOfStockRecord:
    """품절 기록"""
    product_id: int
    wholesaler_id: int
    out_of_stock_time: datetime
    restock_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    action_taken: Optional[OutOfStockAction] = None
    alternative_suggested: bool = False
    estimated_lost_sales: float = 0.0


class OutOfStockManager:
    """품절 관리자"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.auto_deactivate_enabled = True
        self.long_term_threshold_days = 7  # 7일 이상 품절 시 장기 품절로 분류
        self.delete_threshold_days = 30  # 30일 이상 품절 시 삭제 고려
        
    async def handle_out_of_stock(self, product_id: int) -> OutOfStockRecord:
        """품절 처리"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ValueError(f"상품을 찾을 수 없습니다: {product_id}")
                
            self.logger.info(f"품절 처리 시작 - 상품 {product_id}: {product.name}")
            
            # 품절 기록 생성
            outofstock_record = OutOfStockRecord(
                product_id=product_id,
                wholesaler_id=product.wholesaler_id,
                out_of_stock_time=datetime.now()
            )
            
            # 자동 비활성화
            if self.auto_deactivate_enabled:
                await self._deactivate_product_on_platforms(product)
                outofstock_record.action_taken = OutOfStockAction.DEACTIVATE
                
            # 품절 통계 업데이트
            await self._update_outofstock_statistics(product_id)
            
            # 대체 상품 제안
            alternatives = await self._suggest_alternatives(product)
            if alternatives:
                outofstock_record.alternative_suggested = True
                await self._notify_alternatives(product_id, alternatives)
                
            # 매출 손실 추정
            outofstock_record.estimated_lost_sales = await self._estimate_lost_sales(product)
            
            # 품절 기록 저장
            await self._save_outofstock_record(db, outofstock_record)
            
            self.logger.info(f"품절 처리 완료 - 상품 {product_id}")
            return outofstock_record
            
        finally:
            db.close()
            
    async def _deactivate_product_on_platforms(self, product: Product):
        """모든 플랫폼에서 상품 비활성화"""
        from app.services.platforms.platform_manager import PlatformManager
        
        platform_manager = PlatformManager()
        
        # 상품이 등록된 모든 플랫폼에서 비활성화
        for platform_product in product.platform_products:
            try:
                platform = platform_manager.get_platform(platform_product.platform_type)
                await platform.deactivate_product(platform_product.platform_product_id)
                
                # 로컬 상태 업데이트
                platform_product.is_active = False
                platform_product.deactivated_at = datetime.now()
                platform_product.deactivation_reason = "품절로 인한 자동 비활성화"
                
                self.logger.info(f"플랫폼 비활성화 완료 - {platform_product.platform_type}: "
                               f"{platform_product.platform_product_id}")
                
            except Exception as e:
                self.logger.error(f"플랫폼 비활성화 실패 - {platform_product.platform_type}: {e}")
                
        # 메인 상품 상태 업데이트
        product.status = ProductStatus.OUT_OF_STOCK
        product.deactivated_at = datetime.now()
        
    async def _update_outofstock_statistics(self, product_id: int):
        """품절 통계 업데이트"""
        db = next(get_db())
        try:
            # 품절 빈도 업데이트
            from app.models.analytics import ProductAnalytics
            
            analytics = db.query(ProductAnalytics).filter(
                ProductAnalytics.product_id == product_id
            ).first()
            
            if analytics:
                analytics.outofstock_count += 1
                analytics.last_outofstock_date = datetime.now()
            else:
                analytics = ProductAnalytics(
                    product_id=product_id,
                    outofstock_count=1,
                    last_outofstock_date=datetime.now()
                )
                db.add(analytics)
                
            db.commit()
            
        finally:
            db.close()
            
    async def _suggest_alternatives(self, product: Product) -> List[Dict]:
        """대체 상품 제안"""
        from app.services.dropshipping.alternative_finder import AlternativeFinder
        
        alternative_finder = AlternativeFinder()
        return await alternative_finder.find_alternatives(
            category=product.category,
            price_range=(product.selling_price * 0.8, product.selling_price * 1.2),
            exclude_product_id=product.id
        )
        
    async def _notify_alternatives(self, product_id: int, alternatives: List[Dict]):
        """대체 상품 알림"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        await notification_service.send_alternatives_notification(
            product_id=product_id,
            alternatives=alternatives
        )
        
    async def _estimate_lost_sales(self, product: Product) -> float:
        """매출 손실 추정"""
        db = next(get_db())
        try:
            # 최근 30일 평균 일일 판매량 계산
            from app.models.order import Order
            
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_orders = db.query(Order).filter(
                Order.product_id == product.id,
                Order.created_at >= thirty_days_ago,
                Order.status.in_(['completed', 'shipped'])
            ).count()
            
            daily_average_sales = recent_orders / 30
            estimated_daily_loss = daily_average_sales * product.selling_price
            
            return estimated_daily_loss
            
        finally:
            db.close()
            
    async def _save_outofstock_record(self, db: Session, record: OutOfStockRecord):
        """품절 기록 저장"""
        from app.models.dropshipping import OutOfStockHistory
        
        history = OutOfStockHistory(
            product_id=record.product_id,
            wholesaler_id=record.wholesaler_id,
            out_of_stock_time=record.out_of_stock_time,
            action_taken=record.action_taken.value if record.action_taken else None,
            alternative_suggested=record.alternative_suggested,
            estimated_lost_sales=record.estimated_lost_sales
        )
        
        db.add(history)
        db.commit()
        
    async def handle_restock(self, product_id: int):
        """재입고 처리"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return
                
            self.logger.info(f"재입고 처리 시작 - 상품 {product_id}: {product.name}")
            
            # 품절 기록 업데이트
            await self._update_restock_record(db, product_id)
            
            # 자동 재활성화 여부 확인
            if await self._should_auto_reactivate(product):
                await self._reactivate_product_on_platforms(product)
                
            self.logger.info(f"재입고 처리 완료 - 상품 {product_id}")
            
        finally:
            db.close()
            
    async def _update_restock_record(self, db: Session, product_id: int):
        """재입고 기록 업데이트"""
        from app.models.dropshipping import OutOfStockHistory
        
        # 최근 품절 기록 찾기
        recent_outofstock = db.query(OutOfStockHistory).filter(
            OutOfStockHistory.product_id == product_id,
            OutOfStockHistory.restock_time.is_(None)
        ).order_by(OutOfStockHistory.out_of_stock_time.desc()).first()
        
        if recent_outofstock:
            recent_outofstock.restock_time = datetime.now()
            
            # 품절 지속 시간 계산
            duration = datetime.now() - recent_outofstock.out_of_stock_time
            recent_outofstock.duration_hours = duration.total_seconds() / 3600
            
            db.commit()
            
    async def _should_auto_reactivate(self, product: Product) -> bool:
        """자동 재활성화 여부 확인"""
        # 가격 변동 확인
        price_changed = await self._check_price_changes(product)
        if price_changed:
            self.logger.info(f"가격 변동으로 인해 수동 확인 필요 - 상품 {product.id}")
            await self._notify_price_change(product.id)
            return False
            
        # 상품 정보 변경 확인
        info_changed = await self._check_product_info_changes(product)
        if info_changed:
            self.logger.info(f"상품 정보 변경으로 인해 수동 확인 필요 - 상품 {product.id}")
            return False
            
        return True
        
    async def _check_price_changes(self, product: Product) -> bool:
        """가격 변동 확인"""
        from app.services.wholesalers.wholesaler_manager import WholesalerManager
        
        try:
            wholesaler_manager = WholesalerManager()
            wholesaler = wholesaler_manager.get_wholesaler(product.wholesaler_id)
            
            current_info = await wholesaler.get_product_info(product.wholesaler_product_id)
            current_price = current_info.get('price', 0)
            
            # 5% 이상 가격 변동 시 true 반환
            price_change_rate = abs(current_price - product.wholesale_price) / product.wholesale_price
            return price_change_rate > 0.05
            
        except Exception as e:
            self.logger.error(f"가격 변동 확인 실패 - 상품 {product.id}: {e}")
            return True  # 오류 시 수동 확인 필요
            
    async def _check_product_info_changes(self, product: Product) -> bool:
        """상품 정보 변경 확인"""
        # 구현 예정: 상품명, 옵션, 이미지 등 변경 확인
        return False
        
    async def _notify_price_change(self, product_id: int):
        """가격 변동 알림"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        await notification_service.send_price_change_notification(product_id)
        
    async def _reactivate_product_on_platforms(self, product: Product):
        """모든 플랫폼에서 상품 재활성화"""
        from app.services.platforms.platform_manager import PlatformManager
        
        platform_manager = PlatformManager()
        
        for platform_product in product.platform_products:
            try:
                platform = platform_manager.get_platform(platform_product.platform_type)
                await platform.activate_product(platform_product.platform_product_id)
                
                # 로컬 상태 업데이트
                platform_product.is_active = True
                platform_product.reactivated_at = datetime.now()
                
                self.logger.info(f"플랫폼 재활성화 완료 - {platform_product.platform_type}: "
                               f"{platform_product.platform_product_id}")
                
            except Exception as e:
                self.logger.error(f"플랫폼 재활성화 실패 - {platform_product.platform_type}: {e}")
                
        # 메인 상품 상태 업데이트
        product.status = ProductStatus.ACTIVE
        product.reactivated_at = datetime.now()
        
    async def get_outofstock_products(self) -> List[Dict]:
        """품절 상품 목록 조회"""
        db = next(get_db())
        try:
            products = db.query(Product).filter(
                Product.status == ProductStatus.OUT_OF_STOCK
            ).all()
            
            result = []
            for product in products:
                # 품절 지속 시간 계산
                duration = None
                if product.deactivated_at:
                    duration = datetime.now() - product.deactivated_at
                    
                result.append({
                    "product_id": product.id,
                    "name": product.name,
                    "wholesaler_id": product.wholesaler_id,
                    "deactivated_at": product.deactivated_at,
                    "duration_hours": duration.total_seconds() / 3600 if duration else None,
                    "estimated_daily_loss": await self._estimate_lost_sales(product)
                })
                
            return result
            
        finally:
            db.close()
            
    async def get_long_term_outofstock(self) -> List[Dict]:
        """장기 품절 상품 조회"""
        products = await self.get_outofstock_products()
        
        threshold_hours = self.long_term_threshold_days * 24
        return [
            product for product in products
            if product.get("duration_hours", 0) > threshold_hours
        ]
        
    async def cleanup_long_term_outofstock(self) -> Dict:
        """장기 품절 상품 정리"""
        long_term_products = await self.get_long_term_outofstock()
        
        deleted_count = 0
        replacement_count = 0
        
        for product_info in long_term_products:
            product_id = product_info["product_id"]
            duration_days = product_info.get("duration_hours", 0) / 24
            
            if duration_days > self.delete_threshold_days:
                # 삭제 처리
                await self._delete_product(product_id)
                deleted_count += 1
            else:
                # 대체 상품 제안
                await self._suggest_replacement(product_id)
                replacement_count += 1
                
        return {
            "processed": len(long_term_products),
            "deleted": deleted_count,
            "replacement_suggested": replacement_count
        }
        
    async def _delete_product(self, product_id: int):
        """상품 삭제"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                # 소프트 삭제
                product.is_deleted = True
                product.deleted_at = datetime.now()
                db.commit()
                
                self.logger.info(f"장기 품절 상품 삭제 - 상품 {product_id}")
                
        finally:
            db.close()
            
    async def _suggest_replacement(self, product_id: int):
        """대체 상품 제안"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                alternatives = await self._suggest_alternatives(product)
                if alternatives:
                    await self._notify_alternatives(product_id, alternatives)
                    
        finally:
            db.close()
            
    async def get_outofstock_statistics(self) -> Dict:
        """품절 통계 조회"""
        db = next(get_db())
        try:
            from app.models.dropshipping import OutOfStockHistory
            
            # 전체 품절 횟수
            total_outofstock = db.query(OutOfStockHistory).count()
            
            # 현재 품절 상품 수
            current_outofstock = db.query(Product).filter(
                Product.status == ProductStatus.OUT_OF_STOCK
            ).count()
            
            # 평균 품절 지속 시간
            avg_duration = db.query(
                db.func.avg(OutOfStockHistory.duration_hours)
            ).filter(
                OutOfStockHistory.duration_hours.isnot(None)
            ).scalar() or 0
            
            # 총 예상 매출 손실
            total_estimated_loss = db.query(
                db.func.sum(OutOfStockHistory.estimated_lost_sales)
            ).scalar() or 0
            
            return {
                "total_outofstock_events": total_outofstock,
                "current_outofstock_products": current_outofstock,
                "average_duration_hours": round(avg_duration, 2),
                "total_estimated_loss": round(total_estimated_loss, 2)
            }
            
        finally:
            db.close()