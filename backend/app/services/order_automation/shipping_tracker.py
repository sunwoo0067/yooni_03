"""
Shipping tracking service
배송 추적 시스템
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.order import Order, OrderStatus, ShippingStatus
from app.models.order_automation import (
    WholesaleOrder, WholesaleOrderStatus,
    ShippingTracking, ShippingTrackingStatus,
    OrderProcessingLog
)
from app.services.platforms.coupang_api import CoupangAPI
from app.services.platforms.naver_api import NaverAPI
from app.services.platforms.eleventh_street_api import EleventhStreetAPI
from app.services.realtime.websocket_manager import WebSocketManager
from app.services.dashboard.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ShippingTracker:
    """배송 추적 시스템"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.platform_apis = {
            'coupang': CoupangAPI(),
            'naver': NaverAPI(),
            '11st': EleventhStreetAPI()
        }
        self.tracking_apis = {
            'cj': self._track_cj_logistics,
            'lotte': self._track_lotte_logistics,
            'hanjin': self._track_hanjin_logistics,
            'kdexp': self._track_kdexp_logistics,
            'epost': self._track_epost_logistics
        }
        self.websocket_manager = WebSocketManager()
        self.notification_service = NotificationService(db_session)
        self.tracking_active = False
        self.tracking_tasks = {}
    
    async def start_tracking(self):
        """배송 추적 시작"""
        try:
            logger.info("배송 추적 시스템 시작")
            self.tracking_active = True
            
            # 배송 추적 태스크들 시작
            self.tracking_tasks["track_wholesale_shipments"] = asyncio.create_task(
                self._track_wholesale_shipments_continuously()
            )
            
            self.tracking_tasks["update_customer_status"] = asyncio.create_task(
                self._update_customer_status_continuously()
            )
            
            self.tracking_tasks["handle_delivery_issues"] = asyncio.create_task(
                self._handle_delivery_issues_continuously()
            )
            
            self.tracking_tasks["input_tracking_to_markets"] = asyncio.create_task(
                self._input_tracking_to_markets_continuously()
            )
            
            self.tracking_tasks["notify_customers"] = asyncio.create_task(
                self._notify_customers_continuously()
            )
            
            logger.info(f"배송 추적 시스템 {len(self.tracking_tasks)}개 태스크 시작됨")
            
        except Exception as e:
            logger.error(f"배송 추적 시스템 시작 실패: {e}")
            raise
    
    async def stop_tracking(self):
        """배송 추적 중지"""
        try:
            logger.info("배송 추적 시스템 중지 시작")
            self.tracking_active = False
            
            # 모든 태스크 취소
            for task_name, task in self.tracking_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"추적 태스크 {task_name} 취소됨")
            
            self.tracking_tasks.clear()
            logger.info("배송 추적 시스템 중지 완료")
            
        except Exception as e:
            logger.error(f"배송 추적 시스템 중지 실패: {e}")
    
    async def track_wholesale_shipment(self, wholesale_order_id: str) -> Dict[str, Any]:
        """도매처 배송 추적"""
        try:
            # 도매 주문 조회
            wholesale_order = await self._get_wholesale_order(wholesale_order_id)
            if not wholesale_order:
                return {
                    'success': False,
                    'error': '도매 주문을 찾을 수 없습니다'
                }
            
            if not wholesale_order.tracking_number:
                return {
                    'success': False,
                    'error': '송장번호가 없습니다'
                }
            
            # 택배사별 추적
            carrier = wholesale_order.carrier.lower() if wholesale_order.carrier else 'unknown'
            
            if carrier in self.tracking_apis:
                tracking_result = await self.tracking_apis[carrier](
                    wholesale_order.tracking_number
                )
            else:
                # 통합 추적 API 사용
                tracking_result = await self._track_with_unified_api(
                    wholesale_order.tracking_number, carrier
                )
            
            if tracking_result['success']:
                # 추적 정보 업데이트
                await self._update_tracking_info(wholesale_order, tracking_result['data'])
                
                # 상태 변경 감지 및 처리
                status_changed = await self._check_status_change(wholesale_order, tracking_result['data'])
                
                if status_changed:
                    # 상태 변경 시 후속 처리
                    await self._handle_status_change(wholesale_order, tracking_result['data'])
                
                return {
                    'success': True,
                    'tracking_data': tracking_result['data'],
                    'status_changed': status_changed
                }
            else:
                # 추적 실패 처리
                await self._handle_tracking_failure(wholesale_order, tracking_result['error'])
                
                return {
                    'success': False,
                    'error': tracking_result['error']
                }
            
        except Exception as e:
            logger.error(f"도매처 배송 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_customer_status(self, order_id: str) -> Dict[str, Any]:
        """고객 배송 상태 업데이트"""
        try:
            # 주문 조회
            order = await self._get_order(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 도매 주문들의 배송 상태 통합
            wholesale_orders = await self._get_wholesale_orders_by_order_id(order_id)
            
            overall_status = await self._calculate_overall_shipping_status(wholesale_orders)
            
            # 주문 상태 업데이트
            if overall_status != order.shipping_status:
                await self._update_order_shipping_status(order, overall_status)
                
                # 상태 변경 로그
                await self._log_status_change(order, overall_status)
                
                # 실시간 알림
                await self._send_status_notification(order, overall_status)
            
            return {
                'success': True,
                'previous_status': order.shipping_status.value if order.shipping_status else None,
                'current_status': overall_status.value,
                'wholesale_orders_count': len(wholesale_orders)
            }
            
        except Exception as e:
            logger.error(f"고객 배송 상태 업데이트 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_delivery_issues(self, tracking_id: str) -> Dict[str, Any]:
        """배송 문제 자동 처리"""
        try:
            # 배송 추적 정보 조회
            tracking = await self._get_shipping_tracking(tracking_id)
            if not tracking:
                return {
                    'success': False,
                    'error': '배송 추적 정보를 찾을 수 없습니다'
                }
            
            # 배송 문제 유형 분석
            issue_type = await self._analyze_delivery_issue(tracking)
            
            if issue_type:
                # 문제 유형별 자동 처리
                resolution_result = await self._auto_resolve_delivery_issue(tracking, issue_type)
                
                if resolution_result['success']:
                    return {
                        'success': True,
                        'issue_type': issue_type,
                        'resolution': resolution_result['resolution'],
                        'auto_resolved': True
                    }
                else:
                    # 자동 해결 실패 시 에스컬레이션
                    await self._escalate_delivery_issue(tracking, issue_type, resolution_result['error'])
                    
                    return {
                        'success': False,
                        'issue_type': issue_type,
                        'requires_manual_intervention': True,
                        'escalated': True
                    }
            else:
                return {
                    'success': True,
                    'message': '배송 문제가 감지되지 않았습니다'
                }
            
        except Exception as e:
            logger.error(f"배송 문제 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_tracking_number(self, wholesale_order_id: str) -> Dict[str, Any]:
        """송장 번호 수집"""
        try:
            wholesale_order = await self._get_wholesale_order(wholesale_order_id)
            if not wholesale_order:
                return {
                    'success': False,
                    'error': '도매 주문을 찾을 수 없습니다'
                }
            
            # 도매업체별 송장 조회 API 호출
            wholesaler = wholesale_order.wholesaler
            platform = wholesaler.platform
            
            if platform == 'zentrade':
                tracking_info = await self._get_zentrade_tracking_number(wholesale_order)
            elif platform == 'ownerclan':
                tracking_info = await self._get_ownerclan_tracking_number(wholesale_order)
            elif platform == 'domeggook':
                tracking_info = await self._get_domeggook_tracking_number(wholesale_order)
            else:
                return {
                    'success': False,
                    'error': f'지원하지 않는 도매업체: {platform}'
                }
            
            if tracking_info['success']:
                # 송장 정보 저장
                wholesale_order.tracking_number = tracking_info['tracking_number']
                wholesale_order.carrier = tracking_info['carrier']
                wholesale_order.shipped_at = tracking_info.get('shipped_at', datetime.utcnow())
                wholesale_order.status = WholesaleOrderStatus.SHIPPED
                
                await self.db.commit()
                
                # 배송 추적 레코드 생성
                await self._create_shipping_tracking_record(wholesale_order, tracking_info)
                
                return {
                    'success': True,
                    'tracking_number': tracking_info['tracking_number'],
                    'carrier': tracking_info['carrier'],
                    'shipped_at': tracking_info.get('shipped_at')
                }
            else:
                return {
                    'success': False,
                    'error': tracking_info['error']
                }
            
        except Exception as e:
            logger.error(f"송장 번호 수집 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def input_tracking_to_market(self, order_id: str) -> Dict[str, Any]:
        """마켓에 송장 입력"""
        try:
            order = await self._get_order(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 통합 송장 정보 생성
            consolidated_tracking = await self._consolidate_tracking_info(order)
            
            if not consolidated_tracking['tracking_number']:
                return {
                    'success': False,
                    'error': '송장번호가 없습니다'
                }
            
            # 플랫폼별 송장 입력
            platform_account = order.platform_account
            platform = platform_account.platform
            
            if platform == 'coupang':
                result = await self.platform_apis['coupang'].input_tracking_number(
                    account_credentials=platform_account.credentials,
                    order_id=order.platform_order_id,
                    tracking_number=consolidated_tracking['tracking_number'],
                    carrier=consolidated_tracking['carrier']
                )
            elif platform == 'naver':
                result = await self.platform_apis['naver'].input_tracking_number(
                    account_credentials=platform_account.credentials,
                    order_id=order.platform_order_id,
                    tracking_number=consolidated_tracking['tracking_number'],
                    carrier=consolidated_tracking['carrier']
                )
            elif platform == '11st':
                result = await self.platform_apis['11st'].input_tracking_number(
                    account_credentials=platform_account.credentials,
                    order_id=order.platform_order_id,
                    tracking_number=consolidated_tracking['tracking_number'],
                    carrier=consolidated_tracking['carrier']
                )
            else:
                return {
                    'success': False,
                    'error': f'지원하지 않는 플랫폼: {platform}'
                }
            
            if result['success']:
                # 주문 상태 업데이트
                order.tracking_number = consolidated_tracking['tracking_number']
                order.shipping_carrier = consolidated_tracking['carrier']
                order.shipping_status = ShippingStatus.SHIPPED
                order.shipped_at = datetime.utcnow()
                
                await self.db.commit()
                
                # 처리 로그 기록
                await self._log_tracking_input(order, consolidated_tracking, result)
                
                return {
                    'success': True,
                    'platform': platform,
                    'tracking_number': consolidated_tracking['tracking_number'],
                    'carrier': consolidated_tracking['carrier']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
            
        except Exception as e:
            logger.error(f"마켓 송장 입력 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def notify_customers(self, order_id: str) -> Dict[str, Any]:
        """고객 배송 알림"""
        try:
            order = await self._get_order(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 배송 상태별 알림 메시지 생성
            notification_data = await self._generate_shipping_notification(order)
            
            if notification_data['should_notify']:
                # 알림 발송
                notification_result = await self.notification_service.send_shipping_notification(
                    order=order,
                    notification_type=notification_data['type'],
                    message=notification_data['message'],
                    tracking_info=notification_data['tracking_info']
                )
                
                if notification_result['success']:
                    # 알림 발송 기록 업데이트
                    await self._update_notification_record(order, notification_data['type'])
                    
                    return {
                        'success': True,
                        'notification_type': notification_data['type'],
                        'channels_sent': notification_result['channels_sent']
                    }
                else:
                    return {
                        'success': False,
                        'error': notification_result['error']
                    }
            else:
                return {
                    'success': True,
                    'message': '알림 발송 조건에 해당하지 않습니다'
                }
            
        except Exception as e:
            logger.error(f"고객 배송 알림 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 택배사별 추적 메서드들
    async def _track_cj_logistics(self, tracking_number: str) -> Dict[str, Any]:
        """CJ대한통운 배송 추적"""
        try:
            # CJ대한통운 추적 API 호출 (실제 구현에서는 API 연동 필요)
            # 여기서는 예시 구조만 제공
            api_response = await self._call_cj_tracking_api(tracking_number)
            
            if api_response['success']:
                tracking_data = self._normalize_cj_tracking_data(api_response['data'])
                return {
                    'success': True,
                    'data': tracking_data
                }
            else:
                return {
                    'success': False,
                    'error': api_response['error']
                }
            
        except Exception as e:
            logger.error(f"CJ대한통운 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _track_lotte_logistics(self, tracking_number: str) -> Dict[str, Any]:
        """롯데택배 배송 추적"""
        try:
            api_response = await self._call_lotte_tracking_api(tracking_number)
            
            if api_response['success']:
                tracking_data = self._normalize_lotte_tracking_data(api_response['data'])
                return {
                    'success': True,
                    'data': tracking_data
                }
            else:
                return {
                    'success': False,
                    'error': api_response['error']
                }
            
        except Exception as e:
            logger.error(f"롯데택배 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _track_hanjin_logistics(self, tracking_number: str) -> Dict[str, Any]:
        """한진택배 배송 추적"""
        try:
            api_response = await self._call_hanjin_tracking_api(tracking_number)
            
            if api_response['success']:
                tracking_data = self._normalize_hanjin_tracking_data(api_response['data'])
                return {
                    'success': True,
                    'data': tracking_data
                }
            else:
                return {
                    'success': False,
                    'error': api_response['error']
                }
            
        except Exception as e:
            logger.error(f"한진택배 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _track_kdexp_logistics(self, tracking_number: str) -> Dict[str, Any]:
        """경동택배 배송 추적"""
        try:
            api_response = await self._call_kdexp_tracking_api(tracking_number)
            
            if api_response['success']:
                tracking_data = self._normalize_kdexp_tracking_data(api_response['data'])
                return {
                    'success': True,
                    'data': tracking_data
                }
            else:
                return {
                    'success': False,
                    'error': api_response['error']
                }
            
        except Exception as e:
            logger.error(f"경동택배 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _track_epost_logistics(self, tracking_number: str) -> Dict[str, Any]:
        """우체국택배 배송 추적"""
        try:
            api_response = await self._call_epost_tracking_api(tracking_number)
            
            if api_response['success']:
                tracking_data = self._normalize_epost_tracking_data(api_response['data'])
                return {
                    'success': True,
                    'data': tracking_data
                }
            else:
                return {
                    'success': False,
                    'error': api_response['error']
                }
            
        except Exception as e:
            logger.error(f"우체국택배 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 백그라운드 태스크들
    async def _track_wholesale_shipments_continuously(self):
        """지속적인 도매처 배송 추적"""
        while self.tracking_active:
            try:
                # 추적이 필요한 도매 주문들 조회
                wholesale_orders = await self._get_trackable_wholesale_orders()
                
                for order in wholesale_orders:
                    try:
                        await self.track_wholesale_shipment(str(order.id))
                    except Exception as e:
                        logger.error(f"도매 주문 {order.id} 추적 실패: {e}")
                        continue
                
                # 30분마다 실행
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"도매처 배송 추적 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    async def _update_customer_status_continuously(self):
        """지속적인 고객 상태 업데이트"""
        while self.tracking_active:
            try:
                # 상태 업데이트가 필요한 주문들 조회
                orders = await self._get_orders_needing_status_update()
                
                for order in orders:
                    try:
                        await self.update_customer_status(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 상태 업데이트 실패: {e}")
                        continue
                
                # 15분마다 실행
                await asyncio.sleep(900)
                
            except Exception as e:
                logger.error(f"고객 상태 업데이트 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    async def _handle_delivery_issues_continuously(self):
        """지속적인 배송 문제 처리"""
        while self.tracking_active:
            try:
                # 배송 문제가 있는 추적 정보들 조회
                problem_trackings = await self._get_problematic_trackings()
                
                for tracking in problem_trackings:
                    try:
                        await self.handle_delivery_issues(str(tracking.id))
                    except Exception as e:
                        logger.error(f"배송 추적 {tracking.id} 문제 처리 실패: {e}")
                        continue
                
                # 1시간마다 실행
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"배송 문제 처리 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _input_tracking_to_markets_continuously(self):
        """지속적인 마켓 송장 입력"""
        while self.tracking_active:
            try:
                # 송장 입력이 필요한 주문들 조회
                orders = await self._get_orders_needing_tracking_input()
                
                for order in orders:
                    try:
                        await self.input_tracking_to_market(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 송장 입력 실패: {e}")
                        continue
                
                # 10분마다 실행
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"마켓 송장 입력 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    async def _notify_customers_continuously(self):
        """지속적인 고객 알림"""
        while self.tracking_active:
            try:
                # 알림이 필요한 주문들 조회
                orders = await self._get_orders_needing_notification()
                
                for order in orders:
                    try:
                        await self.notify_customers(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 고객 알림 실패: {e}")
                        continue
                
                # 20분마다 실행
                await asyncio.sleep(1200)
                
            except Exception as e:
                logger.error(f"고객 알림 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    # 헬퍼 메서드들 (실제 구현에서 완성 필요)
    async def _get_wholesale_order(self, wholesale_order_id: str) -> Optional[WholesaleOrder]:
        """도매 주문 조회"""
        pass
    
    async def _get_order(self, order_id: str) -> Optional[Order]:
        """주문 조회"""
        pass
    
    async def _update_tracking_info(self, wholesale_order: WholesaleOrder, tracking_data: Dict[str, Any]):
        """추적 정보 업데이트"""
        pass
    
    async def _check_status_change(self, wholesale_order: WholesaleOrder, tracking_data: Dict[str, Any]) -> bool:
        """상태 변경 확인"""
        pass
    
    async def _handle_status_change(self, wholesale_order: WholesaleOrder, tracking_data: Dict[str, Any]):
        """상태 변경 처리"""
        pass
    
    # 추가 헬퍼 메서드들...
    async def _track_with_unified_api(self, tracking_number: str, carrier: str) -> Dict[str, Any]:
        pass
    
    async def _call_cj_tracking_api(self, tracking_number: str) -> Dict[str, Any]:
        pass
    
    async def _normalize_cj_tracking_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    # 기타 택배사 API 호출 및 정규화 메서드들...
    # (각 택배사별로 구현 필요)