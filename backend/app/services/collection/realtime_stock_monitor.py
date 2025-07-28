"""
실시간 재고 모니터링 서비스
중요 상품의 재고를 주기적으로 확인하고 업데이트
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...models.collected_product import CollectedProduct, WholesalerSource, CollectionStatus
from ...models.collected_product_history import CollectedProductHistory, ChangeType, PriceAlert
from ...services.database.database import get_db
from ...services.wholesalers.wholesaler_manager import WholesalerManager
from ...core.cache import cache_manager


class RealtimeStockMonitor:
    """실시간 재고 모니터링 서비스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.wholesaler_manager = WholesalerManager()
        self.is_running = False
        self._monitoring_task = None
        self._monitored_products: Set[str] = set()  # 모니터링 중인 상품 ID 집합
        
    async def start_monitoring(
        self,
        check_interval: int = 300,  # 5분 간격
        priority_check_interval: int = 60  # 우선순위 상품은 1분 간격
    ):
        """재고 모니터링 시작"""
        if self.is_running:
            self.logger.warning("재고 모니터링이 이미 실행 중입니다")
            return
            
        self.is_running = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(check_interval, priority_check_interval)
        )
        self.logger.info("실시간 재고 모니터링 시작")
        
    async def stop_monitoring(self):
        """재고 모니터링 중지"""
        self.is_running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("실시간 재고 모니터링 중지")
        
    async def _monitoring_loop(self, check_interval: int, priority_check_interval: int):
        """모니터링 루프"""
        last_check = datetime.utcnow()
        last_priority_check = datetime.utcnow()
        
        while self.is_running:
            try:
                now = datetime.utcnow()
                
                # 우선순위 상품 체크
                if (now - last_priority_check).total_seconds() >= priority_check_interval:
                    await self._check_priority_products()
                    last_priority_check = now
                
                # 일반 상품 체크
                if (now - last_check).total_seconds() >= check_interval:
                    await self._check_regular_products()
                    last_check = now
                
                await asyncio.sleep(10)  # 10초 대기
                
            except Exception as e:
                self.logger.error(f"재고 모니터링 중 오류: {str(e)}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
                
    async def _check_priority_products(self):
        """우선순위 상품 재고 확인 (인기 상품, 재고 부족 상품)"""
        try:
            db = next(get_db())
            
            # 우선순위 상품 조회 기준:
            # 1. 재고가 10개 이하인 상품
            # 2. 가격 알림이 설정된 상품
            # 3. 최근 24시간 내 가격/재고가 변경된 상품
            priority_products = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.status == CollectionStatus.COLLECTED,
                    or_(
                        CollectedProduct.stock_quantity <= 10,
                        CollectedProduct.id.in_(
                            db.query(PriceAlert.collected_product_id).filter(
                                PriceAlert.is_active == True
                            )
                        ),
                        CollectedProduct.id.in_(
                            db.query(CollectedProductHistory.collected_product_id).filter(
                                CollectedProductHistory.change_timestamp >= datetime.utcnow() - timedelta(hours=24)
                            ).distinct()
                        )
                    )
                )
            ).limit(50).all()
            
            self.logger.info(f"우선순위 상품 {len(priority_products)}개 재고 확인 시작")
            
            # 도매처별로 그룹화
            products_by_source = {}
            for product in priority_products:
                if product.source not in products_by_source:
                    products_by_source[product.source] = []
                products_by_source[product.source].append(product)
            
            # 각 도매처별로 재고 확인
            for source, products in products_by_source.items():
                await self._check_products_stock(source, products, db, is_priority=True)
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"우선순위 상품 재고 확인 실패: {str(e)}")
            
    async def _check_regular_products(self):
        """일반 상품 재고 확인"""
        try:
            db = next(get_db())
            
            # 일반 상품 조회 기준:
            # 1. 활성 상태
            # 2. 최근 6시간 이상 업데이트 안됨
            # 3. 우선순위가 아닌 상품
            regular_products = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.status == CollectionStatus.COLLECTED,
                    CollectedProduct.updated_at < datetime.utcnow() - timedelta(hours=6),
                    ~CollectedProduct.id.in_(self._monitored_products)  # 이미 모니터링 중인 상품 제외
                )
            ).limit(100).all()
            
            self.logger.info(f"일반 상품 {len(regular_products)}개 재고 확인 시작")
            
            # 도매처별로 그룹화
            products_by_source = {}
            for product in regular_products:
                if product.source not in products_by_source:
                    products_by_source[product.source] = []
                products_by_source[product.source].append(product)
            
            # 각 도매처별로 재고 확인
            for source, products in products_by_source.items():
                await self._check_products_stock(source, products, db, is_priority=False)
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"일반 상품 재고 확인 실패: {str(e)}")
            
    async def _check_products_stock(
        self,
        source: WholesalerSource,
        products: List[CollectedProduct],
        db: Session,
        is_priority: bool = False
    ):
        """특정 도매처의 상품들 재고 확인"""
        try:
            # 도매처 클라이언트 생성
            wholesaler_client = await self.wholesaler_manager.get_client(source)
            if not wholesaler_client:
                return
            
            # 모니터링 중 표시
            product_ids = [p.id for p in products]
            self._monitored_products.update(product_ids)
            
            async with wholesaler_client:
                # 각 상품의 재고 확인
                for product in products:
                    try:
                        # 재고 정보 조회
                        stock_info = await wholesaler_client.get_product_stock(
                            product.supplier_id
                        )
                        
                        if stock_info:
                            # 변경사항 확인 및 업데이트
                            await self._update_stock_if_changed(
                                product, stock_info, db, is_priority
                            )
                        
                        # API 호출 제한을 위한 대기
                        await asyncio.sleep(0.5 if is_priority else 1.0)
                        
                    except Exception as e:
                        self.logger.error(
                            f"상품 재고 확인 실패 ({product.supplier_id}): {str(e)}"
                        )
                        
            # 모니터링 완료 표시 제거
            self._monitored_products.difference_update(product_ids)
            
        except Exception as e:
            self.logger.error(f"{source.value} 재고 확인 실패: {str(e)}")
            
    async def _update_stock_if_changed(
        self,
        product: CollectedProduct,
        stock_info: Dict,
        db: Session,
        is_priority: bool
    ):
        """재고 정보가 변경된 경우 업데이트"""
        new_quantity = stock_info.get('quantity', 0)
        new_status = "available" if stock_info.get('is_available', False) else "out_of_stock"
        
        # 변경사항 확인
        stock_changed = (
            product.stock_quantity != new_quantity or
            product.stock_status != new_status
        )
        
        if stock_changed:
            # 변경 이력 생성
            stock_history = CollectedProductHistory(
                collected_product_id=product.id,
                source=product.source,
                supplier_id=product.supplier_id,
                change_type=ChangeType.STOCK_CHANGE,
                old_stock_quantity=product.stock_quantity,
                new_stock_quantity=new_quantity,
                old_stock_status=product.stock_status,
                new_stock_status=new_status,
                changes_summary={
                    'realtime_check': True,
                    'is_priority': is_priority,
                    'check_time': datetime.utcnow().isoformat()
                }
            )
            db.add(stock_history)
            
            # 상품 정보 업데이트
            product.stock_quantity = new_quantity
            product.stock_status = new_status
            product.updated_at = datetime.utcnow()
            
            # 캐시 무효화
            await self._invalidate_product_cache(product)
            
            # 재입고 알림 처리
            if product.stock_status == "out_of_stock" and new_status == "available":
                await self._process_back_in_stock_alerts(product, db)
            
            db.commit()
            
            self.logger.info(
                f"재고 업데이트: {product.name[:30]} "
                f"({product.stock_quantity} -> {new_quantity})"
            )
            
    async def _invalidate_product_cache(self, product: CollectedProduct):
        """상품 관련 캐시 무효화"""
        try:
            # 상품 상세 캐시 무효화
            cache_pattern = f"*collected_product:{product.id}*"
            await cache_manager.clear_pattern(cache_pattern)
            
            # 카테고리별 목록 캐시 무효화
            if product.category:
                category_pattern = f"*category:{product.category}*"
                await cache_manager.clear_pattern(category_pattern)
                
        except Exception as e:
            self.logger.error(f"캐시 무효화 실패: {str(e)}")
            
    async def _process_back_in_stock_alerts(self, product: CollectedProduct, db: Session):
        """재입고 알림 처리"""
        try:
            # 해당 상품의 재입고 알림 조회
            alerts = db.query(PriceAlert).filter(
                and_(
                    PriceAlert.collected_product_id == product.id,
                    PriceAlert.alert_type == "back_in_stock",
                    PriceAlert.is_active == True
                )
            ).all()
            
            for alert in alerts:
                # 알림 발송 로직 (실제 구현 필요)
                self.logger.info(
                    f"재입고 알림 발송: 사용자 {alert.user_id}, "
                    f"상품 {product.name[:30]}"
                )
                
                # 알림 이력 업데이트
                alert.last_alerted_at = datetime.utcnow()
                alert.alert_count += 1
                
        except Exception as e:
            self.logger.error(f"재입고 알림 처리 실패: {str(e)}")
            
    async def add_priority_monitoring(self, product_ids: List[str]):
        """특정 상품을 우선순위 모니터링에 추가"""
        self._monitored_products.update(product_ids)
        self.logger.info(f"{len(product_ids)}개 상품을 우선순위 모니터링에 추가")
        
    async def get_monitoring_stats(self) -> Dict:
        """모니터링 통계 조회"""
        try:
            db = next(get_db())
            
            # 최근 1시간 동안의 변경 이력
            recent_changes = db.query(CollectedProductHistory).filter(
                and_(
                    CollectedProductHistory.change_type == ChangeType.STOCK_CHANGE,
                    CollectedProductHistory.change_timestamp >= datetime.utcnow() - timedelta(hours=1)
                )
            ).count()
            
            # 재고 부족 상품 수
            out_of_stock = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.status == CollectionStatus.COLLECTED,
                    CollectedProduct.stock_status == "out_of_stock"
                )
            ).count()
            
            db.close()
            
            return {
                'is_running': self.is_running,
                'monitored_products_count': len(self._monitored_products),
                'recent_stock_changes': recent_changes,
                'out_of_stock_products': out_of_stock,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"모니터링 통계 조회 실패: {str(e)}")
            return {'error': str(e)}


# 싱글톤 인스턴스
realtime_stock_monitor = RealtimeStockMonitor()