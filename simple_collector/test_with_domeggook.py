#!/usr/bin/env python3
"""
도매꾹 수집기를 포함한 전체 테스트
"""

import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from utils.logger import app_logger
from database.connection import SessionLocal
from database.models import Product
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector

def test_all_collectors():
    """모든 수집기 테스트"""
    print("=== 전체 수집기 테스트 ===")
    print()
    
    collectors_config = [
        {
            'name': '젠트레이드',
            'class': ZentradeCollector,
            'credentials': {
                'api_id': 'test_id',
                'api_key': 'test_key',
                'base_url': 'https://www.zentrade.co.kr/shop/proc'
            }
        },
        {
            'name': '오너클랜',
            'class': OwnerClanCollector,
            'credentials': {
                'username': 'test_user',
                'password': 'test_password',
                'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
                'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
            }
        },
        {
            'name': '도매꾹',
            'class': DomeggookCollector,
            'credentials': {
                'api_key': 'test_key',
                'base_url': 'https://openapi.domeggook.com'
            }
        }
    ]
    
    total_products = 0
    db = SessionLocal()
    
    try:
        for config in collectors_config:
            print(f"### {config['name']} 수집기 테스트 ###")
            
            # 수집기 초기화
            collector = config['class'](config['credentials'])
            
            # 인증
            if collector.authenticate():
                print(f"[OK] {config['name']} 인증 성공")
                
                # 상품 수집 및 저장
                product_count = 0
                for product_data in collector.collect_products():
                    # DB에 저장
                    existing = db.query(Product).filter(
                        Product.product_code == product_data.product_code
                    ).first()
                    
                    if existing:
                        existing.product_info = product_data.product_info
                    else:
                        new_product = Product(
                            product_code=product_data.product_code,
                            product_info=product_data.product_info,
                            supplier=product_data.supplier
                        )
                        db.add(new_product)
                    
                    product_count += 1
                    
                    # 처음 2개만 출력
                    if product_count <= 2:
                        print(f"  > {product_data.product_code}: {product_data.product_info.get('product_name', 'N/A')}")
                
                db.commit()
                
                print(f"[OK] {config['name']}: {product_count}개 상품 수집 완료")
                total_products += product_count
                
            else:
                print(f"[FAIL] {config['name']} 인증 실패")
            
            print()
        
        # 최종 통계
        print("=== 수집 결과 통계 ===")
        
        # 공급사별 상품 수
        for supplier_code in ['zentrade', 'ownerclan', 'domeggook']:
            count = db.query(Product).filter(Product.supplier == supplier_code).count()
            print(f"- {supplier_code}: {count}개")
        
        total_count = db.query(Product).count()
        print(f"\n총 상품 수: {total_count}개")
        
        # 최근 수집 상품 샘플
        print("\n최근 수집 상품 (5개):")
        recent_products = db.query(Product).order_by(Product.created_at.desc()).limit(5).all()
        for product in recent_products:
            info = product.product_info
            print(f"  - [{product.supplier}] {product.product_code}: {info.get('product_name', 'N/A')}")
            if 'category_name' in info:
                print(f"    카테고리: {info.get('category_name')}")
        
    except Exception as e:
        print(f"[ERROR] 테스트 중 오류 발생: {e}")
        db.rollback()
        
    finally:
        db.close()

def test_domeggook_categories():
    """도매꾹 카테고리 기반 수집 테스트"""
    print("\n=== 도매꾹 카테고리 구조 테스트 ===")
    
    try:
        from collectors.domeggook_collector_simple import DomeggookCollector
        
        credentials = {
            'api_key': 'test_key',
            'base_url': 'https://openapi.domeggook.com'
        }
        
        collector = DomeggookCollector(credentials)
        
        # 테스트 카테고리 확인
        categories = collector._get_test_categories()
        print(f"전체 카테고리 수: {len(categories)}개")
        
        # 중분류 필터링 테스트
        middle_categories = collector._filter_middle_categories(categories)
        print(f"중분류 카테고리 수: {len(middle_categories)}개")
        
        print("\n중분류 카테고리 목록:")
        for cat_code in middle_categories:
            cat_name = collector._get_category_name(cat_code)
            print(f"  - {cat_code}: {cat_name}")
        
    except Exception as e:
        print(f"[ERROR] 카테고리 테스트 실패: {e}")

def main():
    """메인 테스트 함수"""
    print("Simple Product Collector - 통합 테스트")
    print("=" * 50)
    
    # 1. 모든 수집기 테스트
    test_all_collectors()
    
    # 2. 도매꾹 카테고리 구조 테스트
    test_domeggook_categories()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] 모든 테스트 완료!")

if __name__ == "__main__":
    main()