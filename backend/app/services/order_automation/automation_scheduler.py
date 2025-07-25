"""
Order automation scheduler
주문 처리 자동화 스케줄러
"""
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from .order_automation_manager import OrderAutomationManager
from app.services.realtime.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """주문 처리 자동화 스케줄러"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.scheduler = AsyncIOScheduler()
        self.automation_manager = OrderAutomationManager(db_session)
        self.websocket_manager = WebSocketManager()
        
        # 스케줄러 상태
        self.is_running = False
        self.scheduled_jobs = {}
        
        # 기본 스케줄 설정
        self.default_schedules = {
            # 정기 작업들
            'daily_reports': {
                'trigger': 'cron',
                'hour': 2,
                'minute': 0,
                'description': '일일 보고서 생성'
            },
            'inventory_sync': {
                'trigger': 'interval',
                'hours': 4,
                'description': '재고 동기화'
            },
            'settlement_generation': {
                'trigger': 'cron',
                'hour': 1,
                'minute': 0,
                'description': '정산 데이터 생성'
            },
            'exception_cleanup': {
                'trigger': 'cron',
                'hour': 3,
                'minute': 0,
                'description': '해결된 예외 케이스 정리'
            },
            'performance_optimization': {
                'trigger': 'cron',
                'hour': 5,
                'minute': 0,
                'description': '성능 최적화 작업'
            },
            
            # 실시간 모니터링
            'order_monitoring': {
                'trigger': 'interval',
                'seconds': 30,
                'description': '주문 모니터링'
            },
            'tracking_updates': {
                'trigger': 'interval',
                'minutes': 15,
                'description': '배송 추적 업데이트'
            },
            'auto_ordering': {
                'trigger': 'interval',
                'minutes': 5,
                'description': '자동 발주 처리'
            },
            
            # 주간/월간 작업
            'weekly_analysis': {
                'trigger': 'cron',
                'day_of_week': 0,  # 월요일
                'hour': 6,
                'minute': 0,
                'description': '주간 분석 보고서'
            },
            'monthly_settlement': {
                'trigger': 'cron',
                'day': 1,
                'hour': 8,
                'minute': 0,
                'description': '월간 정산'
            }
        }
    
    async def start_scheduler(self):
        """스케줄러 시작"""
        try:
            logger.info("주문 처리 자동화 스케줄러 시작")
            
            # 기본 스케줄 작업들 등록
            await self._register_default_jobs()
            
            # 동적 스케줄 작업들 등록
            await self._register_dynamic_jobs()
            
            # 스케줄러 시작
            self.scheduler.start()
            self.is_running = True
            
            # 시작 알림
            await self._send_scheduler_notification('scheduler_started', {
                'total_jobs': len(self.scheduled_jobs),
                'default_jobs': len(self.default_schedules),
                'started_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"스케줄러 시작 완료 - 총 {len(self.scheduled_jobs)}개 작업 등록됨")
            
        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {e}")
            raise
    
    async def stop_scheduler(self):
        """스케줄러 중지"""
        try:
            logger.info("주문 처리 자동화 스케줄러 중지 시작")
            
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            self.is_running = False
            self.scheduled_jobs.clear()
            
            # 중지 알림
            await self._send_scheduler_notification('scheduler_stopped', {
                'stopped_at': datetime.utcnow().isoformat()
            })
            
            logger.info("스케줄러 중지 완료")
            
        except Exception as e:
            logger.error(f"스케줄러 중지 실패: {e}")
    
    async def add_job(self, job_id: str, func: Callable, trigger_config: Dict[str, Any], 
                     description: str = None, **kwargs) -> bool:
        """작업 추가"""
        try:
            # 트리거 생성
            trigger = self._create_trigger(trigger_config)
            
            # 작업 추가
            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                name=description or job_id,
                **kwargs
            )
            
            self.scheduled_jobs[job_id] = {
                'job': job,
                'description': description,
                'trigger_config': trigger_config,
                'added_at': datetime.utcnow(),
                'last_run': None,
                'run_count': 0
            }
            
            logger.info(f"작업 {job_id} 추가됨: {description}")
            
            # 작업 추가 알림
            await self._send_scheduler_notification('job_added', {
                'job_id': job_id,
                'description': description,
                'trigger_config': trigger_config
            })
            
            return True
            
        except Exception as e:
            logger.error(f"작업 {job_id} 추가 실패: {e}")
            return False
    
    async def remove_job(self, job_id: str) -> bool:
        """작업 제거"""
        try:
            if job_id in self.scheduled_jobs:
                self.scheduler.remove_job(job_id)
                del self.scheduled_jobs[job_id]
                
                logger.info(f"작업 {job_id} 제거됨")
                
                # 작업 제거 알림
                await self._send_scheduler_notification('job_removed', {
                    'job_id': job_id
                })
                
                return True
            else:
                logger.warning(f"작업 {job_id}을 찾을 수 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"작업 {job_id} 제거 실패: {e}")
            return False
    
    async def pause_job(self, job_id: str) -> bool:
        """작업 일시 중지"""
        try:
            self.scheduler.pause_job(job_id)
            
            if job_id in self.scheduled_jobs:
                self.scheduled_jobs[job_id]['paused'] = True
            
            logger.info(f"작업 {job_id} 일시 중지됨")
            return True
            
        except Exception as e:
            logger.error(f"작업 {job_id} 일시 중지 실패: {e}")
            return False
    
    async def resume_job(self, job_id: str) -> bool:
        """작업 재개"""
        try:
            self.scheduler.resume_job(job_id)
            
            if job_id in self.scheduled_jobs:
                self.scheduled_jobs[job_id]['paused'] = False
            
            logger.info(f"작업 {job_id} 재개됨")
            return True
            
        except Exception as e:
            logger.error(f"작업 {job_id} 재개 실패: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """작업 상태 조회"""
        try:
            if job_id not in self.scheduled_jobs:
                return {
                    'exists': False,
                    'error': '작업을 찾을 수 없습니다'
                }
            
            job_info = self.scheduled_jobs[job_id]
            scheduler_job = self.scheduler.get_job(job_id)
            
            return {
                'exists': True,
                'job_id': job_id,
                'description': job_info['description'],
                'trigger_config': job_info['trigger_config'],
                'added_at': job_info['added_at'].isoformat(),
                'last_run': job_info['last_run'].isoformat() if job_info['last_run'] else None,
                'run_count': job_info['run_count'],
                'next_run': scheduler_job.next_run_time.isoformat() if scheduler_job.next_run_time else None,
                'paused': job_info.get('paused', False)
            }
            
        except Exception as e:
            logger.error(f"작업 {job_id} 상태 조회 실패: {e}")
            return {
                'exists': False,
                'error': str(e)
            }
    
    async def get_all_jobs_status(self) -> Dict[str, Any]:
        """모든 작업 상태 조회"""
        try:
            jobs_status = {}
            
            for job_id in self.scheduled_jobs:
                jobs_status[job_id] = await self.get_job_status(job_id)
            
            return {
                'scheduler_running': self.is_running,
                'total_jobs': len(self.scheduled_jobs),
                'jobs': jobs_status,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"전체 작업 상태 조회 실패: {e}")
            return {
                'scheduler_running': False,
                'error': str(e)
            }
    
    async def _register_default_jobs(self):
        """기본 스케줄 작업들 등록"""
        try:
            for job_id, config in self.default_schedules.items():
                # 작업 함수 매핑
                job_func = self._get_job_function(job_id)
                
                if job_func:
                    await self.add_job(
                        job_id=job_id,
                        func=job_func,
                        trigger_config=config,
                        description=config['description']
                    )
                else:
                    logger.warning(f"작업 {job_id}에 대한 함수를 찾을 수 없습니다")
                    
        except Exception as e:
            logger.error(f"기본 작업 등록 실패: {e}")
            raise
    
    async def _register_dynamic_jobs(self):
        """동적 스케줄 작업들 등록"""
        try:
            # 데이터베이스에서 사용자 정의 스케줄 조회
            custom_schedules = await self._get_custom_schedules()
            
            for schedule in custom_schedules:
                await self.add_job(
                    job_id=schedule['job_id'],
                    func=self._get_job_function(schedule['job_type']),
                    trigger_config=schedule['trigger_config'],
                    description=schedule['description']
                )
                
        except Exception as e:
            logger.error(f"동적 작업 등록 실패: {e}")
    
    def _create_trigger(self, config: Dict[str, Any]):
        """트리거 생성"""
        trigger_type = config.pop('trigger', 'interval')
        
        if trigger_type == 'cron':
            return CronTrigger(**config)
        elif trigger_type == 'interval':
            return IntervalTrigger(**config)
        elif trigger_type == 'date':
            return DateTrigger(**config)
        else:
            raise ValueError(f"지원하지 않는 트리거 유형: {trigger_type}")
    
    def _get_job_function(self, job_id: str) -> Optional[Callable]:
        """작업 ID에 해당하는 함수 반환"""
        job_functions = {
            # 정기 작업들
            'daily_reports': self._job_generate_daily_reports,
            'inventory_sync': self._job_sync_inventory,
            'settlement_generation': self._job_generate_settlements,
            'exception_cleanup': self._job_cleanup_exceptions,
            'performance_optimization': self._job_optimize_performance,
            
            # 실시간 모니터링
            'order_monitoring': self._job_monitor_orders,
            'tracking_updates': self._job_update_tracking,
            'auto_ordering': self._job_process_auto_orders,
            
            # 주간/월간 작업
            'weekly_analysis': self._job_weekly_analysis,
            'monthly_settlement': self._job_monthly_settlement
        }
        
        return job_functions.get(job_id)
    
    # 스케줄 작업 함수들
    async def _job_generate_daily_reports(self):
        """일일 보고서 생성 작업"""
        try:
            logger.info("일일 보고서 생성 작업 시작")
            
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, time.min)
            end_date = datetime.combine(yesterday, time.max)
            
            # 일일 수익 보고서 생성
            report = await self.automation_manager.auto_settlement.generate_profit_report(
                start_date, end_date
            )
            
            # 보고서 저장 및 알림
            await self._save_and_notify_report('daily', report)
            
            await self._update_job_run_info('daily_reports')
            logger.info("일일 보고서 생성 작업 완료")
            
        except Exception as e:
            logger.error(f"일일 보고서 생성 실패: {e}")
            await self._handle_job_error('daily_reports', e)
    
    async def _job_sync_inventory(self):
        """재고 동기화 작업"""
        try:
            logger.info("재고 동기화 작업 시작")
            
            result = await self.automation_manager.exception_handler.sync_inventory()
            
            # 동기화 결과 알림
            await self._send_scheduler_notification('inventory_synced', {
                'successful_syncs': result.get('successful_syncs', 0),
                'total_updated_items': result.get('total_updated_items', 0)
            })
            
            await self._update_job_run_info('inventory_sync')
            logger.info("재고 동기화 작업 완료")
            
        except Exception as e:
            logger.error(f"재고 동기화 실패: {e}")
            await self._handle_job_error('inventory_sync', e)
    
    async def _job_generate_settlements(self):
        """정산 생성 작업"""
        try:
            logger.info("정산 생성 작업 시작")
            
            # 정산이 필요한 주문들 조회 및 처리
            pending_orders = await self._get_orders_needing_settlement()
            
            settlement_results = []
            for order in pending_orders:
                try:
                    result = await self.automation_manager.auto_settlement.generate_settlement(
                        str(order.id)
                    )
                    settlement_results.append(result)
                except Exception as e:
                    logger.error(f"주문 {order.id} 정산 생성 실패: {e}")
                    continue
            
            # 정산 결과 알림
            successful_settlements = sum(1 for r in settlement_results if r.get('success'))
            await self._send_scheduler_notification('settlements_generated', {
                'total_orders': len(pending_orders),
                'successful_settlements': successful_settlements,
                'failed_settlements': len(settlement_results) - successful_settlements
            })
            
            await self._update_job_run_info('settlement_generation')
            logger.info(f"정산 생성 작업 완료 - {successful_settlements}/{len(pending_orders)} 성공")
            
        except Exception as e:
            logger.error(f"정산 생성 실패: {e}")
            await self._handle_job_error('settlement_generation', e)
    
    async def _job_cleanup_exceptions(self):
        """해결된 예외 케이스 정리 작업"""
        try:
            logger.info("예외 케이스 정리 작업 시작")
            
            # 해결된 오래된 예외 케이스들 정리
            cleanup_result = await self._cleanup_resolved_exceptions()
            
            await self._send_scheduler_notification('exceptions_cleaned', cleanup_result)
            
            await self._update_job_run_info('exception_cleanup')
            logger.info("예외 케이스 정리 작업 완료")
            
        except Exception as e:
            logger.error(f"예외 케이스 정리 실패: {e}")
            await self._handle_job_error('exception_cleanup', e)
    
    async def _job_optimize_performance(self):
        """성능 최적화 작업"""
        try:
            logger.info("성능 최적화 작업 시작")
            
            # 성능 분석 및 최적화
            optimization_result = await self._perform_system_optimization()
            
            await self._send_scheduler_notification('performance_optimized', optimization_result)
            
            await self._update_job_run_info('performance_optimization')
            logger.info("성능 최적화 작업 완료")
            
        except Exception as e:
            logger.error(f"성능 최적화 실패: {e}")
            await self._handle_job_error('performance_optimization', e)
    
    async def _job_monitor_orders(self):
        """주문 모니터링 작업"""
        try:
            # 새로운 주문 확인
            await self._check_new_orders()
            await self._update_job_run_info('order_monitoring')
            
        except Exception as e:
            logger.error(f"주문 모니터링 실패: {e}")
            await self._handle_job_error('order_monitoring', e)
    
    async def _job_update_tracking(self):
        """배송 추적 업데이트 작업"""
        try:
            # 추적 정보 업데이트
            await self._update_all_tracking_info()
            await self._update_job_run_info('tracking_updates')
            
        except Exception as e:
            logger.error(f"배송 추적 업데이트 실패: {e}")
            await self._handle_job_error('tracking_updates', e)
    
    async def _job_process_auto_orders(self):
        """자동 발주 처리 작업"""
        try:
            # 자동 발주 대상 확인 및 처리
            await self._process_pending_auto_orders()
            await self._update_job_run_info('auto_ordering')
            
        except Exception as e:
            logger.error(f"자동 발주 처리 실패: {e}")
            await self._handle_job_error('auto_ordering', e)
    
    async def _job_weekly_analysis(self):
        """주간 분석 작업"""
        try:
            logger.info("주간 분석 작업 시작")
            
            # 주간 분석 보고서 생성
            weekly_report = await self._generate_weekly_analysis()
            
            await self._save_and_notify_report('weekly', weekly_report)
            await self._update_job_run_info('weekly_analysis')
            
            logger.info("주간 분석 작업 완료")
            
        except Exception as e:
            logger.error(f"주간 분석 실패: {e}")
            await self._handle_job_error('weekly_analysis', e)
    
    async def _job_monthly_settlement(self):
        """월간 정산 작업"""
        try:
            logger.info("월간 정산 작업 시작")
            
            # 월간 정산 보고서 생성
            monthly_report = await self._generate_monthly_settlement()
            
            await self._save_and_notify_report('monthly', monthly_report)
            await self._update_job_run_info('monthly_settlement')
            
            logger.info("월간 정산 작업 완료")
            
        except Exception as e:
            logger.error(f"월간 정산 실패: {e}")
            await self._handle_job_error('monthly_settlement', e)
    
    # 헬퍼 메서드들
    async def _update_job_run_info(self, job_id: str):
        """작업 실행 정보 업데이트"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id]['last_run'] = datetime.utcnow()
            self.scheduled_jobs[job_id]['run_count'] += 1
    
    async def _handle_job_error(self, job_id: str, error: Exception):
        """작업 오류 처리"""
        await self._send_scheduler_notification('job_failed', {
            'job_id': job_id,
            'error': str(error),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _send_scheduler_notification(self, event_type: str, data: Dict[str, Any]):
        """스케줄러 알림 발송"""
        try:
            await self.websocket_manager.broadcast_to_channel(
                channel='automation_scheduler',
                message={
                    'type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"스케줄러 알림 발송 실패: {e}")
    
    # 추가 헬퍼 메서드들 (실제 구현에서 완성 필요)
    async def _get_custom_schedules(self) -> List[Dict[str, Any]]:
        """사용자 정의 스케줄 조회"""
        pass
    
    async def _save_and_notify_report(self, report_type: str, report_data: Dict[str, Any]):
        """보고서 저장 및 알림"""
        pass
    
    async def _get_orders_needing_settlement(self) -> List:
        """정산 필요 주문 조회"""
        pass
    
    async def _cleanup_resolved_exceptions(self) -> Dict[str, Any]:
        """해결된 예외 케이스 정리"""
        pass
    
    async def _perform_system_optimization(self) -> Dict[str, Any]:
        """시스템 성능 최적화"""
        pass
    
    async def _check_new_orders(self):
        """새로운 주문 확인"""
        pass
    
    async def _update_all_tracking_info(self):
        """모든 추적 정보 업데이트"""
        pass
    
    async def _process_pending_auto_orders(self):
        """대기 중인 자동 발주 처리"""
        pass
    
    async def _generate_weekly_analysis(self) -> Dict[str, Any]:
        """주간 분석 보고서 생성"""
        pass
    
    async def _generate_monthly_settlement(self) -> Dict[str, Any]:
        """월간 정산 보고서 생성"""
        pass