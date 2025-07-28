#!/usr/bin/env python3
"""
증분 수집 기능 테스트
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from processors.incremental_sync import IncrementalSync
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector
from database.connection import SessionLocal
from database.models import Product, CollectionLog
from utils.logger import app_logger

def setup_test_data():
    """테스트를 위한 초기 데이터 설정"""
    print("=== 테스트 데이터 설정 ===")
    
    db = SessionLocal()
    
    try:
        # 기존 수집 로그 생성 (전체 수집 완료로 표시)
        suppliers = ['zentrade', 'ownerclan', 'domeggook']
        
        for supplier in suppliers:
            # 이미 로그가 있는지 확인
            existing_log = db.query(CollectionLog).filter(
                CollectionLog.supplier == supplier,
                CollectionLog.collection_type == 'full'
            ).first()
            
            if not existing_log:
                # 30분 전에 전체 수집을 완료한 것으로 기록
                log = CollectionLog(
                    supplier=supplier,
                    collection_type='full',
                    status='completed',
                    total_count=10,
                    new_count=10,
                    start_time=datetime.now() - timedelta(minutes=35),
                    end_time=datetime.now() - timedelta(minutes=30)
                )
                db.add(log)
                
        db.commit()
        print("[OK] 초기 수집 로그 설정 완료")
        
    except Exception as e:
        print(f"[ERROR] 테스트 데이터 설정 실패: {e}")
        db.rollback()
        
    finally:
        db.close()

def test_incremental_sync():
    """증분 수집 테스트"""
    print("\n=== 증분 수집 테스트 ===")
    
    sync_manager = IncrementalSync()
    db = SessionLocal()
    
    collectors = [
        ('zentrade', ZentradeCollector({
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        })),
        ('ownerclan', OwnerClanCollector({
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        })),
        ('domeggook', DomeggookCollector({
            'api_key': 'test_key',
            'base_url': 'https://openapi.domeggook.com'
        }))
    ]
    
    try:
        for supplier_name, collector in collectors:
            print(f"\n### {supplier_name} 증분 수집 ###")
            
            # 마지막 동기화 시간 확인
            last_sync = sync_manager.get_last_sync_time(supplier_name, db)
            print(f"마지막 동기화 시간: {last_sync}")
            
            # 증분 수집 실행
            result = sync_manager.sync_incremental(collector, db)
            
            if result.success:
                print(f"[OK] 증분 수집 완료")
                print(f"  - 총 처리: {result.total_count}개")
                print(f"  - 신규: {result.new_count}개")
                print(f"  - 업데이트: {result.updated_count}개")
                print(f"  - 소요 시간: {(result.end_time - result.start_time).total_seconds():.2f}초")
            else:
                print(f"[FAIL] 증분 수집 실패: {result.error_message}")
                
    except Exception as e:
        print(f"[ERROR] 증분 수집 테스트 중 오류: {e}")
        
    finally:
        db.close()

def test_sync_status():
    """동기화 상태 조회 테스트"""
    print("\n=== 동기화 상태 조회 ===")
    
    sync_manager = IncrementalSync()
    db = SessionLocal()
    
    try:
        status = sync_manager.get_sync_status(db)
        
        print("\n공급사별 동기화 상태:")
        for supplier_status in status['suppliers']:
            print(f"\n[{supplier_status['supplier']}]")
            print(f"  - 총 상품 수: {supplier_status['product_count']}개")
            print(f"  - 전체 수집 횟수: {supplier_status['full_sync_count']}회")
            print(f"  - 증분 수집 횟수: {supplier_status['incremental_sync_count']}회")
            
            if supplier_status['last_full_sync']:
                print(f"  - 마지막 전체 수집: {supplier_status['last_full_sync']}")
            else:
                print(f"  - 마지막 전체 수집: 없음")
                
            if supplier_status['last_incremental_sync']:
                print(f"  - 마지막 증분 수집: {supplier_status['last_incremental_sync']}")
            else:
                print(f"  - 마지막 증분 수집: 없음")
                
    except Exception as e:
        print(f"[ERROR] 상태 조회 중 오류: {e}")
        
    finally:
        db.close()

def test_change_detection():
    """변경 감지 테스트"""
    print("\n=== 변경 감지 테스트 ===")
    
    db = SessionLocal()
    
    try:
        # 일부 상품의 정보를 변경
        print("1. 상품 정보 변경 시뮬레이션")
        
        # 오너클랜 상품 중 2개 변경
        products = db.query(Product).filter(
            Product.supplier == 'ownerclan'
        ).limit(2).all()
        
        for product in products:
            # 상품 정보 업데이트
            if isinstance(product.product_info, dict):
                product.product_info['price'] = str(int(product.product_info.get('sale_price', '10000')) + 1000)
                product.product_info['stock_quantity'] = 999
                product.product_info['updated_reason'] = 'price_change'
                
            product.updated_at = datetime.now()
            print(f"  - 상품 {product.product_code} 정보 변경")
            
        db.commit()
        
        # 3초 대기 (시간 차이를 만들기 위해)
        time.sleep(3)
        
        # 증분 수집 실행
        print("\n2. 변경 후 증분 수집")
        sync_manager = IncrementalSync()
        
        collector = OwnerClanCollector({
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        })
        
        result = sync_manager.sync_incremental(collector, db)
        
        if result.success:
            print(f"[OK] 변경 감지 및 증분 수집 완료")
            print(f"  - 업데이트된 상품: {result.updated_count}개")
        
    except Exception as e:
        print(f"[ERROR] 변경 감지 테스트 중 오류: {e}")
        db.rollback()
        
    finally:
        db.close()

def check_collection_logs():
    """수집 로그 확인"""
    print("\n=== 수집 로그 확인 ===")
    
    db = SessionLocal()
    
    try:
        # 최근 수집 로그 10개
        recent_logs = db.query(CollectionLog).order_by(
            CollectionLog.start_time.desc()
        ).limit(10).all()
        
        print(f"\n최근 수집 로그 ({len(recent_logs)}개):")
        for log in recent_logs:
            duration = (log.end_time - log.start_time).total_seconds() if log.end_time else 0
            print(f"  - [{log.supplier}] {log.collection_type} - {log.status}")
            print(f"    시간: {log.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    결과: 총 {log.total_count}개 (신규 {log.new_count}, 업데이트 {log.updated_count})")
            print(f"    소요시간: {duration:.1f}초")
            
            if log.error_message:
                print(f"    오류: {log.error_message}")
                
    except Exception as e:
        print(f"[ERROR] 로그 확인 중 오류: {e}")
        
    finally:
        db.close()

def main():
    """메인 테스트 함수"""
    print("증분 수집 기능 통합 테스트")
    print("=" * 50)
    
    # 1. 테스트 데이터 설정
    setup_test_data()
    
    # 2. 증분 수집 테스트
    test_incremental_sync()
    
    # 3. 동기화 상태 조회
    test_sync_status()
    
    # 4. 변경 감지 테스트
    test_change_detection()
    
    # 5. 수집 로그 확인
    check_collection_logs()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] 증분 수집 테스트 완료!")

if __name__ == "__main__":
    main()