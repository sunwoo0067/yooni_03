#!/usr/bin/env python3
"""
도매처 API 간단 테스트
환경 변수나 하드코딩된 값으로 빠르게 테스트
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_ownerclan_web():
    """오너클랜 웹 스크래핑 테스트"""
    print("\n[오너클랜 웹 테스트]")
    
    async with aiohttp.ClientSession() as session:
        # 상품 검색 페이지
        search_url = "https://www.ownerclan.com/V2/product/search.php"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        params = {
            'sw': '이어폰',  # 검색어
            'page': 1
        }
        
        try:
            async with session.get(search_url, params=params, headers=headers) as response:
                print(f"상태 코드: {response.status}")
                
                if response.status == 200:
                    # HTML 파싱이 필요하지만, 간단히 응답 크기만 확인
                    html = await response.text()
                    print(f"응답 크기: {len(html)} bytes")
                    
                    # 상품이 있는지 간단히 확인
                    if 'product-item' in html or '상품' in html:
                        print("✓ 상품 검색 결과가 있습니다.")
                    else:
                        print("✗ 상품을 찾을 수 없습니다.")
                else:
                    print(f"오류: HTTP {response.status}")
                    
        except Exception as e:
            print(f"오류: {e}")


async def test_domeggook_api():
    """도매꾹 API 테스트 (실제 API가 있다고 가정)"""
    print("\n[도매꾹 API 테스트]")
    
    # 도매꾹 테스트 API 키 (예시)
    api_key = "test-key"  # 실제 키가 필요
    
    async with aiohttp.ClientSession() as session:
        # 카테고리 목록 조회 (API가 있다고 가정)
        url = "https://api.domeggook.com/categories"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                print(f"상태 코드: {response.status}")
                
                if response.status == 401:
                    print("✗ 인증 실패 - API 키가 필요합니다.")
                elif response.status == 404:
                    print("✗ API 엔드포인트를 찾을 수 없습니다.")
                elif response.status == 200:
                    data = await response.json()
                    print(f"✓ 성공: {data}")
                    
        except aiohttp.ClientError as e:
            print(f"연결 오류: {e}")
        except Exception as e:
            print(f"오류: {e}")


async def test_zentrade_web():
    """젠트레이드 웹 테스트"""
    print("\n[젠트레이드 웹 테스트]")
    
    async with aiohttp.ClientSession() as session:
        # 젠트레이드 홈페이지
        url = "https://www.zentrade.co.kr"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                print(f"상태 코드: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    print(f"응답 크기: {len(html)} bytes")
                    print("✓ 웹사이트 접속 가능")
                else:
                    print(f"✗ 접속 실패: HTTP {response.status}")
                    
        except Exception as e:
            print(f"오류: {e}")


async def test_sample_graphql():
    """GraphQL API 테스트 샘플"""
    print("\n[GraphQL API 테스트 샘플]")
    
    # GraphQL 쿼리
    query = """
    query TestQuery {
        products(first: 5) {
            edges {
                node {
                    id
                    name
                    price
                }
            }
        }
    }
    """
    
    # 샘플 GraphQL 엔드포인트 (httpbin.org의 POST 엔드포인트 사용)
    url = "https://httpbin.org/post"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                json={"query": query},
                headers={'Content-Type': 'application/json'}
            ) as response:
                print(f"상태 코드: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✓ GraphQL 요청 형식 테스트 성공")
                    print(f"요청 데이터: {data.get('json', {})}")
                    
        except Exception as e:
            print(f"오류: {e}")


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("도매처 API 간단 테스트")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    # 각 도매처 테스트
    await test_ownerclan_web()
    await test_domeggook_api()
    await test_zentrade_web()
    await test_sample_graphql()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
    
    print("\n[참고사항]")
    print("1. 오너클랜: 웹 스크래핑 또는 공식 API 파트너 신청 필요")
    print("2. 도매꾹: API 키 발급 필요")
    print("3. 젠트레이드: API 문서 확인 필요")
    print("\n실제 API 키가 있다면 .env 파일에 설정하고 기존 구현을 사용하세요.")


if __name__ == "__main__":
    asyncio.run(main())