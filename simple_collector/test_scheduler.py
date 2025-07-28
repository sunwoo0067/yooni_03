"""
배치 스케줄러 테스트
"""

import asyncio
import sys
import requests
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from services.scheduler.scheduler_core import BatchScheduler, JobType, CronSchedule
from utils.logger import app_logger


def test_scheduler_core():
    """스케줄러 코어 테스트"""
    app_logger.info("=== 스케줄러 코어 테스트 시작 ===")
    
    scheduler = BatchScheduler()
    
    # 테스트 작업 생성
    job_id = scheduler.create_job(
        name="테스트 작업",
        job_type=JobType.COLLECTION,
        function_name="collect_wholesale_products",
        schedule=CronSchedule.hourly(minute=0),
        parameters={"test_mode": True, "suppliers": ["zentrade"]},
        max_retries=1,
        timeout_seconds=300
    )
    
    app_logger.info(f"테스트 작업 생성됨: ID {job_id}")
    
    # 작업 목록 조회
    jobs = scheduler.get_jobs()
    app_logger.info(f"총 작업 수: {len(jobs)}")
    
    for job in jobs:
        app_logger.info(f"  - {job['name']}: {job['status']} (다음 실행: {job['next_run_at']})")
    
    # 작업 비활성화
    scheduler.toggle_job(job_id, False)
    app_logger.info(f"작업 {job_id} 비활성화됨")
    
    # 작업 삭제
    scheduler.delete_job(job_id)
    app_logger.info(f"작업 {job_id} 삭제됨")


async def test_api_endpoints():
    """API 엔드포인트 테스트"""
    app_logger.info("\n=== 스케줄러 API 테스트 시작 ===")
    
    base_url = "http://localhost:8000"
    
    # API 서버 확인
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            app_logger.error("API 서버가 실행되지 않았습니다.")
            return
    except:
        app_logger.error("API 서버에 연결할 수 없습니다.")
        return
    
    # 1. 스케줄러 상태 확인
    try:
        response = requests.get(f"{base_url}/scheduler/status")
        if response.status_code == 200:
            status = response.json()
            app_logger.info(f"스케줄러 상태: {status}")
        else:
            app_logger.error(f"상태 조회 실패: {response.status_code}")
    except Exception as e:
        app_logger.error(f"상태 조회 오류: {e}")
    
    # 2. 스케줄러 시작
    try:
        response = requests.post(f"{base_url}/scheduler/start")
        if response.status_code == 200:
            result = response.json()
            app_logger.info(f"스케줄러 시작: {result['message']}")
        else:
            app_logger.error(f"스케줄러 시작 실패: {response.status_code}")
    except Exception as e:
        app_logger.error(f"스케줄러 시작 오류: {e}")
    
    # 잠시 대기
    await asyncio.sleep(2)
    
    # 3. 기본 작업 생성
    try:
        response = requests.post(f"{base_url}/scheduler/jobs/presets")
        if response.status_code == 200:
            result = response.json()
            app_logger.info(f"기본 작업 생성: {result['message']}")
        else:
            app_logger.error(f"기본 작업 생성 실패: {response.status_code}")
    except Exception as e:
        app_logger.error(f"기본 작업 생성 오류: {e}")
    
    # 4. 작업 목록 조회
    try:
        response = requests.get(f"{base_url}/scheduler/jobs")
        if response.status_code == 200:
            result = response.json()
            jobs = result['jobs']
            app_logger.info(f"총 작업 수: {len(jobs)}")
            
            for job in jobs[:3]:  # 처음 3개만 표시
                app_logger.info(f"  - {job['name']}: {job['status']}")
                
        else:
            app_logger.error(f"작업 목록 조회 실패: {response.status_code}")
    except Exception as e:
        app_logger.error(f"작업 목록 조회 오류: {e}")
    
    # 5. 사용 가능한 함수 조회
    try:
        response = requests.get(f"{base_url}/scheduler/functions")
        if response.status_code == 200:
            result = response.json()
            functions = result['functions']
            app_logger.info(f"사용 가능한 함수: {', '.join(functions)}")
        else:
            app_logger.error(f"함수 목록 조회 실패: {response.status_code}")
    except Exception as e:
        app_logger.error(f"함수 목록 조회 오류: {e}")
    
    # 6. 커스텀 작업 생성
    try:
        custom_job = {
            "name": "테스트 베스트셀러 수집",
            "job_type": "COLLECTION",
            "function_name": "collect_bestsellers",
            "cron_expression": "0 */2 * * *",  # 2시간마다
            "parameters": {"marketplaces": ["coupang"]},
            "max_retries": 2,
            "timeout_seconds": 1800
        }
        
        response = requests.post(f"{base_url}/scheduler/jobs", json=custom_job)
        if response.status_code == 200:
            result = response.json()
            app_logger.info(f"커스텀 작업 생성: {result['message']}")
            
            # 생성된 작업 비활성화 (테스트용)
            job_id = result['job_id']
            response = requests.patch(
                f"{base_url}/scheduler/jobs/{job_id}",
                json={"is_active": False}
            )
            if response.status_code == 200:
                app_logger.info(f"테스트 작업 {job_id} 비활성화됨")
            
        else:
            app_logger.error(f"커스텀 작업 생성 실패: {response.status_code} - {response.text}")
    except Exception as e:
        app_logger.error(f"커스텀 작업 생성 오류: {e}")


async def test_job_execution():
    """작업 실행 테스트"""
    app_logger.info("\n=== 작업 실행 테스트 시작 ===")
    
    # 간단한 작업 실행 테스트
    from services.scheduler.job_functions import generate_daily_report
    
    try:
        result = await generate_daily_report()
        app_logger.info(f"일일 리포트 생성 테스트: {result['status']}")
        
        if result['status'] == 'completed':
            app_logger.info(f"리포트 파일: {result.get('report_file', 'N/A')}")
        
    except Exception as e:
        app_logger.error(f"작업 실행 테스트 오류: {e}")


def test_cron_schedule():
    """크론 스케줄 테스트"""
    app_logger.info("\n=== 크론 스케줄 테스트 ===")
    
    # 다양한 스케줄 생성
    schedules = [
        ("매일 새벽 2시", CronSchedule.daily(hour=2, minute=0)),
        ("시간마다", CronSchedule.hourly(minute=30)),
        ("주 1회 일요일 새벽 1시", CronSchedule.weekly(weekday=0, hour=1, minute=0)),
        ("매일 오후 6시 30분", CronSchedule.daily(hour=18, minute=30)),
    ]
    
    for desc, schedule in schedules:
        expression = schedule.to_expression()
        app_logger.info(f"{desc}: {expression}")


async def main():
    """메인 테스트 함수"""
    app_logger.info(f"배치 스케줄러 테스트 시작: {datetime.now()}")
    
    # 1. 크론 스케줄 테스트
    test_cron_schedule()
    
    # 2. 스케줄러 코어 테스트
    test_scheduler_core()
    
    # 3. API 엔드포인트 테스트
    await test_api_endpoints()
    
    # 4. 작업 실행 테스트
    await test_job_execution()
    
    app_logger.info("\n=== 테스트 완료 ===")
    app_logger.info("웹 UI에서 스케줄러를 확인하세요:")
    app_logger.info("URL: http://localhost:4173/scheduler")


if __name__ == "__main__":
    asyncio.run(main())