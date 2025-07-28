"""
배치 스케줄러 코어 시스템
- 작업 스케줄링
- 작업 실행 관리
- 상태 모니터링
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text
from database.models_v2 import Base
from database.connection import engine, SessionLocal
from utils.logger import app_logger


class JobStatus(Enum):
    """작업 상태"""
    PENDING = "pending"      # 대기 중
    RUNNING = "running"      # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"        # 실패
    CANCELLED = "cancelled"  # 취소됨


class JobType(Enum):
    """작업 유형"""
    COLLECTION = "collection"           # 상품 수집
    IMAGE_PROCESSING = "image_processing"  # 이미지 처리
    DATA_SYNC = "data_sync"            # 데이터 동기화
    CLEANUP = "cleanup"                # 정리 작업
    ANALYSIS = "analysis"              # 분석 작업
    REPORT = "report"                  # 리포트 생성


# 스케줄된 작업 테이블
class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    job_type = Column(String(50), nullable=False)
    cron_expression = Column(String(100))  # 크론 표현식
    function_name = Column(String(200), nullable=False)
    parameters = Column(JSON)
    status = Column(String(20), default=JobStatus.PENDING.value)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    last_result = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=3600)  # 1시간
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# 작업 실행 히스토리
class JobExecution(Base):
    __tablename__ = "job_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    result = Column(JSON)
    error_message = Column(Text)
    log_output = Column(Text)


# 테이블 생성
ScheduledJob.__table__.create(engine, checkfirst=True)
JobExecution.__table__.create(engine, checkfirst=True)


@dataclass
class CronSchedule:
    """크론 스케줄 설정"""
    minute: str = "*"    # 0-59
    hour: str = "*"      # 0-23
    day: str = "*"       # 1-31
    month: str = "*"     # 1-12
    weekday: str = "*"   # 0-6 (0=Sunday)
    
    def to_expression(self) -> str:
        return f"{self.minute} {self.hour} {self.day} {self.month} {self.weekday}"
    
    @classmethod
    def daily(cls, hour: int = 2, minute: int = 0) -> 'CronSchedule':
        """매일 실행"""
        return cls(minute=str(minute), hour=str(hour))
    
    @classmethod
    def weekly(cls, weekday: int = 0, hour: int = 2, minute: int = 0) -> 'CronSchedule':
        """주간 실행"""
        return cls(minute=str(minute), hour=str(hour), weekday=str(weekday))
    
    @classmethod
    def hourly(cls, minute: int = 0) -> 'CronSchedule':
        """시간마다 실행"""
        return cls(minute=str(minute))


class BatchScheduler:
    """배치 스케줄러"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.running_jobs: Dict[int, asyncio.Task] = {}
        self.job_functions: Dict[str, Callable] = {}
        self.is_running = False
        
        # 기본 작업 함수 등록
        self._register_default_jobs()
    
    def _register_default_jobs(self):
        """기본 작업 함수 등록"""
        from services.scheduler.job_functions import (
            collect_wholesale_products,
            collect_bestsellers,
            process_images,
            cleanup_old_data,
            generate_daily_report,
            sync_marketplace_data,
            analyze_trends
        )
        
        self.job_functions.update({
            'collect_wholesale_products': collect_wholesale_products,
            'collect_bestsellers': collect_bestsellers,
            'process_images': process_images,
            'cleanup_old_data': cleanup_old_data,
            'generate_daily_report': generate_daily_report,
            'sync_marketplace_data': sync_marketplace_data,
            'analyze_trends': analyze_trends,
        })
    
    def register_job_function(self, name: str, function: Callable):
        """작업 함수 등록"""
        self.job_functions[name] = function
        app_logger.info(f"작업 함수 등록: {name}")
    
    def create_job(self, 
                   name: str,
                   job_type: JobType,
                   function_name: str,
                   schedule: CronSchedule,
                   parameters: Dict = None,
                   max_retries: int = 3,
                   timeout_seconds: int = 3600) -> int:
        """새 작업 생성"""
        try:
            if function_name not in self.job_functions:
                raise ValueError(f"등록되지 않은 함수: {function_name}")
            
            # 다음 실행 시간 계산
            next_run = self._calculate_next_run(schedule)
            
            job = ScheduledJob(
                name=name,
                job_type=job_type.value,
                cron_expression=schedule.to_expression(),
                function_name=function_name,
                parameters=parameters or {},
                next_run_at=next_run,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds
            )
            
            self.db.add(job)
            self.db.commit()
            
            app_logger.info(f"작업 생성: {name} (다음 실행: {next_run})")
            return job.id
            
        except Exception as e:
            app_logger.error(f"작업 생성 오류: {e}")
            self.db.rollback()
            raise
    
    def _calculate_next_run(self, schedule: CronSchedule) -> datetime:
        """다음 실행 시간 계산 (간단한 구현)"""
        # 실제로는 croniter 라이브러리 사용 권장
        now = datetime.now()
        
        # 매일 실행인 경우
        if schedule.hour != "*" and schedule.minute != "*":
            next_run = now.replace(
                hour=int(schedule.hour),
                minute=int(schedule.minute),
                second=0,
                microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        # 시간마다 실행인 경우
        if schedule.minute != "*":
            next_run = now.replace(
                minute=int(schedule.minute),
                second=0,
                microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run
        
        # 기본값: 1시간 후
        return now + timedelta(hours=1)
    
    async def start(self):
        """스케줄러 시작"""
        if self.is_running:
            app_logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        self.is_running = True
        app_logger.info("배치 스케줄러 시작")
        
        try:
            while self.is_running:
                await self._check_and_run_jobs()
                await asyncio.sleep(60)  # 1분마다 확인
                
        except Exception as e:
            app_logger.error(f"스케줄러 실행 오류: {e}")
        finally:
            self.is_running = False
    
    def stop(self):
        """스케줄러 중지"""
        self.is_running = False
        
        # 실행 중인 작업 취소
        for job_id, task in self.running_jobs.items():
            if not task.done():
                task.cancel()
                app_logger.info(f"작업 취소: {job_id}")
        
        app_logger.info("배치 스케줄러 중지")
    
    async def _check_and_run_jobs(self):
        """실행할 작업 확인 및 실행"""
        try:
            # 실행할 작업 조회
            now = datetime.now()
            jobs = self.db.query(ScheduledJob).filter(
                ScheduledJob.is_active == True,
                ScheduledJob.next_run_at <= now,
                ScheduledJob.status.in_([JobStatus.PENDING.value, JobStatus.FAILED.value])
            ).all()
            
            for job in jobs:
                if job.id not in self.running_jobs:
                    await self._execute_job(job)
            
            # 완료된 작업 정리
            completed_jobs = [
                job_id for job_id, task in self.running_jobs.items()
                if task.done()
            ]
            
            for job_id in completed_jobs:
                del self.running_jobs[job_id]
                
        except Exception as e:
            app_logger.error(f"작업 확인 오류: {e}")
    
    async def _execute_job(self, job: ScheduledJob):
        """작업 실행"""
        if job.function_name not in self.job_functions:
            app_logger.error(f"함수를 찾을 수 없음: {job.function_name}")
            return
        
        # 작업 상태 업데이트
        job.status = JobStatus.RUNNING.value
        job.last_run_at = datetime.now()
        self.db.commit()
        
        # 실행 기록 생성
        execution = JobExecution(
            job_id=job.id,
            status=JobStatus.RUNNING.value,
            started_at=datetime.now()
        )
        self.db.add(execution)
        self.db.commit()
        
        app_logger.info(f"작업 실행 시작: {job.name}")
        
        # 비동기 실행
        task = asyncio.create_task(
            self._run_job_function(job, execution)
        )
        self.running_jobs[job.id] = task
    
    async def _run_job_function(self, job: ScheduledJob, execution: JobExecution):
        """작업 함수 실행"""
        try:
            # 타임아웃 설정
            result = await asyncio.wait_for(
                self._call_job_function(job),
                timeout=job.timeout_seconds
            )
            
            # 성공 처리
            job.status = JobStatus.COMPLETED.value
            job.retry_count = 0
            job.last_result = result
            job.error_message = None
            job.next_run_at = self._calculate_next_run(
                self._parse_cron_expression(job.cron_expression)
            )
            
            execution.status = JobStatus.COMPLETED.value
            execution.completed_at = datetime.now()
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
            execution.result = result
            
            app_logger.info(f"작업 완료: {job.name}")
            
        except asyncio.TimeoutError:
            error_msg = f"작업 타임아웃: {job.timeout_seconds}초"
            await self._handle_job_error(job, execution, error_msg)
            
        except Exception as e:
            error_msg = f"작업 실행 오류: {str(e)}\n{traceback.format_exc()}"
            await self._handle_job_error(job, execution, error_msg)
        
        finally:
            self.db.commit()
    
    async def _call_job_function(self, job: ScheduledJob) -> Any:
        """작업 함수 호출"""
        function = self.job_functions[job.function_name]
        parameters = job.parameters or {}
        
        # 함수가 비동기인지 확인
        if asyncio.iscoroutinefunction(function):
            return await function(**parameters)
        else:
            # 동기 함수는 별도 스레드에서 실행
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: function(**parameters))
    
    async def _handle_job_error(self, job: ScheduledJob, execution: JobExecution, error_msg: str):
        """작업 오류 처리"""
        job.retry_count += 1
        job.error_message = error_msg
        
        if job.retry_count >= job.max_retries:
            job.status = JobStatus.FAILED.value
            app_logger.error(f"작업 최종 실패: {job.name} (재시도 {job.retry_count}회)")
        else:
            job.status = JobStatus.PENDING.value
            # 재시도를 위해 다음 실행 시간을 5분 후로 설정
            job.next_run_at = datetime.now() + timedelta(minutes=5)
            app_logger.warning(f"작업 재시도 예정: {job.name} (재시도 {job.retry_count}/{job.max_retries})")
        
        execution.status = JobStatus.FAILED.value
        execution.completed_at = datetime.now()
        execution.duration_seconds = int(
            (execution.completed_at - execution.started_at).total_seconds()
        )
        execution.error_message = error_msg
    
    def _parse_cron_expression(self, expression: str) -> CronSchedule:
        """크론 표현식 파싱"""
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError("잘못된 크론 표현식")
        
        return CronSchedule(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            weekday=parts[4]
        )
    
    def get_jobs(self, status: JobStatus = None) -> List[Dict]:
        """작업 목록 조회"""
        query = self.db.query(ScheduledJob)
        
        if status:
            query = query.filter(ScheduledJob.status == status.value)
        
        jobs = query.order_by(ScheduledJob.created_at.desc()).all()
        
        return [
            {
                'id': job.id,
                'name': job.name,
                'job_type': job.job_type,
                'status': job.status,
                'last_run_at': job.last_run_at.isoformat() if job.last_run_at else None,
                'next_run_at': job.next_run_at.isoformat() if job.next_run_at else None,
                'retry_count': job.retry_count,
                'error_message': job.error_message,
                'is_active': job.is_active,
            }
            for job in jobs
        ]
    
    def get_job_executions(self, job_id: int, limit: int = 50) -> List[Dict]:
        """작업 실행 히스토리 조회"""
        executions = self.db.query(JobExecution).filter(
            JobExecution.job_id == job_id
        ).order_by(
            JobExecution.started_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': execution.id,
                'status': execution.status,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.duration_seconds,
                'error_message': execution.error_message,
            }
            for execution in executions
        ]
    
    def toggle_job(self, job_id: int, active: bool) -> bool:
        """작업 활성화/비활성화"""
        try:
            job = self.db.query(ScheduledJob).filter(
                ScheduledJob.id == job_id
            ).first()
            
            if not job:
                return False
            
            job.is_active = active
            self.db.commit()
            
            app_logger.info(f"작업 {'활성화' if active else '비활성화'}: {job.name}")
            return True
            
        except Exception as e:
            app_logger.error(f"작업 상태 변경 오류: {e}")
            self.db.rollback()
            return False
    
    def delete_job(self, job_id: int) -> bool:
        """작업 삭제"""
        try:
            # 실행 중인 작업이면 취소
            if job_id in self.running_jobs:
                task = self.running_jobs[job_id]
                if not task.done():
                    task.cancel()
                del self.running_jobs[job_id]
            
            # 실행 기록 삭제
            self.db.query(JobExecution).filter(
                JobExecution.job_id == job_id
            ).delete()
            
            # 작업 삭제
            job = self.db.query(ScheduledJob).filter(
                ScheduledJob.id == job_id
            ).first()
            
            if job:
                self.db.delete(job)
                self.db.commit()
                app_logger.info(f"작업 삭제: {job.name}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"작업 삭제 오류: {e}")
            self.db.rollback()
            return False