"""
도매처 전체 상품 수집 스크립트
실제 API를 사용하여 모든 도매처의 상품을 수집합니다.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import SessionLocal
from database.models import Supplier
from utils.logger import app_logger
import requests


def check_api_settings():
    """API 설정 확인"""
    db = SessionLocal()
    try:
        suppliers = db.query(Supplier).filter(
            Supplier.is_active == True
        ).all()
        
        # 도매처만 필터링 (marketplace가 아닌 것)
        suppliers = [s for s in suppliers if not s.api_config.get('marketplace', False)]
        
        app_logger.info("=== 도매처 API 설정 확인 ===")
        
        missing_settings = []
        
        for supplier in suppliers:
            app_logger.info(f"\n{supplier.supplier_name} ({supplier.supplier_code}):")
            
            # API 키 확인
            if supplier.supplier_code == 'zentrade':
                if not supplier.api_key or supplier.api_key == 'your_api_id_here':
                    app_logger.warning("  - API ID 설정 필요")
                    missing_settings.append(supplier.supplier_code)
                else:
                    app_logger.info(f"  - API ID: {supplier.api_key[:10]}...")
                    
            elif supplier.supplier_code == 'ownerclan':
                if not supplier.api_key or supplier.api_key == 'your_username_here':
                    app_logger.warning("  - 사용자명 설정 필요")
                    missing_settings.append(supplier.supplier_code)
                else:
                    app_logger.info(f"  - 사용자명: {supplier.api_key}")
                    
            elif supplier.supplier_code in ['domeggook', 'domomae']:
                if not supplier.api_key or supplier.api_key == 'your_api_key_here':
                    app_logger.warning("  - API 키 설정 필요")
                    missing_settings.append(supplier.supplier_code)
                else:
                    app_logger.info(f"  - API 키: {supplier.api_key[:10]}...")
        
        return missing_settings
        
    finally:
        db.close()


async def collect_supplier(supplier_code: str, test_mode: bool = False):
    """특정 도매처 수집"""
    try:
        # API 호출
        url = f"http://localhost:8000/collection/full/{supplier_code}"
        params = {"test_mode": test_mode}
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            app_logger.info(f"{supplier_code} 수집이 시작되었습니다.")
            data = response.json()
            
            # 백그라운드 작업 시작됨
            if data.get('status') == 'started':
                app_logger.info("백그라운드에서 수집이 진행됩니다.")
                
                # 수집 완료까지 상태 모니터링 (test_mode일 때는 빠르게 완료)
                max_wait = 60 if test_mode else 300  # 테스트: 1분, 실제: 5분
                check_interval = 5 if test_mode else 10
                elapsed = 0
                
                while elapsed < max_wait:
                    await asyncio.sleep(check_interval)
                    elapsed += check_interval
                    
                    # 상태 확인
                    status_response = requests.get(f"http://localhost:8000/collection/status/{supplier_code}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        
                        if status['status'] == 'completed':
                            app_logger.info(f"\n{supplier_code} 수집 완료!")
                            app_logger.info(f"  - 총 상품: {status.get('total_count', 0)}개")
                            app_logger.info(f"  - 신규: {status.get('new_count', 0)}개")
                            app_logger.info(f"  - 업데이트: {status.get('updated_count', 0)}개")
                            app_logger.info(f"  - 오류: {status.get('error_count', 0)}개")
                            break
                        elif status['status'] == 'failed':
                            app_logger.error(f"수집 실패: {status.get('error_message', '알 수 없는 오류')}")
                            break
                        else:
                            app_logger.info(f"진행 중... ({elapsed}초 경과)")
                else:
                    app_logger.warning(f"{supplier_code} 수집이 {max_wait}초 내에 완료되지 않았습니다.")
                    app_logger.info("웹 UI에서 진행 상황을 확인하세요.")
                    
        else:
            app_logger.error(f"수집 시작 실패: {response.status_code}")
            app_logger.error(f"오류: {response.text}")
            raise Exception(f"API 오류: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        app_logger.error("API 서버에 연결할 수 없습니다.")
        raise
    except Exception as e:
        app_logger.error(f"{supplier_code} 수집 중 오류: {e}")
        raise


async def collect_all_suppliers(test_mode: bool = False):
    """모든 도매처 수집"""
    # API 설정 확인
    missing = check_api_settings()
    
    if missing:
        app_logger.warning(f"\n다음 도매처의 API 설정이 필요합니다: {', '.join(missing)}")
        app_logger.info("웹 UI의 설정 메뉴에서 API 키를 입력해주세요.")
        app_logger.info("URL: http://localhost:4173/settings")
        
        if not test_mode:
            app_logger.error("실제 수집을 위해서는 API 키 설정이 필요합니다.")
            app_logger.info("\n=== API 키 설정 가이드 ===")
            app_logger.info("1. 웹 브라우저에서 http://localhost:4173/settings 접속")
            app_logger.info("2. 각 도매처의 API 키 입력:")
            app_logger.info("   - Zentrade: API ID 입력")
            app_logger.info("   - Ownerclan: 사용자명 입력")
            app_logger.info("   - Domeggook: API 키 입력")
            app_logger.info("   - Domomae: API 키 입력")
            app_logger.info("3. 저장 후 다시 실행")
            return
    
    # 도매처 목록
    suppliers = ['zentrade', 'ownerclan', 'domeggook', 'domomae']
    
    app_logger.info(f"\n=== 전체 도매처 수집 시작 ===")
    app_logger.info(f"모드: {'테스트' if test_mode else '실제'}")
    app_logger.info(f"대상 도매처: {', '.join(suppliers)}")
    
    # 수집 결과 추적
    results = {}
    
    # 순차적으로 수집 (동시 실행 시 부하 문제 가능)
    for supplier_code in suppliers:
        app_logger.info(f"\n{'='*50}")
        app_logger.info(f"{supplier_code} 수집 시작...")
        
        try:
            await collect_supplier(supplier_code, test_mode)
            results[supplier_code] = "성공"
        except Exception as e:
            app_logger.error(f"{supplier_code} 수집 실패: {e}")
            results[supplier_code] = f"실패: {str(e)}"
        
        # 다음 수집까지 잠시 대기
        if supplier_code != suppliers[-1]:
            app_logger.info("\n다음 도매처 수집까지 10초 대기...")
            await asyncio.sleep(10)
    
    # 수집 결과 요약
    app_logger.info("\n=== 전체 수집 작업 완료 ===")
    app_logger.info("\n수집 결과:")
    for supplier, status in results.items():
        app_logger.info(f"  - {supplier}: {status}")
    
    app_logger.info("\n각 도매처의 수집 진행 상황은 웹 UI에서 확인하세요.")
    app_logger.info("URL: http://localhost:4173/collection")


def show_collection_summary():
    """수집 결과 요약"""
    db = SessionLocal()
    try:
        from database.models_v2 import WholesaleProduct
        
        app_logger.info("\n=== 수집 결과 요약 ===")
        
        # 도매처별 상품 수
        suppliers = ['zentrade', 'ownerclan', 'domeggook', 'domomae']
        
        total = 0
        for supplier in suppliers:
            count = db.query(WholesaleProduct).filter(
                WholesaleProduct.supplier == supplier,
                WholesaleProduct.is_active == True
            ).count()
            
            app_logger.info(f"{supplier}: {count:,}개")
            total += count
        
        app_logger.info(f"\n총 상품 수: {total:,}개")
        
        # 최근 수집 시간
        latest = db.query(WholesaleProduct).order_by(
            WholesaleProduct.last_synced_at.desc()
        ).first()
        
        if latest:
            app_logger.info(f"최근 수집: {latest.last_synced_at}")
            
    finally:
        db.close()


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='도매처 전체 상품 수집')
    parser.add_argument('--supplier', type=str, help='특정 도매처만 수집 (zentrade, ownerclan, domeggook, domomae)')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (더미 데이터 사용)')
    parser.add_argument('--summary', action='store_true', help='수집 결과 요약만 표시')
    
    args = parser.parse_args()
    
    if args.summary:
        show_collection_summary()
        return
    
    # API 서버 확인
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            app_logger.error("API 서버가 실행되지 않았습니다.")
            app_logger.info("다음 명령으로 API 서버를 시작하세요:")
            app_logger.info("cd simple_collector && python api/main.py")
            return
    except:
        app_logger.error("API 서버에 연결할 수 없습니다.")
        return
    
    if args.supplier:
        # 특정 도매처만 수집
        await collect_supplier(args.supplier, args.test)
    else:
        # 전체 도매처 수집
        await collect_all_suppliers(args.test)
    
    # 수집 결과 요약
    app_logger.info("\n10초 후 수집 결과를 표시합니다...")
    await asyncio.sleep(10)
    show_collection_summary()


if __name__ == "__main__":
    app_logger.info(f"수집 시작 시간: {datetime.now()}")
    asyncio.run(main())