"""
스케줄러 관리 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from services.scheduler.scheduler_core import BatchScheduler, JobType, JobStatus, CronSchedule
from utils.logger import app_logger

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# 전역 스케줄러 인스턴스
scheduler_instance = None


class CreateJobRequest(BaseModel):
    """작업 생성 요청"""
    name: str
    job_type: JobType
    function_name: str
    cron_expression: str
    parameters: Dict[str, Any] = {}
    max_retries: int = 3
    timeout_seconds: int = 3600


class UpdateJobRequest(BaseModel):
    """작업 업데이트 요청"""
    is_active: Optional[bool] = None


@router.post("/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """스케줄러 시작"""
    global scheduler_instance
    
    try:
        if scheduler_instance and scheduler_instance.is_running:
            return {
                "status": "already_running",
                "message": "스케줄러가 이미 실행 중입니다"
            }
        
        scheduler_instance = BatchScheduler()
        
        # 백그라운드에서 스케줄러 실행
        background_tasks.add_task(scheduler_instance.start)
        
        app_logger.info("스케줄러 시작됨")
        
        return {
            "status": "started",
            "message": "스케줄러가 시작되었습니다"
        }
        
    except Exception as e:
        app_logger.error(f"스케줄러 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """스케줄러 중지"""
    global scheduler_instance
    
    try:
        if not scheduler_instance or not scheduler_instance.is_running:
            return {
                "status": "not_running",
                "message": "스케줄러가 실행되지 않았습니다"
            }
        
        scheduler_instance.stop()
        
        return {
            "status": "stopped",
            "message": "스케줄러가 중지되었습니다"
        }
        
    except Exception as e:
        app_logger.error(f"스케줄러 중지 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    global scheduler_instance
    
    is_running = scheduler_instance and scheduler_instance.is_running
    running_jobs_count = len(scheduler_instance.running_jobs) if scheduler_instance else 0
    
    return {
        "is_running": is_running,
        "running_jobs_count": running_jobs_count,
        "status": "running" if is_running else "stopped"
    }


@router.post("/jobs")
async def create_job(request: CreateJobRequest):
    """새 작업 생성"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        # 크론 표현식 파싱
        cron_parts = request.cron_expression.split()
        if len(cron_parts) != 5:
            raise HTTPException(status_code=400, detail="잘못된 크론 표현식 (예: '0 2 * * *')")
        
        schedule = CronSchedule(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            weekday=cron_parts[4]
        )
        
        job_id = scheduler_instance.create_job(
            name=request.name,
            job_type=request.job_type,
            function_name=request.function_name,
            schedule=schedule,
            parameters=request.parameters,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds
        )
        
        return {
            "status": "created",
            "job_id": job_id,
            "message": f"작업 '{request.name}'이 생성되었습니다"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"작업 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def get_jobs(status: Optional[JobStatus] = None):
    """작업 목록 조회"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        jobs = scheduler_instance.get_jobs(status)
        
        return {
            "status": "success",
            "jobs": jobs,
            "total": len(jobs)
        }
        
    except Exception as e:
        app_logger.error(f"작업 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_executions(job_id: int, limit: int = 50):
    """작업 실행 히스토리 조회"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        executions = scheduler_instance.get_job_executions(job_id, limit)
        
        return {
            "status": "success",
            "job_id": job_id,
            "executions": executions,
            "total": len(executions)
        }
        
    except Exception as e:
        app_logger.error(f"작업 히스토리 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/jobs/{job_id}")
async def update_job(job_id: int, request: UpdateJobRequest):
    """작업 업데이트"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        if request.is_active is not None:
            success = scheduler_instance.toggle_job(job_id, request.is_active)
            
            if not success:
                raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
            
            return {
                "status": "updated",
                "job_id": job_id,
                "message": f"작업이 {'활성화' if request.is_active else '비활성화'}되었습니다"
            }
        
        return {
            "status": "no_changes",
            "message": "변경사항이 없습니다"
        }
        
    except Exception as e:
        app_logger.error(f"작업 업데이트 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: int):
    """작업 삭제"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        success = scheduler_instance.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
        
        return {
            "status": "deleted",
            "job_id": job_id,
            "message": "작업이 삭제되었습니다"
        }
        
    except Exception as e:
        app_logger.error(f"작업 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/presets")
async def create_preset_jobs():
    """기본 작업들 생성"""
    global scheduler_instance
    
    try:
        if not scheduler_instance:
            scheduler_instance = BatchScheduler()
        
        presets = [
            {
                "name": "도매처 상품 수집 (매일 새벽 2시)",
                "job_type": JobType.COLLECTION,
                "function_name": "collect_wholesale_products",
                "schedule": CronSchedule.daily(hour=2, minute=0),
                "parameters": {"test_mode": False}
            },
            {
                "name": "베스트셀러 수집 (매일 오후 2시)",
                "job_type": JobType.COLLECTION,
                "function_name": "collect_bestsellers",
                "schedule": CronSchedule.daily(hour=14, minute=0),
                "parameters": {}
            },
            {
                "name": "이미지 처리 (매일 새벽 3시)",
                "job_type": JobType.IMAGE_PROCESSING,
                "function_name": "process_images",
                "schedule": CronSchedule.daily(hour=3, minute=0),
                "parameters": {"limit": 100}
            },
            {
                "name": "데이터 정리 (주 1회 일요일)",
                "job_type": JobType.CLEANUP,
                "function_name": "cleanup_old_data",
                "schedule": CronSchedule.weekly(weekday=0, hour=1, minute=0),
                "parameters": {"days": 30}
            },
            {
                "name": "일일 리포트 생성 (매일 오후 11시)",
                "job_type": JobType.REPORT,
                "function_name": "generate_daily_report",
                "schedule": CronSchedule.daily(hour=23, minute=0),
                "parameters": {}
            },
            {
                "name": "트렌드 분석 (매일 오후 6시)",
                "job_type": JobType.ANALYSIS,
                "function_name": "analyze_trends",
                "schedule": CronSchedule.daily(hour=18, minute=0),
                "parameters": {}
            }
        ]
        
        created_jobs = []
        
        for preset in presets:
            try:
                job_id = scheduler_instance.create_job(
                    name=preset["name"],
                    job_type=preset["job_type"],
                    function_name=preset["function_name"],
                    schedule=preset["schedule"],
                    parameters=preset["parameters"]
                )
                created_jobs.append({
                    "job_id": job_id,
                    "name": preset["name"]
                })
            except Exception as e:
                app_logger.error(f"기본 작업 생성 오류 ({preset['name']}): {e}")
        
        return {
            "status": "created",
            "created_jobs": created_jobs,
            "total": len(created_jobs),
            "message": f"{len(created_jobs)}개의 기본 작업이 생성되었습니다"
        }
        
    except Exception as e:
        app_logger.error(f"기본 작업 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/functions")
async def get_available_functions():
    """사용 가능한 작업 함수 목록"""
    global scheduler_instance
    
    if not scheduler_instance:
        scheduler_instance = BatchScheduler()
    
    functions = list(scheduler_instance.job_functions.keys())
    
    function_info = {
        'collect_wholesale_products': {
            'description': '도매처 상품 수집',
            'parameters': ['suppliers (선택)', 'test_mode (선택)'],
            'recommended_schedule': '매일 새벽 2시'
        },
        'collect_bestsellers': {
            'description': '베스트셀러 수집',
            'parameters': ['marketplaces (선택)'],
            'recommended_schedule': '매일 오후 2시'
        },
        'process_images': {
            'description': '이미지 처리',
            'parameters': ['limit (선택)', 'suppliers (선택)'],
            'recommended_schedule': '매일 새벽 3시'
        },
        'cleanup_old_data': {
            'description': '오래된 데이터 정리',
            'parameters': ['days (기본값: 30)'],
            'recommended_schedule': '주 1회 일요일'
        },
        'generate_daily_report': {
            'description': '일일 리포트 생성',
            'parameters': [],
            'recommended_schedule': '매일 오후 11시'
        },
        'sync_marketplace_data': {
            'description': '마켓플레이스 데이터 동기화',
            'parameters': [],
            'recommended_schedule': '매일 오전 10시'
        },
        'analyze_trends': {
            'description': '트렌드 분석',
            'parameters': [],
            'recommended_schedule': '매일 오후 6시'
        }
    }
    
    return {
        "status": "success",
        "functions": functions,
        "function_info": function_info
    }