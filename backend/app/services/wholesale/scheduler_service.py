"""
자동 수집 스케줄러 서비스
도매처 상품을 주기적으로 자동 수집하는 기능을 제공합니다.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.orm import Session

from app.models.wholesaler import (
    WholesalerAccount, 
    ScheduledCollection, 
    CollectionLog,
    CollectionStatus,
    ConnectionStatus
)
from app.services.database.database import get_db
from app.services.wholesalers.wholesaler_manager import WholesalerManager

logger = logging.getLogger(__name__)


class CollectionTask:
    """수집 작업 정보"""
    
    def __init__(self, wholesaler_account_id: int, collection_type: str, 
                 filters: Dict = None, max_products: int = 1000):
        self.wholesaler_account_id = wholesaler_account_id
        self.collection_type = collection_type
        self.filters = filters or {}
        self.max_products = max_products
        self.created_at = datetime.utcnow()


class SchedulerService:
    """스케줄러 메인 서비스"""
    
    def __init__(self):
        self.scheduler = None
        self.is_running = False
        self.active_jobs = {}
        self.job_stats = {}
        self.wholesaler_manager = None
        
        # 스케줄러 설정
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5분
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Seoul'
        )
    
    async def start(self):
        """스케줄러를 시작합니다."""
        try:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                self.wholesaler_manager = WholesalerManager()
                logger.info("스케줄러가 시작되었습니다.")
                
                # 기존 스케줄 복원
                await self.restore_scheduled_jobs()
                
        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {str(e)}")
            raise
    
    async def stop(self):
        """스케줄러를 중지합니다."""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("스케줄러가 중지되었습니다.")
        except Exception as e:
            logger.error(f"스케줄러 중지 실패: {str(e)}")
    
    async def restore_scheduled_jobs(self):
        """데이터베이스에서 활성 스케줄을 복원합니다."""
        try:
            db = next(get_db())
            active_schedules = db.query(ScheduledCollection).filter(
                ScheduledCollection.is_active == True
            ).all()
            
            for schedule in active_schedules:
                try:
                    await self.add_scheduled_job(
                        schedule_id=schedule.id,
                        wholesaler_account_id=schedule.wholesaler_account_id,
                        cron_expression=schedule.cron_expression,
                        collection_type=schedule.collection_type,
                        filters=schedule.filters,
                        max_products=schedule.max_products
                    )
                    logger.info(f"스케줄 복원됨: {schedule.schedule_name}")
                except Exception as e:
                    logger.error(f"스케줄 복원 실패 (ID: {schedule.id}): {str(e)}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"스케줄 복원 실패: {str(e)}")
    
    async def add_scheduled_job(self, schedule_id: int, wholesaler_account_id: int,
                              cron_expression: str, collection_type: str,
                              filters: Dict = None, max_products: int = 1000) -> bool:
        """새로운 스케줄 작업을 추가합니다."""
        try:
            job_id = f"wholesaler_collection_{schedule_id}"
            
            # 기존 작업이 있다면 제거
            if job_id in self.active_jobs:
                self.scheduler.remove_job(job_id)
            
            # 크론 트리거 생성
            trigger = CronTrigger.from_crontab(cron_expression, timezone='Asia/Seoul')
            
            # 작업 추가
            self.scheduler.add_job(
                func=self._execute_collection_job,
                trigger=trigger,
                id=job_id,
                args=[schedule_id, wholesaler_account_id, collection_type, filters, max_products],
                replace_existing=True
            )
            
            self.active_jobs[job_id] = {
                'schedule_id': schedule_id,
                'wholesaler_account_id': wholesaler_account_id,
                'collection_type': collection_type,
                'created_at': datetime.utcnow()
            }
            
            # 다음 실행 시간 계산 및 업데이트
            next_run = self.scheduler.get_job(job_id).next_run_time
            await self._update_schedule_next_run(schedule_id, next_run)
            
            logger.info(f"스케줄 작업 추가됨: {job_id} (다음 실행: {next_run})")
            return True
            
        except Exception as e:
            logger.error(f"스케줄 작업 추가 실패: {str(e)}")
            return False
    
    async def remove_scheduled_job(self, schedule_id: int) -> bool:
        """스케줄 작업을 제거합니다."""
        try:
            job_id = f"wholesaler_collection_{schedule_id}"
            
            if job_id in self.active_jobs:
                self.scheduler.remove_job(job_id)
                del self.active_jobs[job_id]
                logger.info(f"스케줄 작업 제거됨: {job_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"스케줄 작업 제거 실패: {str(e)}")
            return False
    
    async def pause_scheduled_job(self, schedule_id: int) -> bool:
        """스케줄 작업을 일시 중지합니다."""
        try:
            job_id = f"wholesaler_collection_{schedule_id}"
            self.scheduler.pause_job(job_id)
            logger.info(f"스케줄 작업 일시중지됨: {job_id}")
            return True
        except Exception as e:
            logger.error(f"스케줄 작업 일시중지 실패: {str(e)}")
            return False
    
    async def resume_scheduled_job(self, schedule_id: int) -> bool:
        """일시 중지된 스케줄 작업을 재개합니다."""
        try:
            job_id = f"wholesaler_collection_{schedule_id}"
            self.scheduler.resume_job(job_id)
            
            # 다음 실행 시간 업데이트
            next_run = self.scheduler.get_job(job_id).next_run_time
            await self._update_schedule_next_run(schedule_id, next_run)
            
            logger.info(f"스케줄 작업 재개됨: {job_id}")
            return True
        except Exception as e:
            logger.error(f"스케줄 작업 재개 실패: {str(e)}")
            return False
    
    async def trigger_manual_collection(self, wholesaler_account_id: int, 
                                       collection_type: str = "manual",
                                       filters: Dict = None, 
                                       max_products: int = 1000) -> Dict:
        """수동으로 수집을 실행합니다."""
        try:
            task = CollectionTask(
                wholesaler_account_id, 
                collection_type, 
                filters, 
                max_products
            )
            
            result = await self._execute_collection_task(task)
            return result
            
        except Exception as e:
            logger.error(f"수동 수집 실행 실패: {str(e)}")
            return {
                'success': False,
                'message': f"수집 실행 실패: {str(e)}"
            }
    
    async def _execute_collection_job(self, schedule_id: int, wholesaler_account_id: int,
                                     collection_type: str, filters: Dict, max_products: int):
        """스케줄된 수집 작업을 실행합니다."""
        try:
            logger.info(f"스케줄 수집 시작: Schedule ID {schedule_id}")
            
            # 스케줄 정보 업데이트
            await self._update_schedule_run_start(schedule_id)
            
            task = CollectionTask(wholesaler_account_id, collection_type, filters, max_products)
            result = await self._execute_collection_task(task)
            
            # 스케줄 통계 업데이트
            await self._update_schedule_run_result(schedule_id, result['success'])
            
            # 다음 실행 시간 업데이트
            job_id = f"wholesaler_collection_{schedule_id}"
            if job_id in self.active_jobs:
                next_run = self.scheduler.get_job(job_id).next_run_time
                await self._update_schedule_next_run(schedule_id, next_run)
            
            logger.info(f"스케줄 수집 완료: Schedule ID {schedule_id}, 성공: {result['success']}")
            
        except Exception as e:
            logger.error(f"스케줄 수집 실행 실패 (Schedule ID: {schedule_id}): {str(e)}")
            await self._update_schedule_run_result(schedule_id, False, str(e))
    
    async def _execute_collection_task(self, task: CollectionTask) -> Dict:
        """개별 수집 작업을 실행합니다."""
        db = None
        collection_log = None
        
        try:
            db = next(get_db())
            
            # 도매처 계정 조회
            wholesaler_account = db.query(WholesalerAccount).filter(
                WholesalerAccount.id == task.wholesaler_account_id
            ).first()
            
            if not wholesaler_account:
                return {
                    'success': False,
                    'message': '도매처 계정을 찾을 수 없습니다.'
                }
            
            if not wholesaler_account.is_active:
                return {
                    'success': False,
                    'message': '비활성화된 도매처 계정입니다.'
                }
            
            # 수집 로그 생성
            collection_log = CollectionLog(
                wholesaler_account_id=task.wholesaler_account_id,
                collection_type=task.collection_type,
                status=CollectionStatus.RUNNING,
                filters=task.filters,
                started_at=datetime.utcnow()
            )
            
            db.add(collection_log)
            db.commit()
            db.refresh(collection_log)
            
            # 실제 수집 실행
            if not self.wholesaler_manager:
                self.wholesaler_manager = WholesalerManager()
            
            collection_result = await self.wholesaler_manager.collect_products(
                wholesaler_account=wholesaler_account,
                collection_type=task.collection_type,
                filters=task.filters,
                max_products=task.max_products,
                db=db
            )
            
            # 수집 로그 업데이트
            collection_log.status = CollectionStatus.COMPLETED if collection_result['success'] else CollectionStatus.FAILED
            collection_log.completed_at = datetime.utcnow()
            collection_log.duration_seconds = int((collection_log.completed_at - collection_log.started_at).total_seconds())
            
            if collection_result['success']:
                stats = collection_result.get('stats', {})
                collection_log.total_products_found = stats.get('total_found', 0)
                collection_log.products_collected = stats.get('collected', 0)
                collection_log.products_updated = stats.get('updated', 0)
                collection_log.products_failed = stats.get('failed', 0)
                collection_log.collection_summary = stats
            else:
                collection_log.error_message = collection_result.get('message', 'Unknown error')
                collection_log.error_details = collection_result.get('details', {})
            
            db.commit()
            
            return {
                'success': collection_result['success'],
                'message': collection_result.get('message', ''),
                'collection_log_id': collection_log.id,
                'stats': collection_result.get('stats', {})
            }
            
        except Exception as e:
            logger.error(f"수집 작업 실행 실패: {str(e)}")
            
            if collection_log and db:
                collection_log.status = CollectionStatus.FAILED
                collection_log.error_message = str(e)
                collection_log.completed_at = datetime.utcnow()
                if collection_log.started_at:
                    collection_log.duration_seconds = int((collection_log.completed_at - collection_log.started_at).total_seconds())
                db.commit()
            
            return {
                'success': False,
                'message': f"수집 실행 실패: {str(e)}",
                'collection_log_id': collection_log.id if collection_log else None
            }
        
        finally:
            if db:
                db.close()
    
    async def _update_schedule_run_start(self, schedule_id: int):
        """스케줄 실행 시작 정보를 업데이트합니다."""
        try:
            db = next(get_db())
            schedule = db.query(ScheduledCollection).filter(
                ScheduledCollection.id == schedule_id
            ).first()
            
            if schedule:
                schedule.last_run_at = datetime.utcnow()
                schedule.total_runs += 1
                db.commit()
            
            db.close()
        except Exception as e:
            logger.error(f"스케줄 실행 시작 정보 업데이트 실패: {str(e)}")
    
    async def _update_schedule_run_result(self, schedule_id: int, success: bool, error_message: str = None):
        """스케줄 실행 결과를 업데이트합니다."""
        try:
            db = next(get_db())
            schedule = db.query(ScheduledCollection).filter(
                ScheduledCollection.id == schedule_id
            ).first()
            
            if schedule:
                if success:
                    schedule.successful_runs += 1
                    schedule.last_error = None
                else:
                    schedule.failed_runs += 1
                    schedule.last_error = error_message
                
                db.commit()
            
            db.close()
        except Exception as e:
            logger.error(f"스케줄 실행 결과 업데이트 실패: {str(e)}")
    
    async def _update_schedule_next_run(self, schedule_id: int, next_run_time: datetime):
        """스케줄 다음 실행 시간을 업데이트합니다."""
        try:
            db = next(get_db())
            schedule = db.query(ScheduledCollection).filter(
                ScheduledCollection.id == schedule_id
            ).first()
            
            if schedule:
                schedule.next_run_at = next_run_time
                db.commit()
            
            db.close()
        except Exception as e:
            logger.error(f"스케줄 다음 실행 시간 업데이트 실패: {str(e)}")
    
    def get_scheduler_status(self) -> Dict:
        """스케줄러 상태 정보를 반환합니다."""
        return {
            'is_running': self.is_running,
            'active_jobs_count': len(self.active_jobs),
            'active_jobs': list(self.active_jobs.keys()),
            'scheduler_state': str(self.scheduler.state) if self.scheduler else 'NOT_INITIALIZED'
        }
    
    def get_job_details(self) -> List[Dict]:
        """활성 작업 상세 정보를 반환합니다."""
        job_details = []
        
        for job_id, job_info in self.active_jobs.items():
            try:
                job = self.scheduler.get_job(job_id)
                if job:
                    job_details.append({
                        'job_id': job_id,
                        'schedule_id': job_info['schedule_id'],
                        'wholesaler_account_id': job_info['wholesaler_account_id'],
                        'collection_type': job_info['collection_type'],
                        'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                        'trigger': str(job.trigger),
                        'created_at': job_info['created_at'].isoformat(),
                        'is_paused': job.id in [j.id for j in self.scheduler.get_jobs() if hasattr(j, 'next_run_time') and j.next_run_time is None]
                    })
            except Exception as e:
                logger.error(f"작업 상세 정보 조회 실패 ({job_id}): {str(e)}")
        
        return job_details


class SchedulerManager:
    """스케줄러 관리자 (싱글톤)"""
    
    _instance = None
    _scheduler_service = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_scheduler_service(cls) -> SchedulerService:
        """스케줄러 서비스 인스턴스를 반환합니다."""
        if cls._scheduler_service is None:
            cls._scheduler_service = SchedulerService()
            await cls._scheduler_service.start()
        return cls._scheduler_service
    
    @classmethod
    async def shutdown(cls):
        """스케줄러를 종료합니다."""
        if cls._scheduler_service:
            await cls._scheduler_service.stop()
            cls._scheduler_service = None


# 유틸리티 함수들
def create_cron_expression(interval_type: str, interval_value: int, 
                          time_hour: int = 0, time_minute: int = 0) -> str:
    """간편한 크론 표현식 생성"""
    if interval_type == 'hourly':
        return f"{time_minute} * * * *"
    elif interval_type == 'daily':
        return f"{time_minute} {time_hour} * * *"
    elif interval_type == 'weekly':
        return f"{time_minute} {time_hour} * * {interval_value}"  # interval_value는 요일 (0=일요일)
    elif interval_type == 'monthly':
        return f"{time_minute} {time_hour} {interval_value} * *"  # interval_value는 일
    else:
        raise ValueError(f"지원하지 않는 간격 유형: {interval_type}")


def validate_cron_expression(cron_expression: str) -> bool:
    """크론 표현식 유효성 검증"""
    try:
        CronTrigger.from_crontab(cron_expression)
        return True
    except Exception:
        return False


def get_next_run_times(cron_expression: str, count: int = 5) -> List[datetime]:
    """크론 표현식의 다음 실행 시간들을 반환"""
    try:
        trigger = CronTrigger.from_crontab(cron_expression, timezone='Asia/Seoul')
        times = []
        current_time = datetime.now()
        
        for i in range(count):
            next_time = trigger.get_next_fire_time(None, current_time)
            if next_time:
                times.append(next_time)
                current_time = next_time + timedelta(seconds=1)
            else:
                break
        
        return times
    except Exception:
        return []