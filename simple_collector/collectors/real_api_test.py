#!/usr/bin/env python3
"""
실제 API 키로 도매처 연동 테스트
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from config.settings import settings
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector
from database.connection import SessionLocal, create_tables
from database.models import Product, init_suppliers
from utils.logger import app_logger

def test_zentrade_real():
    """젠트레이드 실제 API 테스트"""
    print("\n=== 젠트레이드 실제 API 테스트 ===")
    
    if not settings.ZENTRADE_API_ID or not settings.ZENTRADE_API_KEY:
        print("[SKIP] 젠트레이드 API 키가 설정되지 않았습니다.")
        print("  .env 파일에 ZENTRADE_API_ID와 ZENTRADE_API_KEY를 설정하세요.")
        return False
    
    try:
        credentials = {
            'api_id': settings.ZENTRADE_API_ID,
            'api_key': settings.ZENTRADE_API_KEY,
            'base_url': settings.ZENTRADE_BASE_URL
        }
        
        collector = ZentradeCollector(credentials)
        collector.test_mode = False  # 실제 API 사용
        
        print(f"API ID: {settings.ZENTRADE_API_ID[:10]}...")
        print(f"API URL: {settings.ZENTRADE_BASE_URL}")
        
        # 인증 테스트
        print("\n1. 인증 테스트...")
        if collector.authenticate():
            print("[OK] 인증 성공!")
        else:
            print("[FAIL] 인증 실패!")
            return False
        
        # 상품 수집 테스트 (처음 10개만)
        print("\n2. 상품 수집 테스트 (10개)...")
        count = 0
        for product in collector.collect_products():
            count += 1
            print(f"  - {product.product_code}: {product.product_info.get('product_name', 'N/A')}")
            if count >= 10:
                break
        
        print(f"\n[SUCCESS] 젠트레이드 테스트 완료! {count}개 상품 확인")
        return True
        
    except Exception as e:
        print(f"[ERROR] 젠트레이드 테스트 중 오류: {e}")
        return False

def test_ownerclan_real():
    """오너클랜 실제 API 테스트"""
    print("\n=== 오너클랜 실제 API 테스트 ===")
    
    if not settings.OWNERCLAN_USERNAME or not settings.OWNERCLAN_PASSWORD:
        print("[SKIP] 오너클랜 계정 정보가 설정되지 않았습니다.")
        print("  .env 파일에 OWNERCLAN_USERNAME과 OWNERCLAN_PASSWORD를 설정하세요.")
        return False
    
    try:
        credentials = {
            'username': settings.OWNERCLAN_USERNAME,
            'password': settings.OWNERCLAN_PASSWORD,
            'api_url': settings.OWNERCLAN_API_URL,
            'auth_url': settings.OWNERCLAN_AUTH_URL
        }
        
        collector = OwnerClanCollector(credentials)
        collector.test_mode = False  # 실제 API 사용
        
        print(f"Username: {settings.OWNERCLAN_USERNAME}")
        print(f"API URL: {settings.OWNERCLAN_API_URL}")
        
        # 인증 테스트
        print("\n1. 인증 테스트...")
        if collector.authenticate():
            print("[OK] 인증 성공!")
            print(f"  토큰: {collector.token[:20]}...")
        else:
            print("[FAIL] 인증 실패!")
            return False
        
        # 상품 코드 수집 테스트
        print("\n2. 상품 코드 수집 테스트...")
        codes = collector._collect_product_codes(limit=10)
        print(f"  수집된 코드 수: {len(codes)}개")
        
        # 상품 상세 정보 테스트 (처음 3개만)
        print("\n3. 상품 상세 정보 테스트 (3개)...")
        for i, code in enumerate(codes[:3]):
            product = collector._get_product_details(code)
            if product:
                print(f"  - {product.product_code}: {product.product_info.get('product_name', 'N/A')}")
        
        print(f"\n[SUCCESS] 오너클랜 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"[ERROR] 오너클랜 테스트 중 오류: {e}")
        return False

def test_domeggook_real():
    """도매꾹 실제 API 테스트"""
    print("\n=== 도매꾹 실제 API 테스트 ===")
    
    if not settings.DOMEGGOOK_API_KEY:
        print("[SKIP] 도매꾹 API 키가 설정되지 않았습니다.")
        print("  .env 파일에 DOMEGGOOK_API_KEY를 설정하세요.")
        return False
    
    try:
        credentials = {
            'api_key': settings.DOMEGGOOK_API_KEY,
            'base_url': settings.DOMEGGOOK_BASE_URL
        }
        
        collector = DomeggookCollector(credentials)
        collector.test_mode = False  # 실제 API 사용
        
        print(f"API Key: {settings.DOMEGGOOK_API_KEY[:10]}...")
        print(f"API URL: {settings.DOMEGGOOK_BASE_URL}")
        
        # 인증 테스트
        print("\n1. 인증 테스트...")
        if collector.authenticate():
            print("[OK] 인증 성공!")
        else:
            print("[FAIL] 인증 실패!")
            return False
        
        # 카테고리 수집 테스트
        print("\n2. 카테고리 수집 테스트...")
        categories = collector._get_categories()
        print(f"  전체 카테고리 수: {len(categories)}개")
        
        # 중분류 카테고리 필터링
        middle_categories = collector._filter_middle_categories(categories)
        print(f"  중분류 카테고리 수: {len(middle_categories)}개")
        
        # 첫 번째 카테고리의 상품 테스트
        if middle_categories:
            print(f"\n3. 상품 수집 테스트 (카테고리: {middle_categories[0]})...")
            products = collector._get_products_by_category(middle_categories[0], page=1, limit=5)
            print(f"  수집된 상품 수: {len(products)}개")
            
            for product in products[:3]:
                print(f"  - {product['product_code']}: {product['product_name']}")
        
        print(f"\n[SUCCESS] 도매꾹 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"[ERROR] 도매꾹 테스트 중 오류: {e}")
        return False

def save_to_database_test():
    """데이터베이스 저장 테스트"""
    print("\n=== 데이터베이스 저장 테스트 ===")
    
    db = SessionLocal()
    
    try:
        # 테스트 상품 저장
        test_products = [
            {
                'supplier': 'zentrade',
                'product_code': 'ZT_REAL_TEST_001',
                'product_info': {
                    'product_name': '젠트레이드 실제 테스트 상품',
                    'price': 25000,
                    'test_time': datetime.now().isoformat()
                }
            },
            {
                'supplier': 'ownerclan',
                'product_code': 'OC_REAL_TEST_001',
                'product_info': {
                    'product_name': '오너클랜 실제 테스트 상품',
                    'price': 35000,
                    'test_time': datetime.now().isoformat()
                }
            },
            {
                'supplier': 'domeggook',
                'product_code': 'DG_REAL_TEST_001',
                'product_info': {
                    'product_name': '도매꾹 실제 테스트 상품',
                    'price': 15000,
                    'test_time': datetime.now().isoformat()
                }
            }
        ]
        
        for product_data in test_products:
            # 기존 상품 확인
            existing = db.query(Product).filter(
                Product.product_code == product_data['product_code']
            ).first()
            
            if existing:
                existing.product_info = product_data['product_info']
                existing.updated_at = datetime.now()
                print(f"[UPDATE] {product_data['product_code']}")
            else:
                product = Product(
                    product_code=product_data['product_code'],
                    product_info=product_data['product_info'],
                    supplier=product_data['supplier']
                )
                db.add(product)
                print(f"[INSERT] {product_data['product_code']}")
        
        db.commit()
        print("\n[SUCCESS] 데이터베이스 저장 완료!")
        
        # 저장된 데이터 확인
        count = db.query(Product).filter(
            Product.product_code.like('%_REAL_TEST_%')
        ).count()
        print(f"실제 테스트 상품 수: {count}개")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 데이터베이스 저장 중 오류: {e}")
        
    finally:
        db.close()

def check_api_settings():
    """API 설정 확인"""
    print("=== API 설정 확인 ===")
    print("\n현재 설정된 API 키:")
    
    # 젠트레이드
    if settings.ZENTRADE_API_ID:
        print(f"[O] 젠트레이드 API ID: {settings.ZENTRADE_API_ID[:10]}...")
    else:
        print("[X] 젠트레이드 API ID: 미설정")
    
    # 오너클랜
    if settings.OWNERCLAN_USERNAME:
        print(f"[O] 오너클랜 Username: {settings.OWNERCLAN_USERNAME}")
    else:
        print("[X] 오너클랜 Username: 미설정")
    
    # 도매꾹
    if settings.DOMEGGOOK_API_KEY:
        print(f"[O] 도매꾹 API Key: {settings.DOMEGGOOK_API_KEY[:10]}...")
    else:
        print("[X] 도매꾹 API Key: 미설정")
    
    print("\n.env 파일에 API 키를 설정하려면:")
    print("1. .env.example 파일을 복사하여 .env 파일 생성")
    print("2. 각 도매처에서 발급받은 API 키 입력")
    print("3. 이 스크립트를 다시 실행")

def main():
    """메인 함수"""
    print("실제 API 키 연동 테스트")
    print("=" * 50)
    
    # API 설정 확인
    check_api_settings()
    
    # 데이터베이스 초기화
    print("\n데이터베이스 초기화...")
    create_tables()
    db = SessionLocal()
    init_suppliers(db)
    db.close()
    
    # 각 도매처 테스트
    results = {
        'zentrade': test_zentrade_real(),
        'ownerclan': test_ownerclan_real(),
        'domeggook': test_domeggook_real()
    }
    
    # 데이터베이스 저장 테스트
    if any(results.values()):
        save_to_database_test()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    for supplier, success in results.items():
        status = "성공" if success else "실패/스킵"
        print(f"  - {supplier}: {status}")
    
    success_count = sum(1 for v in results.values() if v)
    print(f"\n전체: {success_count}/3 성공")

if __name__ == "__main__":
    main()