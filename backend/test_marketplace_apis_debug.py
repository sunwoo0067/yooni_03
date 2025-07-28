#!/usr/bin/env python3
"""
마켓플레이스 API 디버깅 테스트
"""

import os
import sys
import asyncio
import json
import hmac
import hashlib
import time
import urllib.parse
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


async def test_coupang_api_debug():
    """쿠팡 API 디버깅 테스트"""
    print("\n" + "=" * 60)
    print("쿠팡 API 디버깅 테스트")
    print("=" * 60)
    
    try:
        import httpx
        
        # API 자격증명
        access_key = os.getenv('COUPANG_ACCESS_KEY')
        secret_key = os.getenv('COUPANG_SECRET_KEY')
        vendor_id = os.getenv('COUPANG_VENDOR_ID')
        
        print(f"Access Key: {access_key}")
        print(f"Secret Key: {secret_key[:10]}...")
        print(f"Vendor ID: {vendor_id}")
        
        # HMAC 서명 생성
        method = "GET"
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        query = f"vendorId={vendor_id}&limit=1"
        
        datetime_str = time.strftime('%y%m%d')
        datetime_time = time.strftime('T%H%M%SZ')
        datetime_now = datetime_str + datetime_time
        
        message = datetime_now + method + path + query
        print(f"\n서명 메시지: {message}")
        
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"서명: {signature}")
        
        headers = {
            "Authorization": f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_now}, signature={signature}",
            "Content-Type": "application/json;charset=UTF-8"
        }
        
        print(f"\n헤더: {json.dumps(headers, indent=2)}")
        
        # API 호출
        url = f"https://api-gateway.coupang.com{path}?{query}"
        print(f"\nURL: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            print(f"\n응답 상태: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✓ API 호출 성공")
                data = response.json()
                print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ API 호출 실패")
                print(f"응답 본문: {response.text}")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


async def test_11st_api_debug():
    """11번가 API 디버깅 테스트"""
    print("\n" + "=" * 60)
    print("11번가 API 디버깅 테스트")
    print("=" * 60)
    
    try:
        import httpx
        import xml.etree.ElementTree as ET
        
        # API 자격증명
        api_key = os.getenv('ELEVENTH_STREET_API_KEY')
        seller_id = os.getenv('ELEVENTH_STREET_SELLER_ID')
        
        print(f"API Key: {api_key}")
        print(f"Seller ID: {seller_id}")
        
        # API 호출
        url = "https://api.11st.co.kr/rest/prodservices/product"
        headers = {
            "openapikey": api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        params = {
            "page": 1,
            "limit": 1,
            "sellerId": seller_id
        }
        
        print(f"\nURL: {url}")
        print(f"헤더: {json.dumps(headers, indent=2)}")
        print(f"파라미터: {json.dumps(params, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            
            print(f"\n응답 상태: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✓ API 호출 성공")
                print(f"응답 본문:\n{response.text[:500]}...")
                
                # XML 파싱 시도
                try:
                    root = ET.fromstring(response.text)
                    print(f"\nXML 루트 태그: {root.tag}")
                    
                    # 에러 메시지 확인
                    error_code = root.find('.//ErrorCode')
                    error_msg = root.find('.//ErrorMessage')
                    
                    if error_code is not None:
                        print(f"API 에러 코드: {error_code.text}")
                        print(f"API 에러 메시지: {error_msg.text if error_msg is not None else 'N/A'}")
                    else:
                        # 상품 데이터 확인
                        products = root.findall('.//Product')
                        print(f"상품 수: {len(products)}")
                        
                except Exception as e:
                    print(f"XML 파싱 오류: {e}")
            else:
                print(f"✗ API 호출 실패")
                print(f"응답 본문: {response.text}")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


async def test_marketplace_simple():
    """간단한 마켓플레이스 API 테스트"""
    print("\n" + "=" * 60)
    print("간단한 마켓플레이스 API 연동 테스트")
    print("=" * 60)
    
    # 샘플 데이터로 마켓플레이스 연동 시뮬레이션
    marketplace_products = {
        'coupang': [
            {
                'id': 'CP001',
                'name': '쿠팡 테스트 상품 1',
                'price': 25000,
                'stock': 100,
                'status': 'ACTIVE'
            },
            {
                'id': 'CP002',
                'name': '쿠팡 테스트 상품 2',
                'price': 35000,
                'stock': 50,
                'status': 'ACTIVE'
            }
        ],
        'naver': [
            {
                'id': 'NV001',
                'name': '네이버 테스트 상품 1',
                'price': 28000,
                'stock': 80,
                'status': 'SALE'
            },
            {
                'id': 'NV002',
                'name': '네이버 테스트 상품 2',
                'price': 42000,
                'stock': 30,
                'status': 'SALE'
            }
        ],
        '11st': [
            {
                'id': '11ST001',
                'name': '11번가 테스트 상품 1',
                'price': 32000,
                'stock': 60,
                'status': 'SELLING'
            },
            {
                'id': '11ST002',
                'name': '11번가 테스트 상품 2',
                'price': 48000,
                'stock': 20,
                'status': 'SELLING'
            }
        ]
    }
    
    print("\n마켓플레이스별 상품 현황:")
    for marketplace, products in marketplace_products.items():
        print(f"\n[{marketplace}]")
        for product in products:
            print(f"  - {product['name']} ({product['price']:,}원, 재고: {product['stock']})")
    
    # 결과 저장
    with open('marketplace_sample_data.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'marketplaces': marketplace_products,
            'summary': {
                'coupang': len(marketplace_products['coupang']),
                'naver': len(marketplace_products['naver']),
                '11st': len(marketplace_products['11st']),
                'total': sum(len(products) for products in marketplace_products.values())
            }
        }, f, ensure_ascii=False, indent=2)
    
    print("\n샘플 데이터가 marketplace_sample_data.json에 저장되었습니다.")


async def main():
    """메인 함수"""
    print("마켓플레이스 API 디버깅 테스트")
    print("실행 시간:", datetime.now())
    
    # 쿠팡 디버깅
    await test_coupang_api_debug()
    
    # 11번가 디버깅
    await test_11st_api_debug()
    
    # 간단한 테스트
    await test_marketplace_simple()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    print("\n참고: 실제 마켓플레이스 API 연동을 위해서는:")
    print("1. 쿠팡: 파트너스 승인 및 올바른 API 키 필요")
    print("2. 네이버: OAuth 인증 절차 필요")
    print("3. 11번가: 판매자 승인 및 API 키 활성화 필요")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())