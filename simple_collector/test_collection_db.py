#!/usr/bin/env python3
"""
상품 수집 및 데이터베이스 저장 테스트
"""

import sys
from pathlib import Path
from datetime import datetime
import time

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database.connection import SessionLocal, create_tables
from database.models import Product, Supplier, CollectionLog, init_suppliers
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector
from utils.logger import app_logger

def check_database_before():
    """수집 전 데이터베이스 상태 확인"""
    print("\n=== 수집 전 데이터베이스 상태 ===")
    
    db = SessionLocal()
    
    try:
        # 공급사별 상품 수
        suppliers = ['zentrade', 'ownerclan', 'domeggook']
        for supplier in suppliers:
            count = db.query(Product).filter(Product.supplier == supplier).count()
            print(f"{supplier}: {count}개")
            
        total = db.query(Product).count()
        print(f"\n전체 상품 수: {total}개")
        
    finally:
        db.close()

def test_zentrade_collection():
    """젠트레이드 테스트 수집"""
    print("\n=== 젠트레이드 수집 테스트 ===")
    
    db = SessionLocal()
    
    try:
        # 수집기 생성 (테스트 모드)
        credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        collector = ZentradeCollector(credentials)
        collector.test_mode = True  # 테스트 모드 사용
        
        # 인증
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            return
            
        print("[OK] 인증 성공")
        
        # 상품 수집 (10개만)
        count = 0
        new_count = 0
        update_count = 0
        
        print("상품 수집 중...")
        for product_data in collector.collect_products():
            count += 1
            
            # 기존 상품 확인
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                # 업데이트
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
                print(f"  [UPDATE] {product_data.product_code}")
            else:
                # 신규 추가
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
                print(f"  [NEW] {product_data.product_code}: {product_data.product_info.get('product_name', 'N/A')}")
            
            if count >= 10:
                break
                
        db.commit()
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        
        # 수집 로그 저장
        log = CollectionLog(
            supplier='zentrade',
            collection_type='test',
            status='completed',
            total_count=count,
            new_count=new_count,
            updated_count=update_count,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        db.add(log)
        db.commit()
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        db.rollback()
        
    finally:
        db.close()

def test_ownerclan_collection():
    """오너클랜 테스트 수집"""
    print("\n=== 오너클랜 수집 테스트 ===")
    
    db = SessionLocal()
    
    try:
        credentials = {
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth.ownerclan.com/auth'
        }
        
        collector = OwnerClanCollector(credentials)
        collector.test_mode = True
        
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            return
            
        print("[OK] 인증 성공")
        
        count = 0
        new_count = 0
        update_count = 0
        
        print("상품 수집 중...")
        for product_data in collector.collect_products():
            count += 1
            
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
                print(f"  [UPDATE] {product_data.product_code}")
            else:
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
                print(f"  [NEW] {product_data.product_code}: {product_data.product_info.get('product_name', 'N/A')}")
            
            if count >= 10:
                break
                
        db.commit()
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        
        log = CollectionLog(
            supplier='ownerclan',
            collection_type='test',
            status='completed',
            total_count=count,
            new_count=new_count,
            updated_count=update_count,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        db.add(log)
        db.commit()
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        db.rollback()
        
    finally:
        db.close()

def test_domeggook_collection():
    """도매꾹 테스트 수집"""
    print("\n=== 도매꾹 수집 테스트 ===")
    
    db = SessionLocal()
    
    try:
        credentials = {
            'api_key': 'test_key',
            'base_url': 'https://openapi.domeggook.com'
        }
        
        collector = DomeggookCollector(credentials)
        collector.test_mode = True
        
        if not collector.authenticate():
            print("[FAIL] 인증 실패")
            return
            
        print("[OK] 인증 성공")
        
        count = 0
        new_count = 0
        update_count = 0
        
        print("상품 수집 중...")
        for product_data in collector.collect_products():
            count += 1
            
            existing = db.query(Product).filter(
                Product.product_code == product_data.product_code
            ).first()
            
            if existing:
                existing.product_info = product_data.product_info
                existing.updated_at = datetime.now()
                update_count += 1
                print(f"  [UPDATE] {product_data.product_code}")
            else:
                new_product = Product(
                    product_code=product_data.product_code,
                    product_info=product_data.product_info,
                    supplier=product_data.supplier
                )
                db.add(new_product)
                new_count += 1
                print(f"  [NEW] {product_data.product_code}: {product_data.product_info.get('product_name', 'N/A')}")
            
            if count >= 10:
                break
                
        db.commit()
        print(f"\n[완료] 총 {count}개 처리 (신규: {new_count}, 업데이트: {update_count})")
        
        log = CollectionLog(
            supplier='domeggook',
            collection_type='test',
            status='completed',
            total_count=count,
            new_count=new_count,
            updated_count=update_count,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        db.add(log)
        db.commit()
        
    except Exception as e:
        print(f"[ERROR] 수집 중 오류: {e}")
        db.rollback()
        
    finally:
        db.close()

def check_database_after():
    """수집 후 데이터베이스 상태 확인"""
    print("\n=== 수집 후 데이터베이스 상태 ===")
    
    db = SessionLocal()
    
    try:
        # 공급사별 상품 수
        suppliers = ['zentrade', 'ownerclan', 'domeggook']
        for supplier in suppliers:
            count = db.query(Product).filter(Product.supplier == supplier).count()
            print(f"{supplier}: {count}개")
            
            # 최근 상품 3개 출력
            recent_products = db.query(Product).filter(
                Product.supplier == supplier
            ).order_by(Product.created_at.desc()).limit(3).all()
            
            if recent_products:
                print(f"  최근 상품:")
                for p in recent_products:
                    print(f"    - {p.product_code}: {p.product_info.get('product_name', 'N/A')}")
                    
        total = db.query(Product).count()
        print(f"\n전체 상품 수: {total}개")
        
        # 최근 수집 로그
        print("\n=== 최근 수집 로그 ===")
        logs = db.query(CollectionLog).order_by(
            CollectionLog.start_time.desc()
        ).limit(5).all()
        
        for log in logs:
            print(f"{log.supplier} - {log.collection_type}: {log.status} ({log.total_count}개)")
            
    finally:
        db.close()

def check_database_file():
    """데이터베이스 파일 확인"""
    print("\n=== 데이터베이스 파일 확인 ===")
    
    db_path = Path("simple_collector.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1024 / 1024
        print(f"데이터베이스 파일: {db_path}")
        print(f"파일 크기: {size_mb:.2f} MB")
        print(f"수정 시간: {datetime.fromtimestamp(db_path.stat().st_mtime)}")
    else:
        print("데이터베이스 파일이 없습니다!")

def main():
    """메인 함수"""
    print("상품 수집 및 데이터베이스 저장 테스트")
    print("=" * 50)
    
    # 데이터베이스 초기화
    print("데이터베이스 초기화 중...")
    create_tables()
    
    db = SessionLocal()
    init_suppliers(db)
    db.close()
    
    # 데이터베이스 파일 확인
    check_database_file()
    
    # 수집 전 상태
    check_database_before()
    
    # 각 공급사별 수집 테스트
    test_zentrade_collection()
    time.sleep(1)
    
    test_ownerclan_collection()
    time.sleep(1)
    
    test_domeggook_collection()
    
    # 수집 후 상태
    check_database_after()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] 상품 수집 테스트 완료!")

if __name__ == "__main__":
    main()