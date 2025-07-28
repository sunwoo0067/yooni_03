#!/usr/bin/env python3
"""
Simple Product Collector 테스트 스크립트
"""

import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_database():
    """데이터베이스 테스트"""
    print("=== 데이터베이스 테스트 ===")
    
    try:
        from utils.logger import app_logger
        from database.connection import create_tables, SessionLocal
        from database.models import init_suppliers, Supplier
        
        print("1. 데이터베이스 테이블 생성...")
        create_tables()
        print("   [OK] 테이블 생성 완료")
        
        print("2. 기본 공급사 데이터 초기화...")
        db = SessionLocal()
        try:
            init_suppliers(db)
            suppliers = db.query(Supplier).all()
            print(f"   [OK] 공급사 {len(suppliers)}개 등록 완료")
            for supplier in suppliers:
                print(f"     - {supplier.supplier_name} ({supplier.supplier_code})")
        finally:
            db.close()
            
        print("데이터베이스 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"데이터베이스 테스트 실패: {e}")
        return False

def test_collectors():
    """수집기 테스트"""
    print("\n=== 수집기 테스트 ===")
    
    # 1. 젠트레이드 테스트
    print("1. 젠트레이드 수집기 테스트")
    try:
        from collectors.zentrade_collector_simple import ZentradeCollector
        
        zentrade_credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        collector = ZentradeCollector(zentrade_credentials)
        print(f"   - 공급사명: {collector.supplier_name}")
        print(f"   - 공급사 코드: {collector.supplier_code}")
        
        # 인증 테스트
        auth_result = collector.authenticate()
        print(f"   - 인증 결과: {'성공' if auth_result else '실패'}")
        
        if auth_result:
            print("   - 상품 수집 테스트...")
            product_count = 0
            for product in collector.collect_products():
                product_count += 1
                if product_count <= 3:
                    print(f"     > 상품: {product.product_code} - {product.product_info.get('product_name', 'N/A')}")
            print(f"   [OK] 총 {product_count}개 상품 수집 완료")
        
    except Exception as e:
        print(f"   [ERROR] 젠트레이드 테스트 실패: {e}")
    
    # 2. 오너클랜 테스트
    print("\n2. 오너클랜 수집기 테스트")
    try:
        from collectors.ownerclan_collector_simple import OwnerClanCollector
        
        ownerclan_credentials = {
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        }
        
        collector = OwnerClanCollector(ownerclan_credentials)
        print(f"   - 공급사명: {collector.supplier_name}")
        print(f"   - 공급사 코드: {collector.supplier_code}")
        
        # 인증 테스트
        auth_result = collector.authenticate()
        print(f"   - 인증 결과: {'성공' if auth_result else '실패'}")
        
        if auth_result:
            print("   - 2단계 상품 수집 테스트...")
            product_count = 0
            for product in collector.collect_products():
                product_count += 1
                if product_count <= 3:
                    print(f"     > 상품: {product.product_code} - {product.product_info.get('product_name', 'N/A')}")
            print(f"   [OK] 총 {product_count}개 상품 수집 완료")
            print(f"   [OK] 캐시된 코드: {len(collector._cached_codes)}개")
        
    except Exception as e:
        print(f"   [ERROR] 오너클랜 테스트 실패: {e}")
    
    print("수집기 테스트 완료!")

def test_database_save():
    """데이터베이스 저장 테스트"""
    print("\n=== 데이터베이스 저장 테스트 ===")
    
    try:
        from database.connection import SessionLocal
        from database.models import Product
        from collectors.zentrade_collector_simple import ZentradeCollector
        
        # 젠트레이드에서 데이터 수집
        zentrade_credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        collector = ZentradeCollector(zentrade_credentials)
        
        if collector.authenticate():
            db = SessionLocal()
            try:
                saved_count = 0
                
                for product_data in collector.collect_products():
                    # 기존 상품 확인
                    existing = db.query(Product).filter(
                        Product.product_code == product_data.product_code
                    ).first()
                    
                    if existing:
                        # 업데이트
                        existing.product_info = product_data.product_info
                        print(f"   [UPDATE] 상품 업데이트: {product_data.product_code}")
                    else:
                        # 신규 저장
                        new_product = Product(
                            product_code=product_data.product_code,
                            product_info=product_data.product_info,
                            supplier=product_data.supplier
                        )
                        db.add(new_product)
                        print(f"   [NEW] 신규 상품 저장: {product_data.product_code}")
                    
                    saved_count += 1
                    
                    if saved_count >= 5:  # 5개만 테스트
                        break
                
                db.commit()
                
                # 저장된 데이터 확인
                total_products = db.query(Product).count()
                zentrade_products = db.query(Product).filter(Product.supplier == 'zentrade').count()
                
                print(f"   [OK] 총 {saved_count}개 상품 저장 완료")
                print(f"   [OK] 데이터베이스 총 상품: {total_products}개")
                print(f"   [OK] 젠트레이드 상품: {zentrade_products}개")
                
            finally:
                db.close()
        
    except Exception as e:
        print(f"   [ERROR] 데이터베이스 저장 테스트 실패: {e}")

def main():
    """메인 테스트 함수"""
    print("Simple Product Collector MVP - 테스트 실행")
    print("=" * 50)
    
    # 1. 데이터베이스 테스트
    if test_database():
        
        # 2. 수집기 테스트
        test_collectors()
        
        # 3. 데이터베이스 저장 테스트
        test_database_save()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] 모든 테스트 완료!")
        
        # 최종 확인
        try:
            from database.connection import SessionLocal
            from database.models import Product, Supplier
            
            db = SessionLocal()
            try:
                supplier_count = db.query(Supplier).count()
                product_count = db.query(Product).count()
                
                print(f"\n최종 상태:")
                print(f"- 등록된 공급사: {supplier_count}개")
                print(f"- 수집된 상품: {product_count}개")
                
                if product_count > 0:
                    print(f"\n최근 수집 상품 (상위 3개):")
                    recent_products = db.query(Product).order_by(Product.created_at.desc()).limit(3).all()
                    for product in recent_products:
                        print(f"  - {product.product_code}: {product.product_info.get('product_name', 'N/A')} ({product.supplier})")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"최종 확인 중 오류: {e}")
    
    else:
        print("[FAIL] 데이터베이스 테스트 실패로 전체 테스트 중단")

if __name__ == "__main__":
    main()