#!/usr/bin/env python3
"""
도매처 API 테스트 (수정 버전)
"""

import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


async def test_domeggook_correct():
    """도매꾹 API 테스트 (올바른 엔드포인트)"""
    print("\n" + "=" * 60)
    print("도매꾹 API 테스트 (수정 버전)")
    print("=" * 60)
    
    api_key = os.getenv("DOMEGGOOK_API_KEY")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    async with aiohttp.ClientSession() as session:
        # 도매꾹 올바른 API URL
        base_url = "http://api.domeggook.com/index.php"
        
        # 1. 카테고리 조회
        params = {
            'method': 'getCategoryList',
            'key': api_key,
            'output': 'json'
        }
        
        try:
            async with session.get(base_url, params=params) as response:
                print(f"\n1. 카테고리 조회")
                print(f"   URL: {response.url}")
                print(f"   상태 코드: {response.status}")
                
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                        if 'categories' in data:
                            categories = data['categories']
                            print(f"   [성공] 카테고리 수: {len(categories)}")
                            
                            # 첫 3개 카테고리 출력
                            for i, cat in enumerate(categories[:3]):
                                print(f"   - {cat.get('name', 'N/A')} (ID: {cat.get('id', 'N/A')})")
                        else:
                            print(f"   응답: {text[:200]}...")
                    except json.JSONDecodeError:
                        print(f"   JSON 파싱 실패: {text[:200]}...")
                        
        except Exception as e:
            print(f"   오류: {e}")
            
        # 2. 상품 검색
        params = {
            'method': 'getProductSearch',
            'key': api_key,
            'output': 'json',
            'q': '이어폰',
            'page': 1,
            'limit': 5
        }
        
        try:
            async with session.get(base_url, params=params) as response:
                print(f"\n2. 상품 검색 ('이어폰')")
                print(f"   URL: {response.url}")
                print(f"   상태 코드: {response.status}")
                
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                        if 'products' in data:
                            products = data['products']
                            print(f"   [성공] 검색된 상품 수: {len(products)}")
                            
                            # 첫 번째 상품 정보
                            if products:
                                product = products[0]
                                print(f"\n   첫 번째 상품:")
                                print(f"   - 이름: {product.get('name', 'N/A')}")
                                print(f"   - 가격: {product.get('price', 0):,}원")
                                print(f"   - 도매가: {product.get('wholesale_price', 0):,}원")
                        else:
                            print(f"   응답: {text[:200]}...")
                    except json.JSONDecodeError:
                        print(f"   JSON 파싱 실패: {text[:200]}...")
                        
        except Exception as e:
            print(f"   오류: {e}")


async def test_ownerclan_simple():
    """오너클랜 간단 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 웹 접속 테스트")
    print("=" * 60)
    
    username = os.getenv("OWNERCLAN_USERNAME")
    password = os.getenv("OWNERCLAN_PASSWORD")
    
    print(f"Username: {username}")
    print("Password: [숨김]")
    
    # 기존 구현 클래스 사용 테스트
    try:
        from app.services.wholesalers.ownerclan_api import OwnerClanAPI
        
        credentials = {
            'username': username,
            'password': password,
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',  # 샌드박스
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        }
        
        api = OwnerClanAPI(credentials)
        
        # 연결 테스트
        print("\n기존 구현 클래스로 테스트:")
        result = await api.test_connection()
        print(f"결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"오류: {e}")


async def test_zentrade_possible_urls():
    """젠트레이드 가능한 URL 테스트"""
    print("\n" + "=" * 60)
    print("젠트레이드 URL 찾기")
    print("=" * 60)
    
    # 가능한 도메인들
    domains = [
        "https://www.zentrade.co.kr",
        "http://www.zentrade.co.kr",
        "https://zentrade.co.kr",
        "https://api.zentrade.kr",
        "https://openapi.zentrade.co.kr"
    ]
    
    async with aiohttp.ClientSession() as session:
        for domain in domains:
            try:
                print(f"\n테스트: {domain}")
                async with session.get(domain, timeout=5) as response:
                    print(f"  상태: {response.status}")
                    if response.status == 200:
                        print("  [접속 가능]")
                        
                        # robots.txt 확인
                        robots_url = domain + "/robots.txt"
                        async with session.get(robots_url, timeout=3) as robots_response:
                            if robots_response.status == 200:
                                robots_text = await robots_response.text()
                                if 'api' in robots_text.lower():
                                    print("  API 경로가 있을 수 있음")
                                    
            except asyncio.TimeoutError:
                print("  [타임아웃]")
            except Exception as e:
                print(f"  [오류] {type(e).__name__}")


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("도매처 API 테스트 (수정 버전)")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    # 도매꾹 테스트
    await test_domeggook_correct()
    
    # 오너클랜 테스트
    await test_ownerclan_simple()
    
    # 젠트레이드 URL 찾기
    await test_zentrade_possible_urls()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
    
    print("\n[다음 단계]")
    print("1. 도매꾹: 올바른 API 문서 확인 필요")
    print("2. 오너클랜: GraphQL API 파트너 신청 또는 웹 스크래핑")
    print("3. 젠트레이드: 공식 API 문서 확인 필요")


if __name__ == "__main__":
    asyncio.run(main())