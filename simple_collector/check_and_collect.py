"""
도매처 상품 수집 전 확인 및 실행 스크립트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import requests

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import SessionLocal
from database.models import Supplier
from database.models_v2 import WholesaleProduct
from utils.logger import app_logger


def check_current_status():
    """현재 상품 상태 확인"""
    db = SessionLocal()
    try:
        app_logger.info("=== 현재 도매처 상품 현황 ===")
        
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
        
        return total
        
    finally:
        db.close()


def check_api_keys():
    """API 키 설정 확인"""
    db = SessionLocal()
    try:
        suppliers = db.query(Supplier).filter(
            Supplier.is_active == True
        ).all()
        
        # 도매처만 필터링
        suppliers = [s for s in suppliers if not s.api_config.get('marketplace', False)]
        
        app_logger.info("\n=== API 키 설정 상태 ===")
        
        ready_suppliers = []
        not_ready = []
        
        for supplier in suppliers:
            if supplier.supplier_code == 'zentrade':
                if supplier.api_key and supplier.api_key != 'your_api_id_here':
                    ready_suppliers.append(supplier.supplier_code)
                    app_logger.info(f"✓ {supplier.supplier_name}: API 설정 완료")
                else:
                    not_ready.append(supplier.supplier_code)
                    app_logger.warning(f"✗ {supplier.supplier_name}: API ID 필요")
                    
            elif supplier.supplier_code == 'ownerclan':
                if supplier.api_key and supplier.api_key != 'your_username_here':
                    ready_suppliers.append(supplier.supplier_code)
                    app_logger.info(f"✓ {supplier.supplier_name}: API 설정 완료")
                else:
                    not_ready.append(supplier.supplier_code)
                    app_logger.warning(f"✗ {supplier.supplier_name}: 사용자명 필요")
                    
            elif supplier.supplier_code in ['domeggook', 'domomae']:
                if supplier.api_key and supplier.api_key != 'your_api_key_here':
                    ready_suppliers.append(supplier.supplier_code)
                    app_logger.info(f"✓ {supplier.supplier_name}: API 설정 완료")
                else:
                    not_ready.append(supplier.supplier_code)
                    app_logger.warning(f"✗ {supplier.supplier_name}: API 키 필요")
        
        return ready_suppliers, not_ready
        
    finally:
        db.close()


async def collect_ready_suppliers(suppliers: list, test_mode: bool = False):
    """준비된 도매처만 수집"""
    app_logger.info(f"\n=== 수집 시작 ({', '.join(suppliers)}) ===")
    app_logger.info(f"모드: {'테스트' if test_mode else '실제'}")
    
    for supplier_code in suppliers:
        try:
            app_logger.info(f"\n{supplier_code} 수집 시작...")
            
            # API 호출
            url = f"http://localhost:8000/collection/full/{supplier_code}"
            params = {"test_mode": test_mode}
            
            response = requests.post(url, params=params)
            
            if response.status_code == 200:
                app_logger.info(f"{supplier_code} 수집이 시작되었습니다.")
                
                # 잠시 대기 후 상태 확인
                await asyncio.sleep(5)
                
                status_response = requests.get(f"http://localhost:8000/collection/status/{supplier_code}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    app_logger.info(f"현재 상태: {status['status']}")
                    
            else:
                app_logger.error(f"{supplier_code} 수집 시작 실패: {response.status_code}")
                
        except Exception as e:
            app_logger.error(f"{supplier_code} 수집 중 오류: {e}")
        
        # 다음 수집까지 대기
        if supplier_code != suppliers[-1]:
            await asyncio.sleep(5)


async def main():
    """메인 함수"""
    app_logger.info(f"\n시작 시간: {datetime.now()}")
    
    # 1. 현재 상품 현황 확인
    current_count = check_current_status()
    
    # 2. API 키 설정 확인
    ready, not_ready = check_api_keys()
    
    if not_ready:
        app_logger.info("\n=== API 키 설정 안내 ===")
        app_logger.info("1. 웹 브라우저에서 http://localhost:4173/settings 접속")
        app_logger.info("2. 각 도매처의 API 키 입력 후 저장")
        app_logger.info("3. 이 스크립트를 다시 실행")
        
        if ready:
            app_logger.info(f"\n설정된 도매처만 수집하시겠습니까? ({', '.join(ready)})")
            app_logger.info("Enter를 누르면 진행, Ctrl+C로 취소")
            try:
                input()
                await collect_ready_suppliers(ready, test_mode=False)
            except KeyboardInterrupt:
                app_logger.info("\n취소되었습니다.")
                return
    else:
        # 모든 도매처 준비됨
        app_logger.info("\n모든 도매처 API 설정이 완료되었습니다!")
        
        # API 서버 확인
        try:
            response = requests.get("http://localhost:8000/health")
            if response.status_code != 200:
                app_logger.error("API 서버가 실행되지 않았습니다.")
                return
        except:
            app_logger.error("API 서버에 연결할 수 없습니다.")
            app_logger.info("다음 명령으로 API 서버를 시작하세요:")
            app_logger.info("cd simple_collector && python api/main.py")
            return
        
        app_logger.info("\n수집을 시작하시겠습니까? (실제 API 사용)")
        app_logger.info("Enter를 누르면 진행, Ctrl+C로 취소")
        
        try:
            input()
            await collect_ready_suppliers(ready, test_mode=False)
            
            # 수집 후 결과 확인
            app_logger.info("\n10초 후 수집 결과를 확인합니다...")
            await asyncio.sleep(10)
            
            new_count = check_current_status()
            app_logger.info(f"\n수집 전: {current_count:,}개")
            app_logger.info(f"수집 후: {new_count:,}개")
            app_logger.info(f"증가: {new_count - current_count:,}개")
            
        except KeyboardInterrupt:
            app_logger.info("\n취소되었습니다.")
    
    app_logger.info("\n웹 UI에서 상세 내용을 확인하세요:")
    app_logger.info("- 상품 목록: http://localhost:4173/products")
    app_logger.info("- 수집 상태: http://localhost:4173/collection")


if __name__ == "__main__":
    asyncio.run(main())