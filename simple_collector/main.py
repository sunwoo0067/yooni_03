#!/usr/bin/env python3
"""
Simple Product Collector - MVP
단순화된 상품 수집 시스템 메인 실행파일
"""

import asyncio
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from utils.logger import app_logger
from database.connection import create_tables
from database.models import init_suppliers, Supplier
from database.connection import SessionLocal

def init_database():
    """데이터베이스 초기화"""
    try:
        app_logger.info("데이터베이스 초기화 시작")
        
        # 테이블 생성
        create_tables()
        app_logger.info("데이터베이스 테이블 생성 완료")
        
        # 기본 공급사 데이터 초기화
        db = SessionLocal()
        try:
            init_suppliers(db)
            app_logger.info("기본 공급사 데이터 초기화 완료")
            
            # 공급사 목록 출력
            suppliers = db.query(Supplier).all()
            app_logger.info(f"등록된 공급사: {len(suppliers)}개")
            for supplier in suppliers:
                app_logger.info(f"  - {supplier.supplier_name} ({supplier.supplier_code})")
                
        finally:
            db.close()
            
    except Exception as e:
        app_logger.error(f"데이터베이스 초기화 실패: {e}")
        return False
        
    return True

def start_api_server():
    """API 서버 시작"""
    try:
        import uvicorn
        app_logger.info("API 서버 시작")
        
        uvicorn.run(
            "api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except Exception as e:
        app_logger.error(f"API 서버 시작 실패: {e}")

def test_collectors():
    """수집기 기능 테스트"""
    app_logger.info("=== 수집기 기능 테스트 시작 ===")
    
    # 1. 젠트레이드 테스트
    try:
        from collectors.zentrade_collector_simple import ZentradeCollector
        
        app_logger.info("1. 젠트레이드 수집기 테스트")
        
        # 테스트용 더미 인증 정보
        zentrade_credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        zentrade_collector = ZentradeCollector(zentrade_credentials)
        
        app_logger.info(f"  - 공급사명: {zentrade_collector.supplier_name}")
        app_logger.info(f"  - 공급사 코드: {zentrade_collector.supplier_code}")
        
        # 인증 테스트
        auth_result = zentrade_collector.authenticate()
        app_logger.info(f"  - 인증 결과: {auth_result}")
        
        if auth_result:
            # 상품 수집 테스트
            app_logger.info("  - 상품 수집 테스트...")
            product_count = 0
            for product in zentrade_collector.collect_products():
                product_count += 1
                if product_count <= 3:  # 처음 3개만 로그 출력
                    app_logger.info(f"    수집된 상품: {product.product_code} - {product.product_info.get('product_name', 'N/A')}")
            app_logger.info(f"  - 총 수집된 상품: {product_count}개")
        
    except Exception as e:
        app_logger.error(f"젠트레이드 테스트 오류: {e}")
    
    # 2. 오너클랜 테스트  
    try:
        from collectors.ownerclan_collector_simple import OwnerClanCollector
        
        app_logger.info("2. 오너클랜 수집기 테스트")
        
        # 테스트용 더미 인증 정보
        ownerclan_credentials = {
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        }
        
        ownerclan_collector = OwnerClanCollector(ownerclan_credentials)
        
        app_logger.info(f"  - 공급사명: {ownerclan_collector.supplier_name}")
        app_logger.info(f"  - 공급사 코드: {ownerclan_collector.supplier_code}")
        
        # 인증 테스트
        auth_result = ownerclan_collector.authenticate()
        app_logger.info(f"  - 인증 결과: {auth_result}")
        
        if auth_result:
            # 상품 수집 테스트
            app_logger.info("  - 2단계 상품 수집 테스트...")
            product_count = 0
            for product in ownerclan_collector.collect_products():
                product_count += 1
                if product_count <= 3:  # 처음 3개만 로그 출력
                    app_logger.info(f"    수집된 상품: {product.product_code} - {product.product_info.get('product_name', 'N/A')}")
            app_logger.info(f"  - 총 수집된 상품: {product_count}개")
            app_logger.info(f"  - 캐시된 코드: {len(ownerclan_collector._cached_codes)}개")
        
    except Exception as e:
        app_logger.error(f"오너클랜 테스트 오류: {e}")
    
    app_logger.info("=== 수집기 기능 테스트 완료 ===")

def show_menu():
    """메뉴 출력"""
    print("\n" + "="*50)
    print("Simple Product Collector - MVP")
    print("="*50)
    print("1. 데이터베이스 초기화")
    print("2. API 서버 시작")
    print("3. 수집기 기능 테스트")
    print("4. 전체 시스템 테스트")
    print("0. 종료")
    print("="*50)

def main():
    """메인 함수"""
    app_logger.info("Simple Product Collector MVP 시작")
    
    while True:
        show_menu()
        
        try:
            choice = input("선택하세요 (0-4): ").strip()
            
            if choice == "0":
                app_logger.info("프로그램을 종료합니다")
                break
                
            elif choice == "1":
                init_database()
                
            elif choice == "2":
                start_api_server()
                
            elif choice == "3":
                test_collectors()
                
            elif choice == "4":
                app_logger.info("전체 시스템 테스트 시작")
                if init_database():
                    test_collectors()
                    app_logger.info("전체 시스템 테스트 완료")
                    
            else:
                print("잘못된 선택입니다. 0-4 사이의 숫자를 입력하세요.")
                
        except KeyboardInterrupt:
            app_logger.info("사용자에 의해 중단되었습니다")
            break
        except Exception as e:
            app_logger.error(f"오류 발생: {e}")

if __name__ == "__main__":
    main()