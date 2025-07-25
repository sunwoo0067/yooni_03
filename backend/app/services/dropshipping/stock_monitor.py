"""
드롭쉬핑 실시간 재고 모니터링 서비스

도매처별 재고 상태를 실시간으로 추적하고
품절 감지 시 즉시 알림 및 자동 대응
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.services.database.database import get_db
from app.services.wholesalers.wholesaler_manager import WholesalerManager
from app.models.product import ProductStatus
from app.models.inventory import Inventory


class StockStatus(Enum):
    """재고 상태"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"  # 10개 이하
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


@dataclass
class StockCheckResult:
    """재고 체크 결과"""
    product_id: int
    wholesaler_id: int
    current_stock: int
    previous_stock: int
    status: StockStatus
    status_changed: bool
    check_time: datetime
    response_time_ms: float
    error_message: Optional[str] = None


class DropshippingStockMonitor:
    """드롭쉬핑 재고 모니터링 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wholesaler_manager = WholesalerManager()
        self.monitoring_active = False
        self.check_interval = 600  # 10분 간격
        self.low_stock_threshold = 10
        self.monitoring_tasks = {}
        
    async def start_monitoring(self):
        """실시간 모니터링 시작"""
        if self.monitoring_active:
            self.logger.warning("모니터링이 이미 활성화되어 있습니다")
            return
            
        self.monitoring_active = True
        self.logger.info("드롭쉬핑 재고 모니터링 시작")
        
        # 모든 활성 상품에 대해 모니터링 태스크 생성
        await self._start_product_monitoring()
        
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        
        # 모든 모니터링 태스크 중지
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        self.monitoring_tasks.clear()
        self.logger.info("드롭쉬핑 재고 모니터링 중지")
        
    async def _start_product_monitoring(self):
        """상품별 모니터링 태스크 시작"""
        db = next(get_db())
        try:
            # 활성 상품 목록 조회
            active_products = self._get_active_products(db)
            
            for product in active_products:
                task = asyncio.create_task(
                    self._monitor_product_stock(product.id)
                )
                self.monitoring_tasks[product.id] = task
                
        finally:
            db.close()
            
    async def _monitor_product_stock(self, product_id: int):
        """개별 상품 재고 모니터링"""
        while self.monitoring_active:
            try:
                # 재고 상태 체크
                result = await self.check_product_stock(product_id)
                
                if result and result.status_changed:
                    await self._handle_stock_change(result)
                    
                # 다음 체크까지 대기
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"상품 {product_id} 모니터링 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도
                
    async def check_product_stock(self, product_id: int) -> Optional[StockCheckResult]:
        """개별 상품 재고 체크"""
        db = next(get_db())
        try:
            # 상품 정보 조회
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product or not product.is_active:
                return None
                
            # 이전 재고 상태 조회
            previous_inventory = db.query(Inventory).filter(
                Inventory.product_id == product_id
            ).first()
            
            previous_stock = previous_inventory.quantity if previous_inventory else 0
            
            start_time = datetime.now()
            
            try:
                # 도매처에서 현재 재고 조회
                current_stock = await self._fetch_stock_from_wholesaler(
                    product.wholesaler_id, product.wholesaler_product_id
                )
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # 재고 상태 결정
                status = self._determine_stock_status(current_stock)
                status_changed = self._has_status_changed(previous_stock, current_stock)
                
                # 재고 정보 업데이트
                await self._update_inventory(db, product_id, current_stock)
                
                return StockCheckResult(
                    product_id=product_id,
                    wholesaler_id=product.wholesaler_id,
                    current_stock=current_stock,
                    previous_stock=previous_stock,
                    status=status,
                    status_changed=status_changed,
                    check_time=datetime.now(),
                    response_time_ms=response_time
                )
                
            except Exception as e:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.error(f"도매처 재고 조회 실패 - 상품 {product_id}: {e}")
                
                return StockCheckResult(
                    product_id=product_id,
                    wholesaler_id=product.wholesaler_id,
                    current_stock=0,
                    previous_stock=previous_stock,
                    status=StockStatus.UNKNOWN,
                    status_changed=False,
                    check_time=datetime.now(),
                    response_time_ms=response_time,
                    error_message=str(e)
                )
                
        finally:
            db.close()
            
    async def _fetch_stock_from_wholesaler(self, wholesaler_id: int, product_id: str) -> int:
        """도매처에서 재고 정보 조회"""
        wholesaler = self.wholesaler_manager.get_wholesaler(wholesaler_id)
        if not wholesaler:
            raise ValueError(f"도매처를 찾을 수 없습니다: {wholesaler_id}")
            
        # 도매처별 재고 조회 API 호출
        stock_info = await wholesaler.get_product_stock(product_id)
        return stock_info.get('quantity', 0)
        
    def _determine_stock_status(self, stock_quantity: int) -> StockStatus:
        """재고 상태 결정"""
        if stock_quantity <= 0:
            return StockStatus.OUT_OF_STOCK
        elif stock_quantity <= self.low_stock_threshold:
            return StockStatus.LOW_STOCK
        else:
            return StockStatus.IN_STOCK
            
    def _has_status_changed(self, previous_stock: int, current_stock: int) -> bool:
        """재고 상태 변경 여부 확인"""
        previous_status = self._determine_stock_status(previous_stock)
        current_status = self._determine_stock_status(current_stock)
        return previous_status != current_status
        
    async def _update_inventory(self, db: Session, product_id: int, quantity: int):
        """재고 정보 업데이트"""
        inventory = db.query(Inventory).filter(
            Inventory.product_id == product_id
        ).first()
        
        if inventory:
            inventory.quantity = quantity
            inventory.last_updated = datetime.now()
        else:
            inventory = Inventory(
                product_id=product_id,
                quantity=quantity,
                last_updated=datetime.now()
            )
            db.add(inventory)
            
        db.commit()
        
    async def _handle_stock_change(self, result: StockCheckResult):
        """재고 상태 변경 처리"""
        if result.status == StockStatus.OUT_OF_STOCK:
            await self._handle_out_of_stock(result)
        elif result.status == StockStatus.LOW_STOCK:
            await self._handle_low_stock(result)
        elif result.status == StockStatus.IN_STOCK and result.previous_stock <= 0:
            await self._handle_restock(result)
            
    async def _handle_out_of_stock(self, result: StockCheckResult):
        """품절 처리"""
        self.logger.warning(f"품절 감지 - 상품 {result.product_id}")
        
        # 품절 알림 발송
        await self._send_stock_alert(result, "품절 감지")
        
        # 자동 비활성화 처리는 outofstock_manager에서 수행
        from app.services.dropshipping.outofstock_manager import OutOfStockManager
        outofstock_manager = OutOfStockManager()
        await outofstock_manager.handle_out_of_stock(result.product_id)
        
    async def _handle_low_stock(self, result: StockCheckResult):
        """부족 재고 처리"""
        self.logger.warning(f"부족 재고 감지 - 상품 {result.product_id}, 재고: {result.current_stock}")
        
        # 부족 재고 알림 발송
        await self._send_stock_alert(result, "부족 재고 경고")
        
    async def _handle_restock(self, result: StockCheckResult):
        """재입고 처리"""
        self.logger.info(f"재입고 감지 - 상품 {result.product_id}")
        
        # 재입고 알림 발송
        await self._send_stock_alert(result, "재입고 감지")
        
        # 자동 재활성화 처리는 automation 서비스에서 수행
        from app.services.automation.restock_detector import RestockDetector
        restock_detector = RestockDetector()
        await restock_detector.handle_restock(result.product_id)
        
    async def _send_stock_alert(self, result: StockCheckResult, alert_type: str):
        """재고 알림 발송"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        await notification_service.send_stock_notification(
            product_id=result.product_id,
            alert_type=alert_type,
            current_stock=result.current_stock,
            previous_stock=result.previous_stock
        )
        
    def _get_active_products(self, db: Session) -> List:
        """활성 상품 목록 조회"""
        from app.models.product import Product
        
        return db.query(Product).filter(
            Product.status == ProductStatus.ACTIVE,
            Product.is_dropshipping == True
        ).all()
        
    async def get_monitoring_status(self) -> Dict:
        """모니터링 상태 조회"""
        return {
            "active": self.monitoring_active,
            "check_interval": self.check_interval,
            "low_stock_threshold": self.low_stock_threshold,
            "monitored_products": len(self.monitoring_tasks),
            "running_tasks": sum(1 for task in self.monitoring_tasks.values() if not task.done())
        }
        
    async def bulk_stock_check(self, product_ids: List[int]) -> List[StockCheckResult]:
        """대량 재고 체크"""
        tasks = []
        for product_id in product_ids:
            task = asyncio.create_task(self.check_product_stock(product_id))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"상품 {product_ids[i]} 재고 체크 실패: {result}")
            elif result:
                valid_results.append(result)
                
        return valid_results
        
    async def update_monitoring_settings(self, 
                                       check_interval: Optional[int] = None,
                                       low_stock_threshold: Optional[int] = None):
        """모니터링 설정 업데이트"""
        if check_interval:
            self.check_interval = check_interval
            
        if low_stock_threshold:
            self.low_stock_threshold = low_stock_threshold
            
        self.logger.info(f"모니터링 설정 업데이트 - 체크 간격: {self.check_interval}초, "
                        f"부족 재고 임계값: {self.low_stock_threshold}개")