"""
실시간 이벤트 처리기
주문, 재고, 가격 변경 등의 이벤트를 실시간으로 처리
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from enum import Enum

from sqlalchemy.orm import Session

from app.services.realtime.websocket_manager import connection_manager
from app.services.dashboard.dashboard_service import DashboardService
from app.services.cache_service import CacheService
from app.services.dashboard.notification_service import NotificationService
from app.core.logging import logger
from app.core.database import get_db


class EventType(Enum):
    """이벤트 타입"""
    ORDER_CREATED = "order_created"
    ORDER_STATUS_CHANGED = "order_status_changed"
    ORDER_CANCELLED = "order_cancelled"
    INVENTORY_UPDATED = "inventory_updated"
    INVENTORY_LOW = "inventory_low"
    INVENTORY_OUT_OF_STOCK = "inventory_out_of_stock"
    PRICE_UPDATED = "price_updated"
    PRODUCT_TRENDING = "product_trending"
    SALES_MILESTONE = "sales_milestone"
    AI_INSIGHT_READY = "ai_insight_ready"
    COMPETITOR_ALERT = "competitor_alert"
    MARKET_TREND = "market_trend"


class EventProcessor:
    """실시간 이벤트 처리기"""
    
    def __init__(self):
        self.dashboard_service = DashboardService()
        self.cache = CacheService()
        self.notification_service = NotificationService()
        self.event_handlers = {
            EventType.ORDER_CREATED: self._handle_order_created,
            EventType.ORDER_STATUS_CHANGED: self._handle_order_status_changed,
            EventType.ORDER_CANCELLED: self._handle_order_cancelled,
            EventType.INVENTORY_UPDATED: self._handle_inventory_updated,
            EventType.INVENTORY_LOW: self._handle_inventory_low,
            EventType.INVENTORY_OUT_OF_STOCK: self._handle_inventory_out_of_stock,
            EventType.PRICE_UPDATED: self._handle_price_updated,
            EventType.PRODUCT_TRENDING: self._handle_product_trending,
            EventType.SALES_MILESTONE: self._handle_sales_milestone,
            EventType.AI_INSIGHT_READY: self._handle_ai_insight_ready,
            EventType.COMPETITOR_ALERT: self._handle_competitor_alert,
            EventType.MARKET_TREND: self._handle_market_trend
        }
        
    async def process_event(
        self,
        event_type: EventType,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> None:
        """이벤트 처리"""
        try:
            logger.info(f"이벤트 처리 시작: type={event_type.value}, user_id={user_id}")
            
            # 이벤트 핸들러 실행
            handler = self.event_handlers.get(event_type)
            if handler:
                await handler(user_id, data, db)
            else:
                logger.warning(f"알 수 없는 이벤트 타입: {event_type}")
                
            # 이벤트 로그 저장
            await self._log_event(event_type, user_id, data)
            
        except Exception as e:
            logger.error(f"이벤트 처리 실패: {str(e)}")
            
    async def _handle_order_created(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """주문 생성 이벤트 처리"""
        try:
            order_data = data.get("order", {})
            
            # 실시간 대시보드 업데이트
            update_data = {
                "type": "new_order",
                "order": {
                    "id": order_data.get("id"),
                    "platform": order_data.get("platform"),
                    "total_amount": order_data.get("total_amount"),
                    "items_count": order_data.get("items_count"),
                    "customer": order_data.get("customer"),
                    "created_at": order_data.get("created_at")
                }
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "order", update_data
            )
            
            # 알림 생성
            notification = {
                "type": "info",
                "title": "새 주문 접수",
                "message": f"{order_data.get('platform')}에서 {order_data.get('total_amount'):,}원의 새 주문이 접수되었습니다.",
                "data": order_data,
                "priority": "medium"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            
            # 실시간 알림 전송
            await connection_manager.send_notification(user_id, notification)
            
            # 매출 통계 업데이트
            await self._update_sales_statistics(user_id, order_data)
            
            # 재고 확인 트리거
            for item in order_data.get("items", []):
                await self._check_inventory_after_order(
                    user_id, item.get("product_id"), item.get("quantity")
                )
                
        except Exception as e:
            logger.error(f"주문 생성 이벤트 처리 실패: {str(e)}")
            
    async def _handle_order_status_changed(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """주문 상태 변경 이벤트 처리"""
        try:
            order_id = data.get("order_id")
            old_status = data.get("old_status")
            new_status = data.get("new_status")
            
            # 실시간 대시보드 업데이트
            update_data = {
                "type": "order_status_update",
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
                "updated_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "order_status", update_data
            )
            
            # 특정 상태 변경에 대한 알림
            if new_status == "shipped":
                notification = {
                    "type": "success",
                    "title": "배송 시작",
                    "message": f"주문 #{order_id}의 배송이 시작되었습니다.",
                    "priority": "low"
                }
                await connection_manager.send_notification(user_id, notification)
                
            elif new_status == "delivered":
                notification = {
                    "type": "success",
                    "title": "배송 완료",
                    "message": f"주문 #{order_id}이 성공적으로 배송 완료되었습니다.",
                    "priority": "low"
                }
                await connection_manager.send_notification(user_id, notification)
                
        except Exception as e:
            logger.error(f"주문 상태 변경 이벤트 처리 실패: {str(e)}")
            
    async def _handle_order_cancelled(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """주문 취소 이벤트 처리"""
        try:
            order_data = data.get("order", {})
            reason = data.get("reason", "사유 없음")
            
            # 실시간 대시보드 업데이트
            update_data = {
                "type": "order_cancelled",
                "order": order_data,
                "reason": reason,
                "cancelled_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "order_cancel", update_data
            )
            
            # 알림 생성
            notification = {
                "type": "warning",
                "title": "주문 취소",
                "message": f"주문 #{order_data.get('id')}이 취소되었습니다. (사유: {reason})",
                "data": order_data,
                "priority": "high"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 재고 복구
            for item in order_data.get("items", []):
                await self._restore_inventory_after_cancel(
                    user_id, item.get("product_id"), item.get("quantity")
                )
                
        except Exception as e:
            logger.error(f"주문 취소 이벤트 처리 실패: {str(e)}")
            
    async def _handle_inventory_updated(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """재고 업데이트 이벤트 처리"""
        try:
            inventory_data = data.get("inventory", {})
            
            # 실시간 대시보드 업데이트
            update_data = {
                "type": "inventory_update",
                "product_id": inventory_data.get("product_id"),
                "product_name": inventory_data.get("product_name"),
                "old_quantity": inventory_data.get("old_quantity"),
                "new_quantity": inventory_data.get("new_quantity"),
                "platform": inventory_data.get("platform"),
                "updated_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "inventory", update_data
            )
            
            # 재고 수준 확인
            new_quantity = inventory_data.get("new_quantity", 0)
            min_quantity = inventory_data.get("min_quantity", 10)
            
            if new_quantity == 0:
                await self.process_event(
                    EventType.INVENTORY_OUT_OF_STOCK, user_id, data, db
                )
            elif new_quantity <= min_quantity:
                await self.process_event(
                    EventType.INVENTORY_LOW, user_id, data, db
                )
                
        except Exception as e:
            logger.error(f"재고 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def _handle_inventory_low(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """재고 부족 이벤트 처리"""
        try:
            inventory_data = data.get("inventory", {})
            
            # 알림 생성
            notification = {
                "type": "warning",
                "title": "재고 부족 경고",
                "message": f"{inventory_data.get('product_name')}의 재고가 {inventory_data.get('new_quantity')}개로 부족합니다.",
                "data": inventory_data,
                "priority": "high",
                "action": {
                    "type": "restock",
                    "product_id": inventory_data.get("product_id"),
                    "recommended_quantity": inventory_data.get("recommended_order", 100)
                }
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 자동 재주문 제안
            await self._suggest_auto_reorder(user_id, inventory_data)
            
        except Exception as e:
            logger.error(f"재고 부족 이벤트 처리 실패: {str(e)}")
            
    async def _handle_inventory_out_of_stock(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """품절 이벤트 처리"""
        try:
            inventory_data = data.get("inventory", {})
            
            # 긴급 알림 생성
            notification = {
                "type": "error",
                "title": "품절 알림",
                "message": f"{inventory_data.get('product_name')}이(가) 품절되었습니다!",
                "data": inventory_data,
                "priority": "critical",
                "action": {
                    "type": "urgent_restock",
                    "product_id": inventory_data.get("product_id")
                }
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 판매 중지 처리
            await self._pause_product_sales(user_id, inventory_data.get("product_id"))
            
        except Exception as e:
            logger.error(f"품절 이벤트 처리 실패: {str(e)}")
            
    async def _handle_price_updated(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """가격 변경 이벤트 처리"""
        try:
            price_data = data.get("price", {})
            
            # 실시간 대시보드 업데이트
            update_data = {
                "type": "price_update",
                "product_id": price_data.get("product_id"),
                "product_name": price_data.get("product_name"),
                "old_price": price_data.get("old_price"),
                "new_price": price_data.get("new_price"),
                "platform": price_data.get("platform"),
                "change_percentage": self._calculate_price_change_percentage(
                    price_data.get("old_price"), price_data.get("new_price")
                ),
                "updated_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "price", update_data
            )
            
            # 중요한 가격 변경 알림
            change_percentage = update_data["change_percentage"]
            if abs(change_percentage) > 10:  # 10% 이상 변경
                notification = {
                    "type": "info",
                    "title": "가격 변경 알림",
                    "message": f"{price_data.get('product_name')}의 가격이 {change_percentage:+.1f}% 변경되었습니다.",
                    "data": price_data,
                    "priority": "medium"
                }
                await connection_manager.send_notification(user_id, notification)
                
        except Exception as e:
            logger.error(f"가격 변경 이벤트 처리 실패: {str(e)}")
            
    async def _handle_product_trending(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """상품 트렌딩 이벤트 처리"""
        try:
            trending_data = data.get("trending", {})
            
            # 알림 생성
            notification = {
                "type": "success",
                "title": "인기 급상승 상품",
                "message": f"{trending_data.get('product_name')}의 판매가 {trending_data.get('growth_rate')}% 증가했습니다!",
                "data": trending_data,
                "priority": "medium"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 재고 확인 및 추가 주문 제안
            await self._check_trending_product_stock(user_id, trending_data)
            
        except Exception as e:
            logger.error(f"상품 트렌딩 이벤트 처리 실패: {str(e)}")
            
    async def _handle_sales_milestone(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """매출 마일스톤 이벤트 처리"""
        try:
            milestone_data = data.get("milestone", {})
            
            # 축하 알림
            notification = {
                "type": "celebration",
                "title": "매출 목표 달성!",
                "message": f"오늘 매출이 {milestone_data.get('amount'):,}원을 돌파했습니다!",
                "data": milestone_data,
                "priority": "low"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 대시보드 특별 효과
            update_data = {
                "type": "milestone_achieved",
                "milestone": milestone_data,
                "achieved_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "milestone", update_data
            )
            
        except Exception as e:
            logger.error(f"매출 마일스톤 이벤트 처리 실패: {str(e)}")
            
    async def _handle_ai_insight_ready(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """AI 인사이트 준비 완료 이벤트 처리"""
        try:
            insight_data = data.get("insight", {})
            
            # 알림 생성
            notification = {
                "type": "ai",
                "title": "AI 인사이트 도착",
                "message": insight_data.get("summary", "새로운 비즈니스 인사이트가 준비되었습니다."),
                "data": insight_data,
                "priority": "medium",
                "action": {
                    "type": "view_insight",
                    "insight_id": insight_data.get("id")
                }
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
            # 대시보드 AI 섹션 업데이트
            update_data = {
                "type": "ai_insight",
                "insight": insight_data,
                "generated_at": datetime.now().isoformat()
            }
            
            await connection_manager.broadcast_dashboard_update(
                user_id, "ai_insight", update_data
            )
            
        except Exception as e:
            logger.error(f"AI 인사이트 이벤트 처리 실패: {str(e)}")
            
    async def _handle_competitor_alert(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """경쟁사 알림 이벤트 처리"""
        try:
            competitor_data = data.get("competitor", {})
            
            # 알림 생성
            notification = {
                "type": "warning",
                "title": "경쟁사 동향",
                "message": competitor_data.get("message", "경쟁사의 중요한 변화가 감지되었습니다."),
                "data": competitor_data,
                "priority": "high"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"경쟁사 알림 이벤트 처리 실패: {str(e)}")
            
    async def _handle_market_trend(
        self,
        user_id: int,
        data: Dict[str, Any],
        db: Optional[Session]
    ) -> None:
        """시장 트렌드 이벤트 처리"""
        try:
            trend_data = data.get("trend", {})
            
            # 알림 생성
            notification = {
                "type": "opportunity",
                "title": "시장 트렌드 알림",
                "message": f"'{trend_data.get('keyword')}'가 급상승 트렌드입니다.",
                "data": trend_data,
                "priority": "medium"
            }
            
            await self.notification_service.create_notification(
                user_id, notification, db
            )
            await connection_manager.send_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"시장 트렌드 이벤트 처리 실패: {str(e)}")
            
    async def _update_sales_statistics(
        self,
        user_id: int,
        order_data: Dict[str, Any]
    ) -> None:
        """매출 통계 업데이트"""
        try:
            # 일일 매출 캐시 업데이트
            today = datetime.now().date()
            cache_key = f"sales:daily:{user_id}:{today}"
            
            current_sales = await self.cache.get(cache_key) or 0
            new_sales = current_sales + order_data.get("total_amount", 0)
            
            await self.cache.set(cache_key, new_sales, ttl=86400)  # 24시간
            
            # 매출 마일스톤 확인
            milestones = [1000000, 5000000, 10000000]  # 100만, 500만, 1000만
            for milestone in milestones:
                if current_sales < milestone <= new_sales:
                    await self.process_event(
                        EventType.SALES_MILESTONE,
                        user_id,
                        {"milestone": {"amount": milestone, "type": "daily"}},
                        None
                    )
                    
        except Exception as e:
            logger.error(f"매출 통계 업데이트 실패: {str(e)}")
            
    async def _check_inventory_after_order(
        self,
        user_id: int,
        product_id: int,
        quantity_ordered: int
    ) -> None:
        """주문 후 재고 확인"""
        try:
            # 재고 정보 조회 (실제 구현에서는 DB 조회)
            # 여기서는 이벤트 발생만 처리
            pass
            
        except Exception as e:
            logger.error(f"주문 후 재고 확인 실패: {str(e)}")
            
    async def _restore_inventory_after_cancel(
        self,
        user_id: int,
        product_id: int,
        quantity: int
    ) -> None:
        """취소 후 재고 복구"""
        try:
            # 재고 복구 로직
            # 실제 구현에서는 DB 업데이트
            pass
            
        except Exception as e:
            logger.error(f"재고 복구 실패: {str(e)}")
            
    async def _suggest_auto_reorder(
        self,
        user_id: int,
        inventory_data: Dict[str, Any]
    ) -> None:
        """자동 재주문 제안"""
        try:
            # AI 기반 재주문 수량 계산
            # 실제 구현에서는 판매 패턴 분석
            pass
            
        except Exception as e:
            logger.error(f"자동 재주문 제안 실패: {str(e)}")
            
    async def _pause_product_sales(
        self,
        user_id: int,
        product_id: int
    ) -> None:
        """상품 판매 중지"""
        try:
            # 각 플랫폼에 판매 중지 요청
            # 실제 구현에서는 플랫폼 API 호출
            pass
            
        except Exception as e:
            logger.error(f"상품 판매 중지 실패: {str(e)}")
            
    async def _check_trending_product_stock(
        self,
        user_id: int,
        trending_data: Dict[str, Any]
    ) -> None:
        """트렌딩 상품 재고 확인"""
        try:
            # 급상승 상품의 재고가 충분한지 확인
            # 부족하면 추가 주문 제안
            pass
            
        except Exception as e:
            logger.error(f"트렌딩 상품 재고 확인 실패: {str(e)}")
            
    def _calculate_price_change_percentage(
        self,
        old_price: float,
        new_price: float
    ) -> float:
        """가격 변경률 계산"""
        if old_price == 0:
            return 0
        return ((new_price - old_price) / old_price) * 100
        
    async def _log_event(
        self,
        event_type: EventType,
        user_id: int,
        data: Dict[str, Any]
    ) -> None:
        """이벤트 로그 저장"""
        try:
            # 이벤트 로그를 캐시에 저장 (최근 100개)
            cache_key = f"events:log:{user_id}"
            events = await self.cache.get(cache_key) or []
            
            event_log = {
                "type": event_type.value,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            events.insert(0, event_log)
            events = events[:100]  # 최근 100개만 유지
            
            await self.cache.set(cache_key, events, ttl=86400)  # 24시간
            
        except Exception as e:
            logger.error(f"이벤트 로그 저장 실패: {str(e)}")


# 전역 이벤트 프로세서 인스턴스
event_processor = EventProcessor()