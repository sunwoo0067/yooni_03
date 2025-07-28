#!/usr/bin/env python3
"""
업데이트된 API 키로 도매처 실제 테스트
"""

import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import hmac

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


async def test_ownerclan():
    """오너클랜 API 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 API 테스트")
    print("=" * 60)
    
    username = os.getenv("OWNERCLAN_USERNAME")
    password = os.getenv("OWNERCLAN_PASSWORD")
    
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'Not set'}")
    
    # 오너클랜은 주로 웹 스크래핑 방식
    # 로그인이 필요한 경우
    async with aiohttp.ClientSession() as session:
        # 로그인 시도
        login_url = "https://www.ownerclan.com/V2/member/login_ok.php"
        
        login_data = {
            'member_id': username,
            'member_passwd': password,
            'save_id': 'N'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.ownerclan.com/V2/member/login.php'
        }
        
        try:
            # 로그인
            async with session.post(login_url, data=login_data, headers=headers, allow_redirects=False) as response:
                print(f"로그인 응답 코드: {response.status}")
                
                if response.status in [302, 303]:  # 리다이렉트는 성공
                    print("✓ 로그인 성공 (리다이렉트)")
                    
                    # 쿠키 확인
                    cookies = response.cookies
                    if cookies:
                        print(f"쿠키 수: {len(cookies)}")
                    
                    # 상품 검색
                    search_url = "https://www.ownerclan.com/V2/product/search.php"
                    search_params = {'sw': '이어폰', 'page': 1}
                    
                    async with session.get(search_url, params=search_params, headers=headers) as search_response:
                        print(f"\n상품 검색 응답: {search_response.status}")
                        if search_response.status == 200:
                            html = await search_response.text()
                            print(f"검색 결과 크기: {len(html)} bytes")
                            
                            # 간단한 상품 수 확인
                            if '상품' in html:
                                print("✓ 상품 검색 성공")
                        
                elif response.status == 200:
                    html = await response.text()
                    if '로그인' in html and '실패' in html:
                        print("✗ 로그인 실패")
                    else:
                        print("? 알 수 없는 응답")
                        
        except Exception as e:
            print(f"오류: {e}")


async def test_domeggook():
    """도매꾹 API 테스트"""
    print("\n" + "=" * 60)
    print("도매꾹 API 테스트")
    print("=" * 60)
    
    api_key = os.getenv("DOMEGGOOK_API_KEY")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'Not set'}")
    
    async with aiohttp.ClientSession() as session:
        # 도매꾹 오픈API
        base_url = "https://www.domeggook.com/openapi"
        
        # 카테고리 조회
        params = {
            'service': 'getCategoryList',
            'key': api_key,
            'method': 'json'
        }
        
        try:
            async with session.get(base_url, params=params) as response:
                print(f"\n카테고리 조회 응답: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, dict) and 'CategoryList' in data:
                        categories = data['CategoryList']
                        print(f"✓ 카테고리 수: {len(categories)}")
                        
                        # 첫 번째 카테고리 출력
                        if categories:
                            print(f"첫 번째 카테고리: {categories[0]}")
                    else:
                        print(f"응답 데이터: {data}")
                        
            # 상품 검색
            search_params = {
                'service': 'getProductSearch',
                'key': api_key,
                'method': 'json',
                'keyword': '이어폰',
                'page': 1,
                'limit': 10
            }
            
            async with session.get(base_url, params=search_params) as response:
                print(f"\n상품 검색 응답: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, dict) and 'ProductList' in data:
                        products = data['ProductList']
                        print(f"✓ 검색된 상품 수: {len(products)}")
                        
                        # 첫 번째 상품 출력
                        if products:
                            product = products[0]
                            print(f"\n첫 번째 상품:")
                            print(f"  - 이름: {product.get('ProductName', 'N/A')}")
                            print(f"  - 가격: {product.get('Price', 0)}원")
                    else:
                        print(f"응답 데이터: {data}")
                        
        except Exception as e:
            print(f"오류: {e}")


async def test_zentrade():
    """젠트레이드 API 테스트"""
    print("\n" + "=" * 60)
    print("젠트레이드 API 테스트")
    print("=" * 60)
    
    api_key = os.getenv("ZENTRADE_API_KEY")
    api_secret = os.getenv("ZENTRADE_API_SECRET")
    
    print(f"API Key: {api_key}")
    print(f"API Secret: {'*' * 10 if api_secret else 'Not set'}")
    
    async with aiohttp.ClientSession() as session:
        # 젠트레이드 API (실제 엔드포인트 확인 필요)
        base_url = "https://api.zentrade.co.kr"  # 추정 URL
        
        # API 서명 생성 (HMAC-SHA256)
        timestamp = str(int(datetime.now().timestamp()))
        message = f"{api_key}{timestamp}"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-API-KEY': api_key,
            'X-TIMESTAMP': timestamp,
            'X-SIGNATURE': signature,
            'Content-Type': 'application/json'
        }
        
        # 테스트 엔드포인트 (추정)
        endpoints = [
            '/api/v1/categories',
            '/api/v1/products',
            '/api/categories',
            '/api/products',
            '/v1/categories',
            '/v1/products'
        ]
        
        for endpoint in endpoints:
            try:
                url = base_url + endpoint
                print(f"\n테스트: {url}")
                
                async with session.get(url, headers=headers, timeout=5) as response:
                    print(f"응답 코드: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ 성공: {endpoint}")
                        print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                        break
                    elif response.status == 401:
                        print("✗ 인증 실패")
                    elif response.status == 404:
                        print("✗ 엔드포인트 없음")
                        
            except asyncio.TimeoutError:
                print("✗ 타임아웃")
            except Exception as e:
                print(f"✗ 오류: {e}")


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("도매처 API 실제 테스트")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    # 환경 변수 확인
    print("\n환경 변수 상태:")
    print(f"- OWNERCLAN_USERNAME: {'설정됨' if os.getenv('OWNERCLAN_USERNAME') else '미설정'}")
    print(f"- OWNERCLAN_PASSWORD: {'설정됨' if os.getenv('OWNERCLAN_PASSWORD') else '미설정'}")
    print(f"- DOMEGGOOK_API_KEY: {'설정됨' if os.getenv('DOMEGGOOK_API_KEY') else '미설정'}")
    print(f"- ZENTRADE_API_KEY: {'설정됨' if os.getenv('ZENTRADE_API_KEY') else '미설정'}")
    print(f"- ZENTRADE_API_SECRET: {'설정됨' if os.getenv('ZENTRADE_API_SECRET') else '미설정'}")
    
    # 각 도매처 테스트
    await test_ownerclan()
    await test_domeggook()
    await test_zentrade()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())