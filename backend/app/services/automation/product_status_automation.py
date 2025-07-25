"""
드롭쉬핑 상품 상태 자동 관리 서비스

품절/재입고에 따른 상품 상태 자동 변경
모든 플랫폼에서의 일관된 상태 유지
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


class AutomationAction(Enum):
    """자동화 액션 유형"""
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    UPDATE_PRICE = "update_price"
    UPDATE_STOCK = "update_stock"
    DELETE = "delete"
    REPLACE = "replace"


@dataclass
class AutomationRule:
    """자동화 규칙"""
    rule_id: str
    name: str
    condition: str
    action: AutomationAction
    parameters: Dict
    is_active: bool
    priority: int


@dataclass
class AutomationResult:
    """자동화 실행 결과"""
    product_id: int
    rule_applied: str
    action_taken: AutomationAction
    success: bool
    error_message: Optional[str] = None
    execution_time: datetime = None


class ProductStatusAutomation:
    """상품 상태 자동화 관리자"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.automation_rules = []
        self.is_running = False
        
        # 기본 자동화 규칙 초기화
        self._initialize_default_rules()
        
    def _initialize_default_rules(self):
        """기본 자동화 규칙 초기화"""
        default_rules = [
            AutomationRule(
                rule_id="out_of_stock_deactivate",
                name="품절 시 자동 비활성화",
                condition="stock == 0",
                action=AutomationAction.DEACTIVATE,
                parameters={"platforms": "all", "notify": True},
                is_active=True,
                priority=1
            ),
            AutomationRule(
                rule_id="restock_activate",
                name="재입고 시 자동 활성화",
                condition="stock > 0 AND previous_stock == 0",
                action=AutomationAction.ACTIVATE,
                parameters={"check_price": True, "notify": True},
                is_active=True,
                priority=1
            ),
            AutomationRule(
                rule_id="low_stock_warning",
                name="부족 재고 경고",
                condition="stock <= 10 AND stock > 0",
                action=AutomationAction.UPDATE_STOCK,
                parameters={"warning_level": "low", "notify": True},
                is_active=True,
                priority=2
            ),
            AutomationRule(
                rule_id="long_term_outofstock_delete",
                name="장기 품절 자동 삭제",
                condition="days_out_of_stock >= 30",
                action=AutomationAction.DELETE,
                parameters={"backup": True, "suggest_alternatives": True},
                is_active=True,
                priority=3
            ),
            AutomationRule(
                rule_id="price_change_update",
                name="가격 변동 시 업데이트",
                condition="wholesale_price_changed == True",
                action=AutomationAction.UPDATE_PRICE,
                parameters={"margin_maintain": True, "notify": True},
                is_active=True,
                priority=2
            )
        ]
        
        self.automation_rules = default_rules
        
    async def start_automation(self):
        """자동화 시작"""
        if self.is_running:
            self.logger.warning("자동화가 이미 실행 중입니다")
            return
            
        self.is_running = True
        self.logger.info("상품 상태 자동화 시작")
        
        # 백그라운드 태스크로 실행
        asyncio.create_task(self._automation_loop())
        
    async def stop_automation(self):
        """자동화 중지"""
        self.is_running = False
        self.logger.info("상품 상태 자동화 중지")
        
    async def _automation_loop(self):
        """자동화 메인 루프"""
        while self.is_running:
            try:
                await self._process_automation_rules()
                await asyncio.sleep(300)  # 5분 간격
            except Exception as e:
                self.logger.error(f"자동화 처리 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
                
    async def _process_automation_rules(self):
        """자동화 규칙 처리"""
        db = next(get_db())
        try:
            # 활성 상품 조회
            products = db.query(Product).filter(
                Product.is_deleted == False,
                Product.is_dropshipping == True
            ).all()
            
            results = []
            
            for product in products:
                for rule in self.automation_rules:
                    if not rule.is_active:
                        continue
                        
                    # 규칙 조건 확인
                    if await self._check_rule_condition(product, rule):
                        result = await self._execute_rule_action(product, rule)
                        results.append(result)
                        
                        # 우선순위 1 규칙이 적용되면 다른 규칙 건너뛰기
                        if rule.priority == 1 and result.success:
                            break
                            
            # 실행 결과 로깅
            if results:
                success_count = sum(1 for r in results if r.success)
                self.logger.info(f"자동화 규칙 {len(results)}개 실행, {success_count}개 성공")
                
        finally:
            db.close()
            
    async def _check_rule_condition(self, product: Product, rule: AutomationRule) -> bool:
        """규칙 조건 확인"""
        try:
            # 현재 재고 조회
            current_stock = await self._get_current_stock(product.id)
            previous_stock = await self._get_previous_stock(product.id)
            
            # 품절 지속 일수 계산
            days_out_of_stock = 0
            if product.status == ProductStatus.OUT_OF_STOCK and product.deactivated_at:
                days_out_of_stock = (datetime.now() - product.deactivated_at).days
                
            # 가격 변동 확인
            wholesale_price_changed = await self._check_price_change(product.id)
            
            # 조건 변수 설정
            condition_vars = {
                'stock': current_stock,
                'previous_stock': previous_stock,
                'days_out_of_stock': days_out_of_stock,
                'wholesale_price_changed': wholesale_price_changed,
                'product_status': product.status.value
            }
            
            # 조건 평가
            return self._evaluate_condition(rule.condition, condition_vars)
            
        except Exception as e:
            self.logger.error(f"규칙 조건 확인 실패 - 상품 {product.id}, 규칙 {rule.rule_id}: {e}")
            return False
            
    def _evaluate_condition(self, condition: str, variables: Dict) -> bool:
        """조건식 평가"""
        try:
            # 안전한 조건 평가를 위한 제한된 네임스페이스
            safe_dict = {
                '__builtins__': {},
                **variables
            }
            
            return eval(condition, safe_dict)
            
        except Exception as e:
            self.logger.error(f"조건 평가 실패 - {condition}: {e}")
            return False
            
    async def _execute_rule_action(self, product: Product, rule: AutomationRule) -> AutomationResult:
        """규칙 액션 실행"""
        start_time = datetime.now()
        
        try:
            success = False
            error_message = None
            
            if rule.action == AutomationAction.ACTIVATE:
                success = await self._activate_product(product, rule.parameters)
            elif rule.action == AutomationAction.DEACTIVATE:
                success = await self._deactivate_product(product, rule.parameters)
            elif rule.action == AutomationAction.UPDATE_PRICE:
                success = await self._update_product_price(product, rule.parameters)
            elif rule.action == AutomationAction.UPDATE_STOCK:
                success = await self._update_stock_status(product, rule.parameters)
            elif rule.action == AutomationAction.DELETE:
                success = await self._delete_product(product, rule.parameters)
            elif rule.action == AutomationAction.REPLACE:
                success = await self._replace_product(product, rule.parameters)
                
            return AutomationResult(
                product_id=product.id,
                rule_applied=rule.rule_id,
                action_taken=rule.action,
                success=success,
                error_message=error_message,
                execution_time=start_time
            )
            
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"규칙 액션 실행 실패 - 상품 {product.id}, 액션 {rule.action}: {e}")
            
            return AutomationResult(
                product_id=product.id,
                rule_applied=rule.rule_id,
                action_taken=rule.action,
                success=False,
                error_message=error_message,
                execution_time=start_time
            )
            
    async def _activate_product(self, product: Product, parameters: Dict) -> bool:
        """상품 활성화"""
        self.logger.info(f"상품 활성화 - {product.id}: {product.name}")
        
        # 가격 확인 옵션
        if parameters.get("check_price", False):
            price_changed = await self._check_price_change(product.id)
            if price_changed:
                self.logger.warning(f"가격 변동 감지로 수동 확인 필요 - 상품 {product.id}")
                if parameters.get("notify", False):
                    await self._send_price_change_notification(product.id)
                return False
                
        # 모든 플랫폼에서 활성화
        from app.services.platforms.platform_manager import PlatformManager
        platform_manager = PlatformManager()
        
        success = True
        for platform_product in product.platform_products:
            try:
                platform = platform_manager.get_platform(platform_product.platform_type)
                await platform.activate_product(platform_product.platform_product_id)
                
                platform_product.is_active = True
                platform_product.reactivated_at = datetime.now()
                
            except Exception as e:
                self.logger.error(f"플랫폼 활성화 실패 - {platform_product.platform_type}: {e}")
                success = False
                
        # 메인 상품 상태 업데이트
        if success:
            product.status = ProductStatus.ACTIVE
            product.reactivated_at = datetime.now()
            
            db = next(get_db())
            try:
                db.commit()
            finally:
                db.close()
                
        # 알림 전송
        if parameters.get("notify", False):
            await self._send_activation_notification(product.id)
            
        return success
        
    async def _deactivate_product(self, product: Product, parameters: Dict) -> bool:
        """상품 비활성화"""
        self.logger.info(f"상품 비활성화 - {product.id}: {product.name}")
        
        # 모든 플랫폼에서 비활성화
        from app.services.platforms.platform_manager import PlatformManager
        platform_manager = PlatformManager()
        
        success = True
        for platform_product in product.platform_products:
            try:
                platform = platform_manager.get_platform(platform_product.platform_type)
                await platform.deactivate_product(platform_product.platform_product_id)
                
                platform_product.is_active = False
                platform_product.deactivated_at = datetime.now()
                platform_product.deactivation_reason = "자동화 규칙에 의한 비활성화"
                
            except Exception as e:
                self.logger.error(f"플랫폼 비활성화 실패 - {platform_product.platform_type}: {e}")
                success = False
                
        # 메인 상품 상태 업데이트
        if success:
            product.status = ProductStatus.OUT_OF_STOCK
            product.deactivated_at = datetime.now()
            
            db = next(get_db())
            try:
                db.commit()
            finally:
                db.close()
                
        # 알림 전송
        if parameters.get("notify", False):
            await self._send_deactivation_notification(product.id)
            
        return success
        
    async def _update_product_price(self, product: Product, parameters: Dict) -> bool:
        """상품 가격 업데이트"""
        self.logger.info(f"상품 가격 업데이트 - {product.id}: {product.name}")
        
        try:
            # 도매처에서 최신 가격 조회
            from app.services.wholesalers.wholesaler_manager import WholesalerManager
            wholesaler_manager = WholesalerManager()
            wholesaler = wholesaler_manager.get_wholesaler(product.wholesaler_id)
            
            product_info = await wholesaler.get_product_info(product.wholesaler_product_id)
            new_wholesale_price = product_info.get('price', product.wholesale_price)
            
            # 마진 유지 옵션
            if parameters.get("margin_maintain", False):
                current_margin_rate = (product.selling_price - product.wholesale_price) / product.wholesale_price
                new_selling_price = new_wholesale_price * (1 + current_margin_rate)
            else:
                new_selling_price = product.selling_price
                
            # 가격 업데이트
            product.wholesale_price = new_wholesale_price
            product.selling_price = new_selling_price
            product.price_updated_at = datetime.now()
            
            # 플랫폼별 가격 업데이트
            from app.services.platforms.platform_manager import PlatformManager
            platform_manager = PlatformManager()
            
            for platform_product in product.platform_products:
                if platform_product.is_active:
                    try:
                        platform = platform_manager.get_platform(platform_product.platform_type)
                        await platform.update_product_price(
                            platform_product.platform_product_id,
                            new_selling_price
                        )
                    except Exception as e:
                        self.logger.error(f"플랫폼 가격 업데이트 실패 - {platform_product.platform_type}: {e}")
                        
            db = next(get_db())
            try:
                db.commit()
            finally:
                db.close()
                
            # 알림 전송
            if parameters.get("notify", False):
                await self._send_price_update_notification(product.id, new_wholesale_price, new_selling_price)
                
            return True
            
        except Exception as e:
            self.logger.error(f"가격 업데이트 실패 - 상품 {product.id}: {e}")
            return False
            
    async def _update_stock_status(self, product: Product, parameters: Dict) -> bool:
        """재고 상태 업데이트"""
        warning_level = parameters.get("warning_level", "low")
        
        if parameters.get("notify", False):
            await self._send_stock_warning_notification(product.id, warning_level)
            
        return True
        
    async def _delete_product(self, product: Product, parameters: Dict) -> bool:
        """상품 삭제"""
        self.logger.info(f"장기 품절 상품 삭제 - {product.id}: {product.name}")
        
        # 백업 옵션
        if parameters.get("backup", False):
            await self._backup_product_data(product.id)
            
        # 대체 상품 제안
        if parameters.get("suggest_alternatives", False):
            await self._suggest_product_alternatives(product.id)
            
        # 소프트 삭제
        product.is_deleted = True
        product.deleted_at = datetime.now()
        product.deletion_reason = "장기 품절로 인한 자동 삭제"
        
        db = next(get_db())
        try:
            db.commit()
        finally:
            db.close()
            
        return True
        
    async def _replace_product(self, product: Product, parameters: Dict) -> bool:
        """상품 교체"""
        # 구현 예정: 대체 상품으로 자동 교체
        return True
        
    async def _get_current_stock(self, product_id: int) -> int:
        """현재 재고 조회"""
        db = next(get_db())
        try:
            from app.models.inventory import Inventory
            inventory = db.query(Inventory).filter(Inventory.product_id == product_id).first()
            return inventory.quantity if inventory else 0
        finally:
            db.close()
            
    async def _get_previous_stock(self, product_id: int) -> int:
        """이전 재고 조회"""
        # 구현 예정: 재고 히스토리에서 이전 값 조회
        return 0
        
    async def _check_price_change(self, product_id: int) -> bool:
        """가격 변동 확인"""
        # 구현 예정: 가격 히스토리 확인
        return False
        
    # 알림 메서드들
    async def _send_activation_notification(self, product_id: int):
        """활성화 알림"""
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_product_notification(
            product_id, "상품이 자동으로 활성화되었습니다"
        )
        
    async def _send_deactivation_notification(self, product_id: int):
        """비활성화 알림"""
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_product_notification(
            product_id, "상품이 자동으로 비활성화되었습니다"
        )
        
    async def _send_price_change_notification(self, product_id: int):
        """가격 변동 알림"""
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_product_notification(
            product_id, "도매 가격이 변동되어 수동 확인이 필요합니다"
        )
        
    async def _send_price_update_notification(self, product_id: int, new_wholesale: float, new_selling: float):
        """가격 업데이트 알림"""
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_product_notification(
            product_id, f"가격이 업데이트되었습니다 (도매: {new_wholesale:,}원, 판매: {new_selling:,}원)"
        )
        
    async def _send_stock_warning_notification(self, product_id: int, warning_level: str):
        """재고 경고 알림"""
        from app.services.dashboard.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_product_notification(
            product_id, f"재고 부족 경고 ({warning_level})"
        )
        
    async def _backup_product_data(self, product_id: int):
        """상품 데이터 백업"""
        # 구현 예정: 삭제 전 상품 데이터 백업
        pass
        
    async def _suggest_product_alternatives(self, product_id: int):
        """대체 상품 제안"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                from app.services.dropshipping.alternative_finder import AlternativeFinder
                alternative_finder = AlternativeFinder()
                alternatives = await alternative_finder.find_alternatives(
                    category=product.category,
                    price_range=(product.selling_price * 0.8, product.selling_price * 1.2),
                    exclude_product_id=product_id,
                    original_product_name=product.name
                )
                
                if alternatives:
                    from app.services.dashboard.notification_service import NotificationService
                    notification_service = NotificationService()
                    await notification_service.send_alternatives_notification(product_id, alternatives)
        finally:
            db.close()
            
    # 설정 관리 메서드들
    def add_custom_rule(self, rule: AutomationRule):
        """사용자 정의 규칙 추가"""
        self.automation_rules.append(rule)
        self.logger.info(f"자동화 규칙 추가: {rule.name}")
        
    def remove_rule(self, rule_id: str):
        """규칙 제거"""
        self.automation_rules = [rule for rule in self.automation_rules if rule.rule_id != rule_id]
        self.logger.info(f"자동화 규칙 제거: {rule_id}")
        
    def update_rule_status(self, rule_id: str, is_active: bool):
        """규칙 활성화/비활성화"""
        for rule in self.automation_rules:
            if rule.rule_id == rule_id:
                rule.is_active = is_active
                self.logger.info(f"자동화 규칙 상태 변경: {rule_id} -> {is_active}")
                break
                
    def get_automation_status(self) -> Dict:
        """자동화 상태 조회"""
        return {
            "is_running": self.is_running,
            "total_rules": len(self.automation_rules),
            "active_rules": sum(1 for rule in self.automation_rules if rule.is_active),
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "is_active": rule.is_active,
                    "priority": rule.priority
                }
                for rule in self.automation_rules
            ]
        }