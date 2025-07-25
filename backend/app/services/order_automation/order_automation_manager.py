"""
Order automation manager
주문 처리 자동화 통합 관리자
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from .order_monitor import OrderMonitor
from .auto_order_system import AutoOrderSystem
from .shipping_tracker import ShippingTracker
from .auto_settlement import AutoSettlement
from .exception_handler import ExceptionHandler
from app.services.realtime.websocket_manager import WebSocketManager
from app.services.dashboard.notification_service import NotificationService

logger = logging.getLogger(__name__)


class OrderAutomationManager:
    """주문 처리 자동화 통합 관리자"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # 각 모듈 초기화
        self.order_monitor = OrderMonitor(db_session)
        self.auto_order_system = AutoOrderSystem(db_session)
        self.shipping_tracker = ShippingTracker(db_session)
        self.auto_settlement = AutoSettlement(db_session)
        self.exception_handler = ExceptionHandler(db_session)
        
        # 웹소켓 및 알림 서비스
        self.websocket_manager = WebSocketManager()
        self.notification_service = NotificationService(db_session)
        
        # 시스템 상태
        self.is_running = False
        self.automation_tasks = {}
        self.system_health = {
            'order_monitor': False,
            'auto_order_system': False,
            'shipping_tracker': False,
            'auto_settlement': False,
            'exception_handler': False
        }
        
        # 통계 및 성능 모니터링
        self.stats = {
            'orders_processed': 0,
            'automatic_orders_placed': 0,
            'tracking_updates': 0,
            'settlements_generated': 0,
            'exceptions_handled': 0,
            'start_time': None,
            'last_error': None
        }
    
    async def start_automation(self):
        """전체 자동화 시스템 시작"""
        try:
            logger.info("주문 처리 자동화 시스템 시작")
            self.is_running = True
            self.stats['start_time'] = datetime.utcnow()
            
            # 각 모듈 순차적 시작
            await self._start_modules()
            
            # 통합 관리 태스크들 시작
            await self._start_management_tasks()
            
            # 시스템 상태 모니터링 시작
            await self._start_health_monitoring()
            
            # 시작 완료 알림
            await self._send_system_notification('automation_started', {
                'timestamp': datetime.utcnow().isoformat(),
                'modules_started': list(self.system_health.keys())
            })
            
            logger.info("주문 처리 자동화 시스템 시작 완료")
            
        except Exception as e:
            logger.error(f"자동화 시스템 시작 실패: {e}")
            self.stats['last_error'] = str(e)
            await self.stop_automation()
            raise
    
    async def stop_automation(self):
        """전체 자동화 시스템 중지"""
        try:
            logger.info("주문 처리 자동화 시스템 중지 시작")
            self.is_running = False
            
            # 관리 태스크들 중지
            await self._stop_management_tasks()
            
            # 각 모듈 중지
            await self._stop_modules()
            
            # 시스템 상태 초기화
            for module in self.system_health:
                self.system_health[module] = False
            
            # 중지 완료 알림
            await self._send_system_notification('automation_stopped', {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': self._calculate_uptime()
            })
            
            logger.info("주문 처리 자동화 시스템 중지 완료")
            
        except Exception as e:
            logger.error(f"자동화 시스템 중지 실패: {e}")
            self.stats['last_error'] = str(e)
    
    async def restart_automation(self):
        """자동화 시스템 재시작"""
        try:
            logger.info("주문 처리 자동화 시스템 재시작")
            
            await self.stop_automation()
            await asyncio.sleep(5)  # 안전한 재시작을 위한 대기
            await self.start_automation()
            
            logger.info("주문 처리 자동화 시스템 재시작 완료")
            
        except Exception as e:
            logger.error(f"자동화 시스템 재시작 실패: {e}")
            raise
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            # 각 모듈 상태 확인
            module_statuses = {}
            for module_name, is_healthy in self.system_health.items():
                module = getattr(self, module_name)
                module_statuses[module_name] = {
                    'healthy': is_healthy,
                    'active': getattr(module, f'{module_name.split("_")[0]}_active', False),
                    'tasks_count': len(getattr(module, f'{module_name.split("_")[0]}_tasks', {}))
                }
            
            # 성능 통계
            uptime = self._calculate_uptime()
            
            return {
                'system_running': self.is_running,
                'uptime_seconds': uptime,
                'uptime_formatted': self._format_uptime(uptime),
                'modules': module_statuses,
                'statistics': self.stats.copy(),
                'performance_metrics': await self._get_performance_metrics(),
                'last_health_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"시스템 상태 조회 실패: {e}")
            return {
                'system_running': False,
                'error': str(e)
            }
    
    async def process_order_end_to_end(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """주문 처리 end-to-end 프로세스"""
        try:
            start_time = datetime.utcnow()
            process_id = f"order_process_{start_time.strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"주문 처리 프로세스 시작: {process_id}")
            
            # 1단계: 주문 모니터링 및 검증
            monitor_result = await self.order_monitor.process_new_order(
                platform_data=order_data['platform_data'],
                account=order_data['account'],
                platform=order_data['platform']
            )
            
            if not monitor_result:
                return {
                    'success': False,
                    'stage': 'monitoring',
                    'error': '주문 모니터링 실패'
                }
            
            order_id = monitor_result['order_id']
            
            # 2단계: 자동 발주 시스템
            auto_order_results = []
            order_items = await self._get_order_items(order_id)
            
            for order_item in order_items:
                # 최적 공급업체 선택
                best_supplier = await self.auto_order_system._select_best_supplier(order_item)
                
                if best_supplier:
                    platform = best_supplier['platform']
                    if platform == 'zentrade':
                        result = await self.auto_order_system.place_order_zentrade(
                            order_item, best_supplier['wholesaler']
                        )
                    elif platform == 'ownerclan':
                        result = await self.auto_order_system.place_order_ownerclan(
                            order_item, best_supplier['wholesaler']
                        )
                    elif platform == 'domeggook':
                        result = await self.auto_order_system.place_order_domeggook(
                            order_item, best_supplier['wholesaler']
                        )
                    else:
                        result = {
                            'success': False,
                            'error': f'지원하지 않는 플랫폼: {platform}'
                        }
                    
                    auto_order_results.append(result)
                else:
                    # 공급업체를 찾을 수 없는 경우 예외 처리
                    await self.exception_handler._create_exception_case(
                        order_id=order_id,
                        exception_type='supplier_not_found',
                        description=f'상품 {order_item.sku}에 대한 공급업체를 찾을 수 없습니다'
                    )
            
            # 3단계: 배송 추적 시작 (도매 주문이 성공한 경우)
            tracking_setup_results = []
            successful_orders = [r for r in auto_order_results if r.get('success')]
            
            for order_result in successful_orders:
                tracking_setup = await self.shipping_tracker.get_tracking_number(
                    order_result['wholesale_order_id']
                )
                tracking_setup_results.append(tracking_setup)
            
            # 4단계: 정산 데이터 생성
            settlement_result = await self.auto_settlement.generate_settlement(order_id)
            
            # 처리 완료 시간 계산
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 통계 업데이트
            self.stats['orders_processed'] += 1
            self.stats['automatic_orders_placed'] += len(successful_orders)
            
            # 프로세스 완료 알림
            await self._send_process_notification('order_processed', {
                'process_id': process_id,
                'order_id': order_id,
                'processing_time_seconds': processing_time,
                'auto_orders_placed': len(successful_orders),
                'settlement_generated': settlement_result.get('success', False)
            })
            
            return {
                'success': True,
                'process_id': process_id,
                'order_id': order_id,
                'processing_time_seconds': processing_time,
                'stages': {
                    'monitoring': monitor_result,
                    'auto_ordering': auto_order_results,
                    'tracking_setup': tracking_setup_results,
                    'settlement': settlement_result
                },
                'summary': {
                    'total_items': len(order_items),
                    'successful_orders': len(successful_orders),
                    'failed_orders': len(auto_order_results) - len(successful_orders),
                    'tracking_enabled': len([t for t in tracking_setup_results if t.get('success')]),
                    'settlement_ready': settlement_result.get('success', False)
                }
            }
            
        except Exception as e:
            logger.error(f"주문 처리 프로세스 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'unknown'
            }
    
    async def handle_system_exception(self, exception_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """시스템 레벨 예외 처리"""
        try:
            logger.warning(f"시스템 예외 발생: {exception_type}")
            
            # 예외 유형별 처리
            if exception_type == 'module_failure':
                # 모듈 실패 시 재시작 시도
                failed_module = context.get('module')
                if failed_module in self.system_health:
                    await self._restart_module(failed_module)
                    
            elif exception_type == 'database_connection_lost':
                # 데이터베이스 연결 실패 시 재연결 시도
                await self._reconnect_database()
                
            elif exception_type == 'api_rate_limit':
                # API 사용량 제한 시 대기 및 재시도
                await self._handle_rate_limit(context)
                
            elif exception_type == 'critical_error':
                # 치명적 오류 시 시스템 중지
                await self.stop_automation()
                
            else:
                # 일반적인 예외는 exception_handler에 위임
                await self.exception_handler._create_exception_case(
                    order_id=context.get('order_id'),
                    exception_type=exception_type,
                    description=f"시스템 예외: {context}"
                )
            
            return {
                'success': True,
                'exception_type': exception_type,
                'handled': True
            }
            
        except Exception as e:
            logger.error(f"시스템 예외 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _start_modules(self):
        """각 모듈 시작"""
        try:
            # 순서가 중요함 - 의존성 고려
            modules_to_start = [
                ('order_monitor', self.order_monitor.start_monitoring),
                ('auto_order_system', self.auto_order_system.start_auto_ordering),
                ('shipping_tracker', self.shipping_tracker.start_tracking),
                ('auto_settlement', self.auto_settlement.start_auto_settlement),
                ('exception_handler', self.exception_handler.start_exception_handling)
            ]
            
            for module_name, start_method in modules_to_start:
                try:
                    await start_method()
                    self.system_health[module_name] = True
                    logger.info(f"모듈 {module_name} 시작 완료")
                except Exception as e:
                    logger.error(f"모듈 {module_name} 시작 실패: {e}")
                    self.system_health[module_name] = False
                    raise
            
        except Exception as e:
            logger.error(f"모듈 시작 실패: {e}")
            raise
    
    async def _stop_modules(self):
        """각 모듈 중지"""
        try:
            # 시작의 역순으로 중지
            modules_to_stop = [
                ('exception_handler', self.exception_handler.stop_exception_handling),
                ('auto_settlement', self.auto_settlement.stop_auto_settlement),
                ('shipping_tracker', self.shipping_tracker.stop_tracking),
                ('auto_order_system', self.auto_order_system.stop_auto_ordering),
                ('order_monitor', self.order_monitor.stop_monitoring)
            ]
            
            for module_name, stop_method in modules_to_stop:
                try:
                    await stop_method()
                    self.system_health[module_name] = False
                    logger.info(f"모듈 {module_name} 중지 완료")
                except Exception as e:
                    logger.error(f"모듈 {module_name} 중지 실패: {e}")
            
        except Exception as e:
            logger.error(f"모듈 중지 실패: {e}")
    
    async def _start_management_tasks(self):
        """통합 관리 태스크들 시작"""
        try:
            self.automation_tasks["system_monitor"] = asyncio.create_task(
                self._system_monitor_task()
            )
            
            self.automation_tasks["performance_tracker"] = asyncio.create_task(
                self._performance_tracker_task()
            )
            
            self.automation_tasks["health_checker"] = asyncio.create_task(
                self._health_checker_task()
            )
            
            self.automation_tasks["stats_updater"] = asyncio.create_task(
                self._stats_updater_task()
            )
            
            logger.info(f"통합 관리 태스크 {len(self.automation_tasks)}개 시작됨")
            
        except Exception as e:
            logger.error(f"관리 태스크 시작 실패: {e}")
            raise
    
    async def _stop_management_tasks(self):
        """통합 관리 태스크들 중지"""
        try:
            for task_name, task in self.automation_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"관리 태스크 {task_name} 취소됨")
            
            self.automation_tasks.clear()
            logger.info("통합 관리 태스크 중지 완료")
            
        except Exception as e:
            logger.error(f"관리 태스크 중지 실패: {e}")
    
    async def _start_health_monitoring(self):
        """시스템 상태 모니터링 시작"""
        try:
            # 헬스체크 및 모니터링 로직
            pass
        except Exception as e:
            logger.error(f"상태 모니터링 시작 실패: {e}")
    
    # 백그라운드 태스크들
    async def _system_monitor_task(self):
        """시스템 모니터링 태스크"""
        while self.is_running:
            try:
                # 시스템 전반적인 상태 모니터링
                await self._check_system_health()
                
                # 30초마다 실행
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"시스템 모니터링 태스크 오류: {e}")
                await asyncio.sleep(60)
    
    async def _performance_tracker_task(self):
        """성능 추적 태스크"""
        while self.is_running:
            try:
                # 성능 메트릭 수집 및 업데이트
                await self._update_performance_metrics()
                
                # 5분마다 실행
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"성능 추적 태스크 오류: {e}")
                await asyncio.sleep(120)
    
    async def _health_checker_task(self):
        """헬스체크 태스크"""
        while self.is_running:
            try:
                # 각 모듈의 헬스체크
                for module_name in self.system_health:
                    health_status = await self._check_module_health(module_name)
                    self.system_health[module_name] = health_status
                
                # 1분마다 실행
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"헬스체크 태스크 오류: {e}")
                await asyncio.sleep(60)
    
    async def _stats_updater_task(self):
        """통계 업데이트 태스크"""
        while self.is_running:
            try:
                # 통계 데이터 수집 및 업데이트
                await self._update_statistics()
                
                # 10분마다 실행
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"통계 업데이트 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    # 헬퍼 메서드들
    def _calculate_uptime(self) -> int:
        """가동 시간 계산 (초)"""
        if self.stats['start_time']:
            return int((datetime.utcnow() - self.stats['start_time']).total_seconds())
        return 0
    
    def _format_uptime(self, seconds: int) -> str:
        """가동 시간 포맷팅"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    async def _send_system_notification(self, event_type: str, data: Dict[str, Any]):
        """시스템 알림 발송"""
        try:
            await self.websocket_manager.broadcast_to_channel(
                channel='system_automation',
                message={
                    'type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"시스템 알림 발송 실패: {e}")
    
    async def _send_process_notification(self, event_type: str, data: Dict[str, Any]):
        """프로세스 알림 발송"""
        try:
            await self.websocket_manager.broadcast_to_channel(
                channel='order_processing',
                message={
                    'type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"프로세스 알림 발송 실패: {e}")
    
    # 추가 헬퍼 메서드들 (실제 구현에서 완성 필요)
    async def _get_order_items(self, order_id: str) -> List:
        """주문 아이템 조회"""
        pass
    
    async def _check_system_health(self):
        """시스템 전반 상태 확인"""
        pass
    
    async def _check_module_health(self, module_name: str) -> bool:
        """모듈 헬스체크"""
        pass
    
    async def _update_performance_metrics(self):
        """성능 메트릭 업데이트"""
        pass
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        pass
    
    async def _update_statistics(self):
        """통계 업데이트"""
        pass
    
    async def _restart_module(self, module_name: str):
        """모듈 재시작"""
        pass
    
    async def _reconnect_database(self):
        """데이터베이스 재연결"""
        pass
    
    async def _handle_rate_limit(self, context: Dict[str, Any]):
        """API 사용량 제한 처리"""
        pass