"""
Exception handling service
예외 상황 처리 시스템
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.order_core import Order, OrderItem, OrderStatus
from app.models.order_automation import (
    WholesaleOrder, WholesaleOrderStatus,
    ExceptionCase, OrderProcessingLog
)
from app.services.realtime.websocket_manager import WebSocketManager
from app.services.dashboard.notification_service import NotificationService
from app.services.platforms.coupang_api import CoupangAPI
from app.services.platforms.naver_api import NaverAPI
from app.services.platforms.eleventh_street_api import EleventhStreetAPI

logger = logging.getLogger(__name__)


class ExceptionHandler:
    """예외 상황 처리 시스템"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.platform_apis = {
            'coupang': CoupangAPI(),
            'naver': NaverAPI(),
            '11st': EleventhStreetAPI()
        }
        self.websocket_manager = WebSocketManager()
        self.notification_service = NotificationService(db_session)
        self.exception_handling_active = False
        self.handler_tasks = {}
    
    async def start_exception_handling(self):
        """예외 처리 시스템 시작"""
        try:
            logger.info("예외 처리 시스템 시작")
            self.exception_handling_active = True
            
            # 예외 처리 태스크들 시작
            self.handler_tasks["handle_order_cancellations"] = asyncio.create_task(
                self._handle_order_cancellations_continuously()
            )
            
            self.handler_tasks["process_exchange_requests"] = asyncio.create_task(
                self._process_exchange_requests_continuously()
            )
            
            self.handler_tasks["manage_return_processes"] = asyncio.create_task(
                self._manage_return_processes_continuously()
            )
            
            self.handler_tasks["sync_inventory"] = asyncio.create_task(
                self._sync_inventory_continuously()
            )
            
            self.handler_tasks["handle_stockouts"] = asyncio.create_task(
                self._handle_stockouts_continuously()
            )
            
            self.handler_tasks["find_alternatives"] = asyncio.create_task(
                self._find_alternatives_continuously()
            )
            
            logger.info(f"예외 처리 시스템 {len(self.handler_tasks)}개 태스크 시작됨")
            
        except Exception as e:
            logger.error(f"예외 처리 시스템 시작 실패: {e}")
            raise
    
    async def stop_exception_handling(self):
        """예외 처리 시스템 중지"""
        try:
            logger.info("예외 처리 시스템 중지 시작")
            self.exception_handling_active = False
            
            # 모든 태스크 취소
            for task_name, task in self.handler_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"예외 처리 태스크 {task_name} 취소됨")
            
            self.handler_tasks.clear()
            logger.info("예외 처리 시스템 중지 완료")
            
        except Exception as e:
            logger.error(f"예외 처리 시스템 중지 실패: {e}")
    
    async def handle_order_cancellation(self, order_id: str, cancellation_reason: str = None) -> Dict[str, Any]:
        """주문 취소 처리"""
        try:
            start_time = datetime.utcnow()
            
            # 주문 조회
            order = await self._get_order_with_details(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 취소 가능 여부 확인
            if not order.can_cancel:
                return {
                    'success': False,
                    'error': '취소할 수 없는 주문 상태입니다'
                }
            
            # 도매 주문 취소 처리
            wholesale_orders = await self._get_wholesale_orders_by_order_id(order_id)
            wholesale_cancellation_results = []
            
            for wholesale_order in wholesale_orders:
                if wholesale_order.status in [WholesaleOrderStatus.PENDING, WholesaleOrderStatus.SUBMITTED]:
                    # 도매처에 취소 요청
                    cancel_result = await self._cancel_wholesale_order(wholesale_order, cancellation_reason)
                    wholesale_cancellation_results.append(cancel_result)
                elif wholesale_order.status in [WholesaleOrderStatus.CONFIRMED, WholesaleOrderStatus.PROCESSING]:
                    # 취소 불가능한 경우 예외 케이스 생성
                    await self._create_exception_case(
                        order_id=order.id,
                        wholesale_order_id=wholesale_order.id,
                        exception_type='cancellation_impossible',
                        description=f"도매 주문이 이미 처리 중이어서 취소할 수 없습니다. 도매업체: {wholesale_order.wholesaler.name}"
                    )
            
            # 플랫폼 주문 취소
            platform_cancellation = await self._cancel_platform_order(order, cancellation_reason)
            
            if platform_cancellation['success']:
                # 주문 상태 업데이트
                order.status = OrderStatus.CANCELLED
                order.internal_notes = f"취소 사유: {cancellation_reason or '고객 요청'}"
                
                await self.db.commit()
                
                # 취소 처리 로그 기록
                processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self._log_exception_processing(
                    order_id=order_id,
                    action='handle_order_cancellation',
                    success=True,
                    processing_time_ms=int(processing_time),
                    output_data={
                        'wholesale_cancellations': len(wholesale_cancellation_results),
                        'platform_cancelled': platform_cancellation['success']
                    }
                )
                
                # 고객 알림
                await self._notify_customer_cancellation(order, cancellation_reason)
                
                # 실시간 알림
                await self._send_exception_notification('order_cancelled', {
                    'order_id': order_id,
                    'order_number': order.order_number,
                    'reason': cancellation_reason
                })
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'wholesale_cancellations': wholesale_cancellation_results,
                    'platform_cancellation': platform_cancellation,
                    'customer_notified': True
                }
            else:
                # 플랫폼 취소 실패
                await self._create_exception_case(
                    order_id=order.id,
                    exception_type='platform_cancellation_failed',
                    description=f"플랫폼 주문 취소 실패: {platform_cancellation['error']}"
                )
                
                return {
                    'success': False,
                    'error': f"플랫폼 주문 취소 실패: {platform_cancellation['error']}"
                }
            
        except Exception as e:
            logger.error(f"주문 취소 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_exchange_request(self, order_id: str, exchange_items: List[Dict[str, Any]], 
                                     exchange_reason: str = None) -> Dict[str, Any]:
        """교환 요청 처리"""
        try:
            # 주문 조회
            order = await self._get_order_with_details(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 교환 가능 여부 확인
            exchange_eligibility = await self._check_exchange_eligibility(order, exchange_items)
            if not exchange_eligibility['eligible']:
                return {
                    'success': False,
                    'error': exchange_eligibility['reason']
                }
            
            # 교환 상품 재고 확인
            availability_check = await self._check_exchange_product_availability(exchange_items)
            
            if availability_check['all_available']:
                # 자동 교환 처리
                exchange_result = await self._process_automatic_exchange(
                    order, exchange_items, exchange_reason
                )
                
                if exchange_result['success']:
                    # 고객 알림
                    await self._notify_customer_exchange_approved(order, exchange_items)
                    
                    return {
                        'success': True,
                        'exchange_type': 'automatic',
                        'new_order_id': exchange_result['new_order_id'],
                        'tracking_info': exchange_result['tracking_info']
                    }
                else:
                    # 자동 교환 실패 시 수동 처리 필요
                    await self._create_exception_case(
                        order_id=order.id,
                        exception_type='exchange_processing_failed',
                        description=f"자동 교환 처리 실패: {exchange_result['error']}"
                    )
                    
                    return {
                        'success': False,
                        'error': exchange_result['error'],
                        'requires_manual_processing': True
                    }
            else:
                # 일부 상품 품절로 수동 처리 필요
                await self._create_exception_case(
                    order_id=order.id,
                    exception_type='exchange_stock_shortage',
                    description=f"교환 상품 품절: {availability_check['unavailable_items']}"
                )
                
                # 고객에게 대안 제시
                await self._notify_customer_exchange_alternatives(order, availability_check)
                
                return {
                    'success': False,
                    'error': '일부 교환 상품이 품절되었습니다',
                    'unavailable_items': availability_check['unavailable_items'],
                    'alternatives_suggested': True
                }
            
        except Exception as e:
            logger.error(f"교환 요청 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def manage_return_process(self, order_id: str, return_items: List[Dict[str, Any]], 
                                  return_reason: str = None) -> Dict[str, Any]:
        """반품 프로세스 관리"""
        try:
            # 주문 조회
            order = await self._get_order_with_details(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 반품 가능 여부 확인
            return_eligibility = await self._check_return_eligibility(order, return_items)
            if not return_eligibility['eligible']:
                return {
                    'success': False,
                    'error': return_eligibility['reason']
                }
            
            # 반품 유형 결정 (전체/부분 반품)
            return_type = await self._determine_return_type(order, return_items)
            
            # 반품 승인 및 처리
            return_approval = await self._approve_return_request(order, return_items, return_reason, return_type)
            
            if return_approval['approved']:
                # 반품 라벨 생성
                return_label = await self._generate_return_label(order, return_items)
                
                # 도매처 반품 처리
                wholesale_return_results = []
                if return_approval['wholesale_return_required']:
                    wholesale_return_results = await self._process_wholesale_returns(order, return_items)
                
                # 환불 처리 (부분 또는 전체)
                refund_result = await self._process_refund(order, return_items, return_type)
                
                # 고객 알림
                await self._notify_customer_return_approved(order, return_items, return_label)
                
                # 실시간 알림
                await self._send_exception_notification('return_processed', {
                    'order_id': order_id,
                    'return_type': return_type,
                    'refund_amount': refund_result['amount']
                })
                
                return {
                    'success': True,
                    'return_type': return_type,
                    'return_label': return_label,
                    'refund_amount': refund_result['amount'],
                    'wholesale_returns': wholesale_return_results,
                    'customer_notified': True
                }
            else:
                # 반품 거부
                await self._notify_customer_return_rejected(order, return_items, return_approval['reason'])
                
                return {
                    'success': False,
                    'error': f"반품 거부: {return_approval['reason']}",
                    'customer_notified': True
                }
            
        except Exception as e:
            logger.error(f"반품 프로세스 관리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sync_inventory(self) -> Dict[str, Any]:
        """재고 동기화"""
        try:
            # 모든 활성 도매업체 조회
            wholesalers = await self._get_active_wholesalers()
            
            sync_results = []
            
            for wholesaler in wholesalers:
                try:
                    # 도매업체별 재고 동기화
                    wholesaler_sync = await self._sync_wholesaler_inventory(wholesaler)
                    sync_results.append(wholesaler_sync)
                    
                    # 재고 부족 상품 감지
                    if wholesaler_sync['low_stock_items']:
                        await self._handle_low_stock_items(wholesaler, wholesaler_sync['low_stock_items'])
                    
                    # 품절 상품 처리
                    if wholesaler_sync['out_of_stock_items']:
                        await self._handle_out_of_stock_items(wholesaler, wholesaler_sync['out_of_stock_items'])
                
                except Exception as e:
                    logger.error(f"도매업체 {wholesaler.name} 재고 동기화 실패: {e}")
                    sync_results.append({
                        'wholesaler_id': wholesaler.id,
                        'wholesaler_name': wholesaler.name,
                        'success': False,
                        'error': str(e)
                    })
            
            # 동기화 결과 요약
            successful_syncs = sum(1 for result in sync_results if result['success'])
            total_updated_items = sum(result.get('updated_items', 0) for result in sync_results if result['success'])
            
            return {
                'success': True,
                'total_wholesalers': len(wholesalers),
                'successful_syncs': successful_syncs,
                'total_updated_items': total_updated_items,
                'sync_results': sync_results
            }
            
        except Exception as e:
            logger.error(f"재고 동기화 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_stockout(self, product_sku: str, wholesaler_id: str) -> Dict[str, Any]:
        """품절 처리"""
        try:
            # 품절된 상품의 영향받는 주문 조회
            affected_orders = await self._get_orders_affected_by_stockout(product_sku, wholesaler_id)
            
            stockout_handling_results = []
            
            for order in affected_orders:
                try:
                    # 대체 상품 찾기
                    alternatives = await self.find_alternatives(product_sku, order.id)
                    
                    if alternatives['success'] and alternatives['alternatives']:
                        # 자동 대체 가능한 경우
                        best_alternative = alternatives['alternatives'][0]  # 최적 대체 상품
                        
                        if best_alternative['auto_replaceable']:
                            # 자동 대체 실행
                            replacement_result = await self._execute_automatic_replacement(
                                order, product_sku, best_alternative
                            )
                            
                            stockout_handling_results.append({
                                'order_id': str(order.id),
                                'action': 'auto_replaced',
                                'alternative_sku': best_alternative['sku'],
                                'success': replacement_result['success']
                            })
                            
                            # 고객 알림
                            if replacement_result['success']:
                                await self._notify_customer_product_replacement(
                                    order, product_sku, best_alternative
                                )
                        else:
                            # 수동 선택 필요
                            await self._create_alternative_selection_case(
                                order, product_sku, alternatives['alternatives']
                            )
                            
                            stockout_handling_results.append({
                                'order_id': str(order.id),
                                'action': 'manual_selection_required',
                                'alternatives_count': len(alternatives['alternatives'])
                            })
                    else:
                        # 대체 상품이 없는 경우
                        await self._handle_no_alternative_available(order, product_sku)
                        
                        stockout_handling_results.append({
                            'order_id': str(order.id),
                            'action': 'no_alternatives',
                            'requires_cancellation': True
                        })
                
                except Exception as e:
                    logger.error(f"주문 {order.id} 품절 처리 실패: {e}")
                    stockout_handling_results.append({
                        'order_id': str(order.id),
                        'action': 'error',
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'product_sku': product_sku,
                'wholesaler_id': wholesaler_id,
                'affected_orders': len(affected_orders),
                'handling_results': stockout_handling_results
            }
            
        except Exception as e:
            logger.error(f"품절 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def find_alternatives(self, product_sku: str, order_id: str = None) -> Dict[str, Any]:
        """대체 상품 찾기"""
        try:
            # 원본 상품 정보 조회
            original_product = await self._get_product_by_sku(product_sku)
            if not original_product:
                return {
                    'success': False,
                    'error': '원본 상품을 찾을 수 없습니다'
                }
            
            # 대체 상품 검색 전략
            search_strategies = [
                'same_brand_similar_model',  # 같은 브랜드 유사 모델
                'similar_features',         # 유사한 기능/특성
                'same_category',           # 같은 카테고리
                'price_range'              # 유사한 가격대
            ]
            
            all_alternatives = []
            
            for strategy in search_strategies:
                alternatives = await self._search_alternatives_by_strategy(
                    original_product, strategy
                )
                
                # 중복 제거 및 점수 계산
                for alt in alternatives:
                    if not any(existing['sku'] == alt['sku'] for existing in all_alternatives):
                        alt['match_strategy'] = strategy
                        alt['similarity_score'] = await self._calculate_similarity_score(
                            original_product, alt, strategy
                        )
                        all_alternatives.append(alt)
            
            # 점수 순으로 정렬
            all_alternatives.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # 재고 및 가격 검증
            verified_alternatives = []
            for alt in all_alternatives[:10]:  # 상위 10개만 검증
                verification = await self._verify_alternative_availability(alt, order_id)
                if verification['available']:
                    alt.update(verification)
                    verified_alternatives.append(alt)
            
            return {
                'success': True,
                'original_sku': product_sku,
                'alternatives': verified_alternatives,
                'total_found': len(all_alternatives),
                'verified_count': len(verified_alternatives)
            }
            
        except Exception as e:
            logger.error(f"대체 상품 찾기 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 백그라운드 태스크들
    async def _handle_order_cancellations_continuously(self):
        """지속적인 주문 취소 처리"""
        while self.exception_handling_active:
            try:
                # 취소 요청이 있는 주문들 조회
                cancellation_requests = await self._get_pending_cancellation_requests()
                
                for request in cancellation_requests:
                    try:
                        await self.handle_order_cancellation(
                            str(request.order_id), 
                            request.cancellation_reason
                        )
                    except Exception as e:
                        logger.error(f"취소 요청 {request.id} 처리 실패: {e}")
                        continue
                
                # 30분마다 실행
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"주문 취소 처리 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    async def _process_exchange_requests_continuously(self):
        """지속적인 교환 요청 처리"""
        while self.exception_handling_active:
            try:
                # 교환 요청이 있는 주문들 조회
                exchange_requests = await self._get_pending_exchange_requests()
                
                for request in exchange_requests:
                    try:
                        await self.process_exchange_request(
                            str(request.order_id),
                            request.exchange_items,
                            request.exchange_reason
                        )
                    except Exception as e:
                        logger.error(f"교환 요청 {request.id} 처리 실패: {e}")
                        continue
                
                # 1시간마다 실행
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"교환 요청 처리 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _manage_return_processes_continuously(self):
        """지속적인 반품 프로세스 관리"""
        while self.exception_handling_active:
            try:
                # 반품 요청이 있는 주문들 조회
                return_requests = await self._get_pending_return_requests()
                
                for request in return_requests:
                    try:
                        await self.manage_return_process(
                            str(request.order_id),
                            request.return_items,
                            request.return_reason
                        )
                    except Exception as e:
                        logger.error(f"반품 요청 {request.id} 처리 실패: {e}")
                        continue
                
                # 2시간마다 실행
                await asyncio.sleep(7200)
                
            except Exception as e:
                logger.error(f"반품 프로세스 관리 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _sync_inventory_continuously(self):
        """지속적인 재고 동기화"""
        while self.exception_handling_active:
            try:
                await self.sync_inventory()
                
                # 4시간마다 실행
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error(f"재고 동기화 태스크 오류: {e}")
                await asyncio.sleep(1800)
    
    async def _handle_stockouts_continuously(self):
        """지속적인 품절 처리"""
        while self.exception_handling_active:
            try:
                # 품절된 상품들 조회
                stockout_products = await self._get_stockout_products()
                
                for product in stockout_products:
                    try:
                        await self.handle_stockout(product.sku, str(product.wholesaler_id))
                    except Exception as e:
                        logger.error(f"품절 상품 {product.sku} 처리 실패: {e}")
                        continue
                
                # 30분마다 실행
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"품절 처리 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _find_alternatives_continuously(self):
        """지속적인 대체 상품 찾기"""
        while self.exception_handling_active:
            try:
                # 대체 상품이 필요한 케이스들 조회
                alternative_needed_cases = await self._get_cases_needing_alternatives()
                
                for case in alternative_needed_cases:
                    try:
                        await self.find_alternatives(case.product_sku, str(case.order_id))
                    except Exception as e:
                        logger.error(f"대체 상품 찾기 케이스 {case.id} 처리 실패: {e}")
                        continue
                
                # 1시간마다 실행
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"대체 상품 찾기 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    # 헬퍼 메서드들 (실제 구현에서 완성 필요)
    async def _get_order_with_details(self, order_id: str) -> Optional[Order]:
        """주문 상세 정보 조회"""
        pass
    
    async def _get_wholesale_orders_by_order_id(self, order_id: str) -> List[WholesaleOrder]:
        """주문의 도매 주문들 조회"""
        pass
    
    async def _cancel_wholesale_order(self, wholesale_order: WholesaleOrder, reason: str) -> Dict[str, Any]:
        """도매 주문 취소"""
        pass
    
    async def _cancel_platform_order(self, order: Order, reason: str) -> Dict[str, Any]:
        """플랫폼 주문 취소"""
        pass
    
    async def _create_exception_case(self, order_id: str, exception_type: str, description: str,
                                   wholesale_order_id: str = None):
        """예외 케이스 생성"""
        pass
    
    async def _log_exception_processing(self, order_id: str, action: str, success: bool,
                                      processing_time_ms: int = None, output_data: Dict = None):
        """예외 처리 로그 기록"""
        pass
    
    async def _send_exception_notification(self, event_type: str, data: Dict[str, Any]):
        """예외 상황 알림 발송"""
        pass
    
    # 추가 헬퍼 메서드들...
    async def _notify_customer_cancellation(self, order: Order, reason: str):
        pass
    
    async def _check_exchange_eligibility(self, order: Order, exchange_items: List[Dict]) -> Dict[str, Any]:
        pass
    
    async def _process_automatic_exchange(self, order: Order, exchange_items: List[Dict], reason: str) -> Dict[str, Any]:
        pass