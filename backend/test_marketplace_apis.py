#!/usr/bin/env python3
"""
마켓플레이스 API 테스트
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


async def test_coupang_api():
    """쿠팡 API 테스트"""
    print("\n" + "=" * 60)
    print("쿠팡 API 테스트")
    print("=" * 60)
    
    try:
        from app.services.platforms.coupang_api import CoupangAPI
        
        # API 자격증명
        credentials = {
            "access_key": os.getenv('COUPANG_ACCESS_KEY'),
            "secret_key": os.getenv('COUPANG_SECRET_KEY'),
            "vendor_id": os.getenv('COUPANG_VENDOR_ID')
        }
        
        print(f"Access Key: {credentials['access_key'][:10]}...")
        print(f"Vendor ID: {credentials['vendor_id']}")
        
        async with CoupangAPI(credentials) as api:
            # 연결 테스트
            print("\n1. 연결 테스트...")
            connected = await api.test_connection()
            if connected:
                print("✓ 연결 성공")
            else:
                print("✗ 연결 실패")
                return False
            
            # 상품 목록 조회
            print("\n2. 상품 목록 조회...")
            try:
                products = await api.list_products(limit=5)
                print(f"✓ 상품 조회 성공")
                
                if 'data' in products and products['data']:
                    print(f"총 {len(products['data'])}개 상품 조회됨")
                    for i, product in enumerate(products['data'][:3], 1):
                        print(f"  {i}. {product.get('sellerProductName', 'N/A')}")
                else:
                    print("상품이 없습니다.")
                    
            except Exception as e:
                print(f"✗ 상품 조회 실패: {e}")
            
            # 최근 주문 조회
            print("\n3. 최근 주문 조회...")
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                orders = await api.get_orders(start_date, end_date)
                print(f"✓ 주문 조회 성공")
                
                if 'data' in orders and orders['data']:
                    print(f"최근 7일간 {len(orders['data'])}개 주문")
                else:
                    print("최근 주문이 없습니다.")
                    
            except Exception as e:
                print(f"✗ 주문 조회 실패: {e}")
            
            # 카테고리 조회
            print("\n4. 카테고리 조회...")
            try:
                categories = await api.get_categories()
                print(f"✓ 카테고리 조회 성공")
                
                if 'data' in categories and categories['data']:
                    print(f"총 {len(categories['data'])}개 카테고리")
                    
            except Exception as e:
                print(f"✗ 카테고리 조회 실패: {e}")
            
            return True
            
    except Exception as e:
        print(f"쿠팡 API 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_naver_api():
    """네이버 스마트스토어 API 테스트"""
    print("\n" + "=" * 60)
    print("네이버 스마트스토어 API 테스트")
    print("=" * 60)
    
    try:
        from app.services.platforms.naver_api import NaverAPI
        
        # API 자격증명
        credentials = {
            "client_id": os.getenv('NAVER_CLIENT_ID'),
            "client_secret": os.getenv('NAVER_CLIENT_SECRET'),
            "store_id": os.getenv('NAVER_STORE_ID')
        }
        
        print(f"Client ID: {credentials['client_id'][:10]}...")
        print(f"Store ID: {credentials['store_id']}")
        
        # 토큰이 없으므로 OAuth 인증이 필요함
        print("\n네이버 API는 OAuth 인증이 필요합니다.")
        print("실제 사용 시 OAuth 토큰을 먼저 발급받아야 합니다.")
        
        # 기본 연결 테스트만 수행
        async with NaverAPI(credentials) as api:
            print("\n1. API 초기화 성공")
            
            # 실제 API 호출은 access_token이 있어야 가능
            print("\n주의: 실제 API 호출을 위해서는 OAuth 인증 절차가 필요합니다.")
            print("1. 네이버 커머스 API 센터에서 앱 등록")
            print("2. OAuth 인증 URL로 사용자 인증")
            print("3. 발급받은 access_token과 refresh_token 사용")
            
        return True
            
    except Exception as e:
        print(f"네이버 API 오류: {e}")
        return False


async def test_11st_api():
    """11번가 API 테스트"""
    print("\n" + "=" * 60)
    print("11번가 API 테스트")
    print("=" * 60)
    
    try:
        from app.services.platforms.eleventh_street_api import EleventhStreetAPI
        
        # API 자격증명
        credentials = {
            "api_key": os.getenv('ELEVENTH_STREET_API_KEY'),
            "seller_id": os.getenv('ELEVENTH_STREET_SELLER_ID')
        }
        
        print(f"API Key: {credentials['api_key'][:10]}...")
        print(f"Seller ID: {credentials['seller_id']}")
        
        async with EleventhStreetAPI(credentials) as api:
            # 연결 테스트
            print("\n1. 연결 테스트...")
            connected = await api.test_connection()
            if connected:
                print("✓ 연결 성공")
            else:
                print("✗ 연결 실패")
                return False
            
            # 상품 목록 조회
            print("\n2. 상품 목록 조회...")
            try:
                products = await api.list_products(page=1, limit=5)
                print(f"✓ 상품 조회 성공")
                
                # XML 응답 처리
                if products and 'Product' in products:
                    product_list = products['Product']
                    if not isinstance(product_list, list):
                        product_list = [product_list]
                    
                    print(f"총 {len(product_list)}개 상품 조회됨")
                    for i, product in enumerate(product_list[:3], 1):
                        print(f"  {i}. {product.get('prdNm', 'N/A')}")
                else:
                    print("상품이 없습니다.")
                    
            except Exception as e:
                print(f"✗ 상품 조회 실패: {e}")
            
            # 최근 주문 조회
            print("\n3. 최근 주문 조회...")
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                orders = await api.get_orders(start_date, end_date)
                print(f"✓ 주문 조회 성공")
                
                if orders and 'Order' in orders:
                    order_list = orders['Order']
                    if not isinstance(order_list, list):
                        order_list = [order_list]
                    print(f"최근 7일간 {len(order_list)}개 주문")
                else:
                    print("최근 주문이 없습니다.")
                    
            except Exception as e:
                print(f"✗ 주문 조회 실패: {e}")
            
            # 배송회사 목록 조회
            print("\n4. 배송회사 목록 조회...")
            try:
                companies = await api.get_delivery_companies()
                print(f"✓ 배송회사 조회 성공")
                
                if companies and 'DeliveryCompany' in companies:
                    company_list = companies['DeliveryCompany']
                    if not isinstance(company_list, list):
                        company_list = [company_list]
                    print(f"총 {len(company_list)}개 배송회사")
                    
            except Exception as e:
                print(f"✗ 배송회사 조회 실패: {e}")
            
            return True
            
    except Exception as e:
        print(f"11번가 API 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 함수"""
    print("마켓플레이스 API 테스트")
    print("실행 시간:", datetime.now())
    
    results = {}
    
    # 쿠팡 테스트
    results['coupang'] = await test_coupang_api()
    
    # 네이버 테스트
    results['naver'] = await test_naver_api()
    
    # 11번가 테스트
    results['11st'] = await test_11st_api()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"쿠팡: {'성공' if results['coupang'] else '실패'}")
    print(f"네이버: {'OAuth 인증 필요' if results['naver'] else '실패'}")
    print(f"11번가: {'성공' if results['11st'] else '실패'}")
    
    # 결과 저장
    with open('marketplace_api_test_result.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'notes': {
                'naver': '네이버는 OAuth 인증이 필요하여 실제 API 호출은 테스트하지 못했습니다.',
                'coupang': '쿠팡 파트너스 API 연동',
                '11st': '11번가 오픈 API 연동'
            }
        }, f, ensure_ascii=False, indent=2)
    
    print("\n결과가 marketplace_api_test_result.json에 저장되었습니다.")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())