"""
드롭쉬핑 재입고 감지 서비스

품절 상품의 재입고를 감지하고 자동 재활성화 처리
가격 변동, 상품 정보 변경 확인 후 안전한 재활성화
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.services.database.database import get_db
from app.models.product import Product, ProductStatus


class RestockDecision(Enum):
    """재입고 결정"""
    AUTO_REACTIVATE = "auto_reactivate"      # 자동 재활성화
    MANUAL_REVIEW = "manual_review"          # 수동 검토 필요
    PRICE_CHANGED = "price_changed"          # 가격 변동으로 인한 검토
    INFO_CHANGED = "info_changed"            # 상품 정보 변경으로 인한 검토
    SUPPLIER_UNRELIABLE = "supplier_unreliable"  # 공급업체 신뢰도 문제


@dataclass
class RestockEvent:
    """재입고 이벤트"""
    product_id: int
    previous_stock: int
    current_stock: int
    detected_at: datetime
    wholesale_price_before: float
    wholesale_price_after: float
    price_change_rate: float
    decision: RestockDecision
    auto_reactivated: bool = False
    review_required: bool = False
    reason: Optional[str] = None


class RestockDetector:
    """재입고 감지기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.price_change_threshold = 0.05  # 5% 이상 가격 변동 시 검토
        self.auto_reactivation_enabled = True
        self.detection_interval = 300  # 5분 간격
        self.is_running = False
        
    async def start_detection(self):
        """재입고 감지 시작"""
        if self.is_running:
            self.logger.warning("재입고 감지가 이미 실행 중입니다")
            return
            
        self.is_running = True
        self.logger.info("재입고 감지 시작")
        
        # 백그라운드 태스크로 실행
        asyncio.create_task(self._detection_loop())
        
    async def stop_detection(self):
        """재입고 감지 중지"""
        self.is_running = False
        self.logger.info("재입고 감지 중지")
        
    async def _detection_loop(self):
        """재입고 감지 루프"""
        while self.is_running:
            try:
                await self._detect_restocks()
                await asyncio.sleep(self.detection_interval)
            except Exception as e:
                self.logger.error(f"재입고 감지 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
                
    async def _detect_restocks(self):
        """재입고 감지 처리"""
        db = next(get_db())
        try:
            # 품절 상품 조회
            out_of_stock_products = db.query(Product).filter(
                Product.status == ProductStatus.OUT_OF_STOCK,
                Product.is_deleted == False,
                Product.is_dropshipping == True
            ).all()
            
            restock_events = []
            
            for product in out_of_stock_products:
                event = await self._check_product_restock(product)
                if event:
                    restock_events.append(event)
                    
            # 재입고 이벤트 처리
            for event in restock_events:
                await self._process_restock_event(event)
                
            if restock_events:
                self.logger.info(f"재입고 이벤트 {len(restock_events)}개 처리 완료")
                
        finally:
            db.close()
            
    async def _check_product_restock(self, product: Product) -> Optional[RestockEvent]:
        """개별 상품 재입고 확인"""
        try:
            # 현재 재고 조회
            current_stock = await self._get_current_wholesaler_stock(
                product.wholesaler_id, product.wholesaler_product_id
            )
            
            # 재입고 확인 (0에서 양수로 변경)
            if current_stock <= 0:
                return None
                
            # 이전 재고는 0이었다고 가정 (품절 상태이므로)
            previous_stock = 0
            
            # 현재 도매 가격 조회
            current_wholesale_price = await self._get_current_wholesale_price(
                product.wholesaler_id, product.wholesaler_product_id
            )
            
            # 가격 변동률 계산
            price_change_rate = 0.0
            if product.wholesale_price > 0:
                price_change_rate = abs(current_wholesale_price - product.wholesale_price) / product.wholesale_price
                
            # 재입고 결정 로직
            decision = await self._make_restock_decision(product, current_wholesale_price, price_change_rate)
            
            event = RestockEvent(
                product_id=product.id,
                previous_stock=previous_stock,
                current_stock=current_stock,
                detected_at=datetime.now(),
                wholesale_price_before=product.wholesale_price,
                wholesale_price_after=current_wholesale_price,
                price_change_rate=price_change_rate,
                decision=decision
            )
            
            self.logger.info(f"재입고 감지 - 상품 {product.id}: {product.name}, "
                           f"재고 {current_stock}개, 가격변동 {price_change_rate:.2%}")
            
            return event
            
        except Exception as e:
            self.logger.error(f"상품 {product.id} 재입고 확인 실패: {e}")
            return None
            
    async def _get_current_wholesaler_stock(self, wholesaler_id: int, product_id: str) -> int:
        """도매처 현재 재고 조회"""
        from app.services.wholesalers.wholesaler_manager import WholesalerManager
        
        wholesaler_manager = WholesalerManager()
        wholesaler = wholesaler_manager.get_wholesaler(wholesaler_id)
        
        if not wholesaler:
            raise ValueError(f"도매처를 찾을 수 없습니다: {wholesaler_id}")
            
        stock_info = await wholesaler.get_product_stock(product_id)
        return stock_info.get('quantity', 0)
        
    async def _get_current_wholesale_price(self, wholesaler_id: int, product_id: str) -> float:
        """현재 도매 가격 조회"""
        from app.services.wholesalers.wholesaler_manager import WholesalerManager
        
        wholesaler_manager = WholesalerManager()
        wholesaler = wholesaler_manager.get_wholesaler(wholesaler_id)
        
        if not wholesaler:
            raise ValueError(f"도매처를 찾을 수 없습니다: {wholesaler_id}")
            
        product_info = await wholesaler.get_product_info(product_id)
        return product_info.get('price', 0.0)
        
    async def _make_restock_decision(self, 
                                   product: Product, 
                                   current_price: float, 
                                   price_change_rate: float) -> RestockDecision:
        """재입고 결정 로직"""
        
        # 1. 공급업체 신뢰도 확인
        supplier_reliable = await self._check_supplier_reliability(product.wholesaler_id)
        if not supplier_reliable:
            return RestockDecision.SUPPLIER_UNRELIABLE
            
        # 2. 가격 변동 확인
        if price_change_rate > self.price_change_threshold:
            return RestockDecision.PRICE_CHANGED
            
        # 3. 상품 정보 변경 확인
        info_changed = await self._check_product_info_changes(product)
        if info_changed:
            return RestockDecision.INFO_CHANGED
            
        # 4. 자동 재활성화 조건 충족
        if self.auto_reactivation_enabled:
            return RestockDecision.AUTO_REACTIVATE
        else:
            return RestockDecision.MANUAL_REVIEW
            
    async def _check_supplier_reliability(self, wholesaler_id: int) -> bool:
        """공급업체 신뢰도 확인"""
        try:
            db = next(get_db())
            try:
                from app.models.dropshipping import SupplierReliability
                
                reliability = db.query(SupplierReliability).filter(
                    SupplierReliability.supplier_id == wholesaler_id
                ).first()
                
                if not reliability:
                    return True  # 신뢰도 데이터가 없으면 통과
                    
                # 신뢰도 점수 60점 이상 필요
                return reliability.reliability_score >= 60.0
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"공급업체 신뢰도 확인 실패 - {wholesaler_id}: {e}")
            return True  # 오류 시 통과
            
    async def _check_product_info_changes(self, product: Product) -> bool:
        """상품 정보 변경 확인"""
        try:
            from app.services.wholesalers.wholesaler_manager import WholesalerManager
            
            wholesaler_manager = WholesalerManager()
            wholesaler = wholesaler_manager.get_wholesaler(product.wholesaler_id)
            
            current_info = await wholesaler.get_product_info(product.wholesaler_product_id)
            
            # 상품명 변경 확인
            current_name = current_info.get('name', '')
            if current_name and current_name != product.name:
                return True
                
            # 옵션 변경 확인 (구현 예정)
            # 이미지 변경 확인 (구현 예정)
            
            return False
            
        except Exception as e:
            self.logger.error(f"상품 정보 변경 확인 실패 - 상품 {product.id}: {e}")
            return False
            
    async def _process_restock_event(self, event: RestockEvent):
        """재입고 이벤트 처리"""
        # 재입고 이벤트 저장
        await self._save_restock_event(event)
        
        # 결정에 따른 처리
        if event.decision == RestockDecision.AUTO_REACTIVATE:
            await self._auto_reactivate_product(event)
        elif event.decision in [RestockDecision.PRICE_CHANGED, RestockDecision.INFO_CHANGED, RestockDecision.MANUAL_REVIEW]:
            await self._request_manual_review(event)
        elif event.decision == RestockDecision.SUPPLIER_UNRELIABLE:
            await self._handle_unreliable_supplier(event)
            
        # 알림 발송
        await self._send_restock_notification(event)
        
    async def _save_restock_event(self, event: RestockEvent):
        """재입고 이벤트 저장"""
        db = next(get_db())
        try:
            from app.models.dropshipping import RestockHistory
            
            history = RestockHistory(
                product_id=event.product_id,
                previous_stock=event.previous_stock,
                current_stock=event.current_stock,
                detected_at=event.detected_at,
                wholesale_price_before=event.wholesale_price_before,
                wholesale_price_after=event.wholesale_price_after,
                price_change_rate=event.price_change_rate,
                decision=event.decision.value,
                auto_reactivated=event.auto_reactivated,
                review_required=event.review_required,
                reason=event.reason
            )
            
            db.add(history)
            db.commit()
            
        finally:
            db.close()
            
    async def _auto_reactivate_product(self, event: RestockEvent):
        """상품 자동 재활성화"""
        try:
            from app.services.automation.product_status_automation import ProductStatusAutomation
            
            automation = ProductStatusAutomation()
            
            db = next(get_db())
            try:
                product = db.query(Product).filter(Product.id == event.product_id).first()
                if product:
                    # 가격 업데이트
                    product.wholesale_price = event.wholesale_price_after
                    
                    # 자동 활성화
                    parameters = {"check_price": False, "notify": True}
                    success = await automation._activate_product(product, parameters)
                    
                    event.auto_reactivated = success
                    event.reason = "자동 재활성화 완료" if success else "자동 재활성화 실패"
                    
                    # 재고 업데이트
                    from app.models.inventory import Inventory
                    inventory = db.query(Inventory).filter(Inventory.product_id == event.product_id).first()
                    if inventory:
                        inventory.quantity = event.current_stock
                        inventory.last_updated = datetime.now()
                    else:
                        inventory = Inventory(
                            product_id=event.product_id,
                            quantity=event.current_stock,
                            last_updated=datetime.now()
                        )
                        db.add(inventory)
                        
                    db.commit()
                    
                    self.logger.info(f"상품 자동 재활성화 - {event.product_id}: {success}")
                    
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"자동 재활성화 실패 - 상품 {event.product_id}: {e}")
            event.auto_reactivated = False
            event.reason = f"자동 재활성화 실패: {str(e)}"
            
    async def _request_manual_review(self, event: RestockEvent):
        """수동 검토 요청"""
        event.review_required = True
        
        if event.decision == RestockDecision.PRICE_CHANGED:
            event.reason = f"가격 변동 ({event.price_change_rate:.2%}) 검토 필요"
        elif event.decision == RestockDecision.INFO_CHANGED:
            event.reason = "상품 정보 변경 검토 필요"
        else:
            event.reason = "수동 검토 필요"
            
        # 검토 요청 알림 발송
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_manual_review_request(
            event.product_id, event.reason
        )
        
        self.logger.info(f"수동 검토 요청 - 상품 {event.product_id}: {event.reason}")
        
    async def _handle_unreliable_supplier(self, event: RestockEvent):
        """신뢰도 낮은 공급업체 처리"""
        event.review_required = True
        event.reason = "공급업체 신뢰도 낮음 - 검토 필요"
        
        # 대체 공급업체 제안
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == event.product_id).first()
            if product:
                from app.services.dropshipping.alternative_finder import AlternativeFinder
                alternative_finder = AlternativeFinder()
                
                alternatives = await alternative_finder.find_alternatives(
                    category=product.category,
                    price_range=(product.selling_price * 0.8, product.selling_price * 1.2),
                    exclude_product_id=product.id
                )
                
                if alternatives:
                    # 더 신뢰할 수 있는 대안만 필터링
                    reliable_alternatives = [
                        alt for alt in alternatives 
                        if alt.reliability_score >= 70
                    ]
                    
                    if reliable_alternatives:
                        from app.services.dashboard.notification_service import NotificationService
                        notification_service = NotificationService()
                        await notification_service.send_supplier_alternatives_notification(
                            event.product_id, reliable_alternatives
                        )
                        
        finally:
            db.close()
            
    async def _send_restock_notification(self, event: RestockEvent):
        """재입고 알림 발송"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        if event.auto_reactivated:
            message = f"재입고 감지 및 자동 재활성화 완료 (재고: {event.current_stock}개)"
        else:
            message = f"재입고 감지 (재고: {event.current_stock}개) - {event.reason}"
            
        await notification_service.send_restock_notification(
            event.product_id, message, event.auto_reactivated
        )
        
    # 수동 처리 메서드들
    async def handle_restock(self, product_id: int):
        """외부에서 호출되는 재입고 처리"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return
                
            event = await self._check_product_restock(product)
            if event:
                await self._process_restock_event(event)
                
        finally:
            db.close()
            
    async def approve_manual_review(self, product_id: int, approved: bool):
        """수동 검토 승인/거부"""
        db = next(get_db())
        try:
            from app.models.dropshipping import RestockHistory
            
            # 최근 재입고 이벤트 조회
            recent_event = db.query(RestockHistory).filter(
                RestockHistory.product_id == product_id,
                RestockHistory.review_required == True
            ).order_by(RestockHistory.detected_at.desc()).first()
            
            if not recent_event:
                return
                
            if approved:
                # 수동 승인 후 재활성화
                product = db.query(Product).filter(Product.id == product_id).first()
                if product:
                    from app.services.automation.product_status_automation import ProductStatusAutomation
                    automation = ProductStatusAutomation()
                    
                    parameters = {"check_price": False, "notify": True}
                    success = await automation._activate_product(product, parameters)
                    
                    recent_event.auto_reactivated = success
                    recent_event.review_required = False
                    recent_event.reason += " (수동 승인 후 활성화)"
                    
            else:
                # 승인 거부
                recent_event.review_required = False
                recent_event.reason += " (수동 검토 거부)"
                
            db.commit()
            
        finally:
            db.close()
            
    def get_restock_statistics(self) -> Dict:
        """재입고 통계 조회"""
        db = next(get_db())
        try:
            from app.models.dropshipping import RestockHistory
            
            # 최근 30일 통계
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            total_restocks = db.query(RestockHistory).filter(
                RestockHistory.detected_at >= thirty_days_ago
            ).count()
            
            auto_reactivated = db.query(RestockHistory).filter(
                RestockHistory.detected_at >= thirty_days_ago,
                RestockHistory.auto_reactivated == True
            ).count()
            
            manual_reviews = db.query(RestockHistory).filter(
                RestockHistory.detected_at >= thirty_days_ago,
                RestockHistory.review_required == True
            ).count()
            
            avg_detection_to_activation = db.query(
                db.func.avg(
                    db.func.extract('epoch', RestockHistory.detected_at) - 
                    db.func.extract('epoch', Product.deactivated_at)
                )
            ).join(Product).filter(
                RestockHistory.detected_at >= thirty_days_ago,
                RestockHistory.auto_reactivated == True
            ).scalar() or 0
            
            return {
                "detection_running": self.is_running,
                "total_restocks_30d": total_restocks,
                "auto_reactivated_30d": auto_reactivated,
                "manual_reviews_30d": manual_reviews,
                "auto_reactivation_rate": (auto_reactivated / total_restocks * 100) if total_restocks > 0 else 0,
                "avg_detection_to_activation_hours": avg_detection_to_activation / 3600
            }
            
        finally:
            db.close()