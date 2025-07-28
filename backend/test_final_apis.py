#!/usr/bin/env python3
"""
최종 API 테스트 - 실제 상품 수집
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


async def test_ownerclan_simple():
    """오너클랜 간단한 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 간단한 테스트")
    print("=" * 60)
    
    import aiohttp
    
    # 1. 인증
    username = os.getenv('OWNERCLAN_USERNAME')
    password = os.getenv('OWNERCLAN_PASSWORD')
    
    auth_url = 'https://auth.ownerclan.com/auth'
    auth_data = {
        "service": "ownerclan",
        "userType": "seller",
        "username": username,
        "password": password
    }
    
    async with aiohttp.ClientSession() as session:
        # 인증
        async with session.post(auth_url, json=auth_data) as response:
            if response.status == 200:
                token = await response.text()
                token = token.strip()
                print(f"✓ 토큰 발급 성공")
            else:
                print(f"✗ 인증 실패: {response.status}")
                return None
                
        # 2. 상품 조회
        api_url = 'https://api.ownerclan.com/v1/graphql'
        query = """
        query GetAllItems($first: Int) {
            allItems(first: $first) {
                edges {
                    node {
                        key
                        name
                        price
                        status
                    }
                }
            }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        payload = {
            'query': query,
            'variables': {'first': 5}
        }
        
        async with session.post(api_url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                if 'errors' in data:
                    print(f"✗ GraphQL 오류: {data['errors']}")
                    return None
                    
                products = []
                edges = data.get('data', {}).get('allItems', {}).get('edges', [])
                
                for edge in edges:
                    node = edge.get('node', {})
                    products.append({
                        'id': node.get('key'),
                        'name': node.get('name'),
                        'price': node.get('price'),
                        'status': node.get('status')
                    })
                    
                print(f"✓ {len(products)}개 상품 조회 성공")
                return products
            else:
                print(f"✗ API 호출 실패: {response.status}")
                return None


async def test_zentrade_simple():
    """젠트레이드 간단한 테스트"""
    print("\n" + "=" * 60)
    print("젠트레이드 간단한 테스트")
    print("=" * 60)
    
    import aiohttp
    import xml.etree.ElementTree as ET
    
    api_id = os.getenv('ZENTRADE_API_KEY')
    api_secret = os.getenv('ZENTRADE_API_SECRET')
    
    url = "https://www.zentrade.co.kr/shop/proc/product_api.php"
    params = {
        'id': api_id,
        'm_skey': api_secret
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                
                # EUC-KR 디코딩
                try:
                    xml_content = content.decode('euc-kr')
                    root = ET.fromstring(xml_content)
                    
                    if root.tag == 'zentrade':
                        products = []
                        product_elements = root.findall('product')
                        
                        for product in product_elements[:5]:  # 처음 5개만
                            code = product.get('code')
                            name_elem = product.find('prdtname')
                            price_elem = product.find('price')
                            
                            products.append({
                                'id': code,
                                'name': name_elem.text.strip() if name_elem is not None else '',
                                'price': int(price_elem.get('buyprice', 0)) if price_elem is not None else 0
                            })
                            
                        print(f"✓ {len(products)}개 상품 조회 성공 (전체: {len(product_elements)}개)")
                        return products
                        
                except Exception as e:
                    print(f"✗ XML 파싱 오류: {e}")
                    return None
            else:
                print(f"✗ API 호출 실패: {response.status}")
                return None


async def main():
    """메인 함수"""
    print("최종 API 테스트")
    print("실행 시간:", datetime.now())
    
    results = {}
    
    # 오너클랜 테스트
    ownerclan_products = await test_ownerclan_simple()
    if ownerclan_products:
        print("\n오너클랜 상품 샘플:")
        for p in ownerclan_products[:3]:
            print(f"  - [{p['id']}] {p['name']} ({p['price']}원)")
        results['ownerclan'] = {
            'status': 'success',
            'count': len(ownerclan_products),
            'products': ownerclan_products
        }
    else:
        results['ownerclan'] = {'status': 'failed'}
    
    # 젠트레이드 테스트
    zentrade_products = await test_zentrade_simple()
    if zentrade_products:
        print("\n젠트레이드 상품 샘플:")
        for p in zentrade_products[:3]:
            print(f"  - [{p['id']}] {p['name']} ({p['price']}원)")
        results['zentrade'] = {
            'status': 'success',
            'count': len(zentrade_products),
            'products': zentrade_products
        }
    else:
        results['zentrade'] = {'status': 'failed'}
    
    # 결과 저장
    filename = f'final_api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일: {filename}")
    
    # 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"오너클랜: {results['ownerclan']['status']}")
    if results['ownerclan']['status'] == 'success':
        print(f"  - 상품 수: {results['ownerclan']['count']}")
    print(f"젠트레이드: {results['zentrade']['status']}")
    if results['zentrade']['status'] == 'success':
        print(f"  - 상품 수: {results['zentrade']['count']}")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())