#!/usr/bin/env python3
"""
전체 상품 수집 스크립트
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database.connection import SessionLocal, create_tables
from database.models import Product, Supplier, CollectionLog, init_suppliers
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector
from utils.logger import app_logger

def collect_zentrade(test_mode=True, limit=None):
    """젠트레이드 전체 수집"""
    print("\n=== 젠트레이드 전체 수집 시작 ===")
    
    db = SessionLocal()
    
    # 수집 로그 생성
    log = CollectionLog(
        supplier='zentrade',
        collection_type='full',
        status='running',
        start_time=datetime.now()
    )
    db.add(log)
    db.commit()
    
    try:
        # 수집기 생성
        credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        collector = ZentradeCollector(credentials)
        collector.test_mode = test_mode
        
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            log.status = 'failed'
            log.error_message = '인증 실패'
            db.commit()
            return
            
        print("[OK] 인증 성공")
        print("상품 수집 중...")
        
        count = 0
        new_count = 0
        update_count = 0
        
        for product_data in collector.collect_products():
            count += 1
            
            # 기존 상품 확인
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
            else:
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
            
            # 진행 상황 출력
            if count % 100 == 0:
                db.commit()
                print(f"  진행 중: {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
                
            # 제한이 있으면 확인
            if limit and count >= limit:
                break
                
        db.commit()
        
        # 로그 업데이트
        log.end_time = datetime.now()
        log.status = 'completed'
        log.total_count = count
        log.new_count = new_count
        log.updated_count = update_count
        db.commit()
        
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        print(f"소요 시간: {(log.end_time - log.start_time).total_seconds():.1f}초")
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        log.status = 'failed'
        log.error_message = str(e)
        log.end_time = datetime.now()
        db.commit()
        
    finally:
        db.close()

def collect_ownerclan(test_mode=True, limit=None):
    """오너클랜 전체 수집"""
    print("\n=== 오너클랜 전체 수집 시작 ===")
    
    db = SessionLocal()
    
    log = CollectionLog(
        supplier='ownerclan',
        collection_type='full',
        status='running',
        start_time=datetime.now()
    )
    db.add(log)
    db.commit()
    
    try:
        credentials = {
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth.ownerclan.com/auth'
        }
        
        collector = OwnerClanCollector(credentials)
        collector.test_mode = test_mode
        
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            log.status = 'failed'
            log.error_message = '인증 실패'
            db.commit()
            return
            
        print("[OK] 인증 성공")
        print("상품 수집 중...")
        
        count = 0
        new_count = 0
        update_count = 0
        
        for product_data in collector.collect_products():
            count += 1
            
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
            else:
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
            
            if count % 100 == 0:
                db.commit()
                print(f"  진행 중: {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
                
            if limit and count >= limit:
                break
                
        db.commit()
        
        log.end_time = datetime.now()
        log.status = 'completed'
        log.total_count = count
        log.new_count = new_count
        log.updated_count = update_count
        db.commit()
        
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        print(f"소요 시간: {(log.end_time - log.start_time).total_seconds():.1f}초")
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        log.status = 'failed'
        log.error_message = str(e)
        log.end_time = datetime.now()
        db.commit()
        
    finally:
        db.close()

def collect_domeggook(test_mode=True, limit=None):
    """도매꾹 전체 수집"""
    print("\n=== 도매꾹 전체 수집 시작 ===")
    
    db = SessionLocal()
    
    log = CollectionLog(
        supplier='domeggook',
        collection_type='full',
        status='running',
        start_time=datetime.now()
    )
    db.add(log)
    db.commit()
    
    try:
        credentials = {
            'api_key': 'test_key',
            'base_url': 'https://openapi.domeggook.com'
        }
        
        collector = DomeggookCollector(credentials)
        collector.test_mode = test_mode
        
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            log.status = 'failed'
            log.error_message = '인증 실패'
            db.commit()
            return
            
        print("[OK] 인증 성공")
        print("상품 수집 중...")
        
        count = 0
        new_count = 0
        update_count = 0
        
        for product_data in collector.collect_products():
            count += 1
            
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
            else:
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
            
            if count % 100 == 0:
                db.commit()
                print(f"  진행 중: {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
                
            if limit and count >= limit:
                break
                
        db.commit()
        
        log.end_time = datetime.now()
        log.status = 'completed'
        log.total_count = count
        log.new_count = new_count
        log.updated_count = update_count
        db.commit()
        
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        print(f"소요 시간: {(log.end_time - log.start_time).total_seconds():.1f}초")
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        log.status = 'failed'
        log.error_message = str(e)
        log.end_time = datetime.now()
        db.commit()
        
    finally:
        db.close()

def check_status():
    """현재 상태 확인"""
    print("\n=== 현재 데이터베이스 상태 ===")
    
    db = SessionLocal()
    
    # 전체 상품 수
    total = db.query(Product).count()
    print(f"전체 상품 수: {total}개")
    
    # 공급사별 상품 수
    suppliers = ['zentrade', 'ownerclan', 'domeggook']
    for supplier in suppliers:
        count = db.query(Product).filter(Product.supplier == supplier).count()
        print(f"  - {supplier}: {count}개")
        
    # 최근 수집 로그
    print("\n최근 수집 기록:")
    logs = db.query(CollectionLog).order_by(
        CollectionLog.start_time.desc()
    ).limit(5).all()
    
    for log in logs:
        duration = (log.end_time - log.start_time).total_seconds() if log.end_time else 0
        print(f"  - [{log.supplier}] {log.collection_type} - {log.status} ({log.total_count}개, {duration:.1f}초)")
        
    db.close()

def main():
    """메인 함수"""
    print("전체 상품 수집")
    print("=" * 50)
    
    # 현재 상태 확인
    check_status()
    
    print("\n수집 옵션:")
    print("1. 테스트 모드 (더미 데이터)")
    print("2. 실제 API 모드 (API 키 필요)")
    print("3. 제한된 수집 (각 100개씩)")
    print("4. 전체 수집 (시간 소요)")
    
    choice = input("\n선택 (1-4, 기본값 3): ").strip() or "3"
    
    test_mode = True
    limit = None
    
    if choice == "1":
        test_mode = True
        limit = None
        print("\n테스트 모드로 전체 수집을 시작합니다.")
    elif choice == "2":
        test_mode = False
        limit = None
        print("\n실제 API로 전체 수집을 시작합니다.")
        print("※ API 키가 설정되어 있어야 합니다!")
    elif choice == "3":
        test_mode = True
        limit = 100
        print("\n테스트 모드로 각 100개씩 수집합니다.")
    elif choice == "4":
        test_mode = True
        limit = None
        print("\n테스트 모드로 전체 수집을 시작합니다.")
        print("※ 시간이 오래 걸릴 수 있습니다!")
    
    confirm = input("\n계속하시겠습니까? (y/n): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return
    
    # 수집 시작
    start_time = time.time()
    
    # 각 공급사별 수집
    collect_zentrade(test_mode, limit)
    time.sleep(1)
    
    collect_ownerclan(test_mode, limit)
    time.sleep(1)
    
    collect_domeggook(test_mode, limit)
    
    # 최종 결과
    print("\n" + "=" * 50)
    print("전체 수집 완료!")
    print(f"총 소요 시간: {time.time() - start_time:.1f}초")
    
    # 최종 상태
    check_status()

if __name__ == "__main__":
    main()