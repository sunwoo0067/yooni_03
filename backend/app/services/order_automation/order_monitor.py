"""
Order monitoring service
실시간 주문 모니터링 시스템
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.order_core import Order, OrderStatus, PaymentStatus
from app.models.order_automation import OrderProcessingLog, ExceptionCase
from app.models.platform_account import PlatformAccount
from app.services.platforms.coupang_api import CoupangAPI
from app.services.platforms.naver_api import NaverAPI
from app.services.platforms.eleventh_street_api import EleventhStreetAPI
from app.services.realtime.websocket_manager import ConnectionManager as WebSocketManager
from app.services.dashboard.notification_service import NotificationService

logger = logging.getLogger(__name__)


class OrderMonitor:
    """실시간 주문 모니터링 시스템"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.platform_apis = {
            'coupang': CoupangAPI(),
            'naver': NaverAPI(),
            '11st': EleventhStreetAPI()
        }
        self.websocket_manager = WebSocketManager()
        self.notification_service = NotificationService(db_session)
        self.monitoring_active = False
        self.monitor_tasks = {}
        
    async def start_monitoring(self):
        """주문 모니터링 시작"""
        try:
            logger.info("주문 모니터링 시작")
            self.monitoring_active = True
            
            # 각 플랫폼별 모니터링 태스크 시작
            for platform in self.platform_apis.keys():
                task_name = f"monitor_{platform}_orders"
                self.monitor_tasks[task_name] = asyncio.create_task(
                    self._monitor_platform_orders(platform)
                )
            
            # 주문 데이터 검증 태스크
            self.monitor_tasks["validate_orders"] = asyncio.create_task(
                self._validate_orders_continuously()
            )
            
            # 주문 매핑 태스크
            self.monitor_tasks["map_orders"] = asyncio.create_task(
                self._map_wholesale_products_continuously()
            )
            
            logger.info(f"총 {len(self.monitor_tasks)}개 모니터링 태스크 시작됨")
            
        except Exception as e:
            logger.error(f"주문 모니터링 시작 실패: {e}")
            raise
    
    async def stop_monitoring(self):
        """주문 모니터링 중지"""
        try:
            logger.info("주문 모니터링 중지 시작")
            self.monitoring_active = False
            
            # 모든 태스크 취소
            for task_name, task in self.monitor_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"태스크 {task_name} 취소됨")
            
            self.monitor_tasks.clear()
            logger.info("주문 모니터링 중지 완료")
            
        except Exception as e:
            logger.error(f"주문 모니터링 중지 실패: {e}")
    
    async def monitor_coupang_orders(self) -> List[Dict[str, Any]]:
        """쿠팡 주문 모니터링"""
        try:
            accounts = await self._get_platform_accounts('coupang')
            new_orders = []
            
            for account in accounts:
                try:
                    # 쿠팡 API를 통해 새 주문 조회
                    api_orders = await self.platform_apis['coupang'].get_new_orders(
                        account_credentials=account.credentials,
                        since=datetime.utcnow() - timedelta(hours=1)
                    )
                    
                    for api_order in api_orders:
                        # 이미 존재하는 주문인지 확인
                        existing_order = await self._check_existing_order(
                            platform_order_id=api_order['orderId'],
                            platform_account_id=account.id
                        )
                        
                        if not existing_order:
                            # 새 주문 처리
                            order = await self._process_new_order(
                                platform_data=api_order,
                                account=account,
                                platform='coupang'
                            )
                            if order:
                                new_orders.append(order)
                
                except Exception as e:
                    logger.error(f"쿠팡 계정 {account.id} 주문 조회 실패: {e}")
                    await self._log_monitoring_error(account.id, 'coupang', str(e))
            
            return new_orders
            
        except Exception as e:
            logger.error(f"쿠팡 주문 모니터링 실패: {e}")
            return []
    
    async def monitor_naver_orders(self) -> List[Dict[str, Any]]:
        """네이버 주문 모니터링"""
        try:
            accounts = await self._get_platform_accounts('naver')
            new_orders = []
            
            for account in accounts:
                try:
                    # 네이버 API를 통해 새 주문 조회
                    api_orders = await self.platform_apis['naver'].get_new_orders(
                        account_credentials=account.credentials,
                        since=datetime.utcnow() - timedelta(hours=1)
                    )
                    
                    for api_order in api_orders:
                        existing_order = await self._check_existing_order(
                            platform_order_id=api_order['orderNo'],
                            platform_account_id=account.id
                        )
                        
                        if not existing_order:
                            order = await self._process_new_order(
                                platform_data=api_order,
                                account=account,
                                platform='naver'
                            )
                            if order:
                                new_orders.append(order)
                
                except Exception as e:
                    logger.error(f"네이버 계정 {account.id} 주문 조회 실패: {e}")
                    await self._log_monitoring_error(account.id, 'naver', str(e))
            
            return new_orders
            
        except Exception as e:
            logger.error(f"네이버 주문 모니터링 실패: {e}")
            return []
    
    async def monitor_11st_orders(self) -> List[Dict[str, Any]]:
        """11번가 주문 모니터링"""
        try:
            accounts = await self._get_platform_accounts('11st')
            new_orders = []
            
            for account in accounts:
                try:
                    # 11번가 API를 통해 새 주문 조회
                    api_orders = await self.platform_apis['11st'].get_new_orders(
                        account_credentials=account.credentials,
                        since=datetime.utcnow() - timedelta(hours=1)
                    )
                    
                    for api_order in api_orders:
                        existing_order = await self._check_existing_order(
                            platform_order_id=api_order['orderSeq'],
                            platform_account_id=account.id
                        )
                        
                        if not existing_order:
                            order = await self._process_new_order(
                                platform_data=api_order,
                                account=account,
                                platform='11st'
                            )
                            if order:
                                new_orders.append(order)
                
                except Exception as e:
                    logger.error(f"11번가 계정 {account.id} 주문 조회 실패: {e}")
                    await self._log_monitoring_error(account.id, '11st', str(e))
            
            return new_orders
            
        except Exception as e:
            logger.error(f"11번가 주문 모니터링 실패: {e}")
            return []
    
    async def process_new_order(self, platform_data: Dict[str, Any], account: PlatformAccount, platform: str) -> Optional[Dict[str, Any]]:
        """신규 주문 처리"""
        try:
            start_time = datetime.utcnow()
            
            # 주문 데이터 정규화
            normalized_data = await self._normalize_order_data(platform_data, platform)
            
            # 주문 생성
            order = await self._create_order_from_data(normalized_data, account)
            
            # 주문 검증
            validation_result = await self.validate_order_data(order)
            if not validation_result['valid']:
                await self._create_exception_case(
                    order_id=order.id,
                    exception_type='validation_failed',
                    description=f"주문 데이터 검증 실패: {validation_result['errors']}"
                )
                return None
            
            # 도매 상품 매핑
            mapping_result = await self.map_to_wholesale_product(order)
            if not mapping_result['success']:
                await self._create_exception_case(
                    order_id=order.id,
                    exception_type='product_mapping_failed',
                    description=f"도매 상품 매핑 실패: {mapping_result['error']}"
                )
            
            # 처리 로그 기록
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_order_processing(
                order_id=order.id,
                step='order_received',
                action='process_new_order',
                success=True,
                processing_time_ms=int(processing_time),
                input_data=platform_data,
                output_data={'order_id': str(order.id)}
            )
            
            # 실시간 알림 발송
            await self._send_realtime_notification('new_order', {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'platform': platform,
                'total_amount': float(order.total_amount),
                'customer_name': order.customer_name
            })
            
            return {
                'order_id': order.id,
                'order_number': order.order_number,
                'status': order.status.value,
                'total_amount': float(order.total_amount)
            }
            
        except Exception as e:
            logger.error(f"신규 주문 처리 실패: {e}")
            await self._log_order_processing(
                order_id=None,
                step='order_received',
                action='process_new_order',
                success=False,
                error_message=str(e),
                input_data=platform_data
            )
            return None
    
    async def validate_order_data(self, order: Order) -> Dict[str, Any]:
        """주문 데이터 검증"""
        try:
            errors = []
            
            # 필수 필드 검증
            if not order.customer_name:
                errors.append("고객명이 없습니다")
            
            if not order.shipping_address1:
                errors.append("배송지 주소가 없습니다")
            
            if not order.total_amount or order.total_amount <= 0:
                errors.append("주문 금액이 유효하지 않습니다")
            
            # 주문 아이템 검증
            if not order.order_items:
                errors.append("주문 상품이 없습니다")
            else:
                for item in order.order_items:
                    if not item.sku:
                        errors.append(f"상품 {item.product_name}의 SKU가 없습니다")
                    if item.quantity <= 0:
                        errors.append(f"상품 {item.product_name}의 수량이 유효하지 않습니다")
                    if item.unit_price <= 0:
                        errors.append(f"상품 {item.product_name}의 가격이 유효하지 않습니다")
            
            # 배송 정보 검증
            if order.shipping_city and len(order.shipping_city) < 2:
                errors.append("배송지 도시명이 너무 짧습니다")
            
            # 중복 주문 검증
            duplicate_order = await self._check_duplicate_order(order)
            if duplicate_order:
                errors.append(f"중복 주문입니다 (기존 주문: {duplicate_order.order_number})")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': []
            }
            
        except Exception as e:
            logger.error(f"주문 데이터 검증 실패: {e}")
            return {
                'valid': False,
                'errors': [f"검증 처리 중 오류: {str(e)}"],
                'warnings': []
            }
    
    async def map_to_wholesale_product(self, order: Order) -> Dict[str, Any]:
        """도매 상품 매핑"""
        try:
            mapping_results = []
            
            for order_item in order.order_items:
                # SKU 기반 도매 상품 조회
                wholesale_product = await self._find_wholesale_product_by_sku(order_item.sku)
                
                if wholesale_product:
                    mapping_results.append({
                        'order_item_id': order_item.id,
                        'wholesale_product_id': wholesale_product['id'],
                        'wholesale_sku': wholesale_product['sku'],
                        'wholesale_price': wholesale_product['price'],
                        'supplier': wholesale_product['supplier'],
                        'stock_quantity': wholesale_product['stock_quantity']
                    })
                else:
                    # 매핑 실패 시 대체 상품 검색
                    alternative_products = await self._find_alternative_products(order_item)
                    
                    if alternative_products:
                        mapping_results.append({
                            'order_item_id': order_item.id,
                            'alternatives': alternative_products,
                            'requires_manual_selection': True
                        })
                    else:
                        # 완전히 매핑 실패
                        await self._create_exception_case(
                            order_id=order.id,
                            exception_type='product_not_found',
                            description=f"상품 {order_item.sku} ({order_item.product_name})에 대한 도매 상품을 찾을 수 없습니다"
                        )
                        return {
                            'success': False,
                            'error': f"도매 상품 매핑 실패: {order_item.sku}"
                        }
            
            return {
                'success': True,
                'mappings': mapping_results
            }
            
        except Exception as e:
            logger.error(f"도매 상품 매핑 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _monitor_platform_orders(self, platform: str):
        """플랫폼별 주문 모니터링 (백그라운드 태스크)"""
        while self.monitoring_active:
            try:
                if platform == 'coupang':
                    await self.monitor_coupang_orders()
                elif platform == 'naver':
                    await self.monitor_naver_orders()
                elif platform == '11st':
                    await self.monitor_11st_orders()
                
                # 모니터링 간격 (30초)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"{platform} 주문 모니터링 태스크 오류: {e}")
                # 오류 발생 시 1분 대기 후 재시도
                await asyncio.sleep(60)
    
    async def _validate_orders_continuously(self):
        """지속적인 주문 데이터 검증"""
        while self.monitoring_active:
            try:
                # 최근 생성된 미검증 주문 조회
                unvalidated_orders = await self._get_unvalidated_orders()
                
                for order in unvalidated_orders:
                    await self.validate_order_data(order)
                
                # 5분마다 실행
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"주문 검증 태스크 오류: {e}")
                await asyncio.sleep(60)
    
    async def _map_wholesale_products_continuously(self):
        """지속적인 도매 상품 매핑"""
        while self.monitoring_active:
            try:
                # 매핑되지 않은 주문 조회
                unmapped_orders = await self._get_unmapped_orders()
                
                for order in unmapped_orders:
                    await self.map_to_wholesale_product(order)
                
                # 2분마다 실행
                await asyncio.sleep(120)
                
            except Exception as e:
                logger.error(f"상품 매핑 태스크 오류: {e}")
                await asyncio.sleep(60)
    
    async def _get_platform_accounts(self, platform: str) -> List[PlatformAccount]:
        """플랫폼 계정 조회"""
        try:
            stmt = select(PlatformAccount).where(
                and_(
                    PlatformAccount.platform == platform,
                    PlatformAccount.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"플랫폼 계정 조회 실패: {e}")
            return []
    
    async def _check_existing_order(self, platform_order_id: str, platform_account_id: str) -> Optional[Order]:
        """기존 주문 확인"""
        try:
            stmt = select(Order).where(
                and_(
                    Order.platform_order_id == platform_order_id,
                    Order.platform_account_id == platform_account_id
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"기존 주문 확인 실패: {e}")
            return None
    
    async def _normalize_order_data(self, platform_data: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """플랫폼별 주문 데이터 정규화"""
        if platform == 'coupang':
            return await self._normalize_coupang_order_data(platform_data)
        elif platform == 'naver':
            return await self._normalize_naver_order_data(platform_data)
        elif platform == '11st':
            return await self._normalize_11st_order_data(platform_data)
        else:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
    
    async def _normalize_coupang_order_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """쿠팡 주문 데이터 정규화"""
        return {
            'platform_order_id': data['orderId'],
            'order_date': datetime.fromisoformat(data['orderDate']),
            'customer_name': data['orderer']['name'],
            'customer_email': data['orderer'].get('email'),
            'customer_phone': data['orderer'].get('phone'),
            'shipping_address1': data['receiver']['address1'],
            'shipping_address2': data['receiver'].get('address2'),
            'shipping_city': data['receiver']['city'],
            'shipping_postal_code': data['receiver']['zipCode'],
            'total_amount': data['totalPrice'],
            'currency': 'KRW',
            'platform_data': data
        }
    
    async def _normalize_naver_order_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """네이버 주문 데이터 정규화"""
        return {
            'platform_order_id': data['orderNo'],
            'order_date': datetime.fromisoformat(data['orderDate']),
            'customer_name': data['orderName'],
            'customer_phone': data['orderTel'],
            'shipping_address1': data['receiverAddr1'],
            'shipping_address2': data['receiverAddr2'],
            'shipping_city': data['receiverCity'],
            'shipping_postal_code': data['receiverZipCode'],
            'total_amount': data['totalPayAmt'],
            'currency': 'KRW',
            'platform_data': data
        }
    
    async def _normalize_11st_order_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """11번가 주문 데이터 정규화"""
        return {
            'platform_order_id': data['orderSeq'],
            'order_date': datetime.fromisoformat(data['orderDt']),
            'customer_name': data['buyerName'],
            'customer_phone': data['buyerPhone'],
            'shipping_address1': data['rcvAddr'],
            'shipping_city': data['rcvCity'],
            'shipping_postal_code': data['rcvZipCd'],
            'total_amount': data['totalOrderAmt'],
            'currency': 'KRW',
            'platform_data': data
        }
    
    async def _create_order_from_data(self, normalized_data: Dict[str, Any], account: PlatformAccount) -> Order:
        """정규화된 데이터로부터 주문 생성"""
        # 실제 구현에서는 Order 객체 생성 및 DB 저장 로직 필요
        pass
    
    async def _log_order_processing(self, order_id: Optional[str], step: str, action: str, 
                                  success: bool, processing_time_ms: Optional[int] = None,
                                  error_message: Optional[str] = None, 
                                  input_data: Optional[Dict] = None,
                                  output_data: Optional[Dict] = None):
        """주문 처리 로그 기록"""
        try:
            log = OrderProcessingLog(
                order_id=order_id,
                processing_step=step,
                action=action,
                success=success,
                error_message=error_message,
                processing_time_ms=processing_time_ms,
                input_data=input_data,
                output_data=output_data,
                processor_name='OrderMonitor'
            )
            
            self.db.add(log)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"주문 처리 로그 기록 실패: {e}")
    
    async def _send_realtime_notification(self, event_type: str, data: Dict[str, Any]):
        """실시간 알림 발송"""
        try:
            await self.websocket_manager.broadcast_to_channel(
                channel='order_monitoring',
                message={
                    'type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"실시간 알림 발송 실패: {e}")
    
    async def _create_exception_case(self, order_id: str, exception_type: str, description: str):
        """예외 상황 케이스 생성"""
        try:
            exception_case = ExceptionCase(
                order_id=order_id,
                exception_type=exception_type,
                title=f"{exception_type} 예외 발생",
                description=description,
                severity='medium'
            )
            
            self.db.add(exception_case)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"예외 케이스 생성 실패: {e}")
    
    async def _log_monitoring_error(self, account_id: str, platform: str, error_message: str):
        """모니터링 오류 로그"""
        logger.error(f"모니터링 오류 - 계정: {account_id}, 플랫폼: {platform}, 오류: {error_message}")
    
    # 추가 헬퍼 메서드들은 실제 구현에서 완성 필요
    async def _check_duplicate_order(self, order: Order) -> Optional[Order]:
        """중복 주문 확인"""
        pass
    
    async def _find_wholesale_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """SKU로 도매 상품 조회"""
        pass
    
    async def _find_alternative_products(self, order_item) -> List[Dict[str, Any]]:
        """대체 상품 검색"""
        pass
    
    async def _get_unvalidated_orders(self) -> List[Order]:
        """미검증 주문 조회"""
        pass
    
    async def _get_unmapped_orders(self) -> List[Order]:
        """매핑되지 않은 주문 조회"""
        pass