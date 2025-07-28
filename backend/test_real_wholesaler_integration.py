#!/usr/bin/env python3
"""
실제 도매처 API 통합 테스트
기존 구조를 활용한 실제 API 연동
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# 기존 구현 임포트
from app.services.wholesalers.ownerclan_api import OwnerClanAPI
from app.services.wholesalers.domeggook_api import DomeggookAPI
from app.services.wholesalers.base_wholesaler import CollectionType


async def test_ownerclan():
    """오너클랜 실제 API 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 API 테스트")
    print("=" * 60)
    
    # 실제 인증 정보 설정
    credentials = {
        'username': os.getenv('OWNERCLAN_USERNAME', ''),
        'password': os.getenv('OWNERCLAN_PASSWORD', ''),
        'api_url': 'https://api.ownerclan.com/v1/graphql',  # 실제 API URL
        'auth_url': 'https://auth.ownerclan.com/auth'      # 실제 인증 URL
    }
    
    if not credentials['username'] or not credentials['password']:
        print("[경고] 오너클랜 인증 정보가 설정되지 않았습니다.")
        print("환경 변수를 설정하세요:")
        print("- OWNERCLAN_USERNAME")
        print("- OWNERCLAN_PASSWORD")
        return
    
    api = OwnerClanAPI(credentials)
    
    # 1. 연결 테스트
    print("\n1. 연결 테스트")
    test_result = await api.test_connection()
    print(f"결과: {json.dumps(test_result, indent=2, ensure_ascii=False)}")
    
    if not test_result['success']:
        print("연결 실패! API URL이나 인증 정보를 확인하세요.")
        return
    
    # 2. 카테고리 조회
    print("\n2. 카테고리 조회")
    categories = await api.get_categories()
    print(f"카테고리 수: {len(categories)}")
    if categories:
        print(f"첫 번째 카테고리: {categories[0]}")
    
    # 3. 상품 수집 (최근 상품)
    print("\n3. 최근 상품 수집")
    collected_count = 0
    products = []
    
    async for product in api.collect_products(
        collection_type=CollectionType.RECENT,
        filters={'days': 7},
        max_products=5
    ):
        collected_count += 1
        products.append({
            'id': product.wholesaler_product_id,
            'name': product.name,
            'price': product.wholesale_price,
            'stock': product.stock_quantity,
            'category': product.category_path
        })
        print(f"수집 {collected_count}: {product.name}")
    
    print(f"\n총 {collected_count}개 상품 수집 완료")
    
    # 결과 저장
    with open('ownerclan_products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


async def test_domeggook():
    """도매꾹 실제 API 테스트"""
    print("\n" + "=" * 60)
    print("도매꾹 API 테스트")
    print("=" * 60)
    
    # 실제 인증 정보 설정
    credentials = {
        'api_key': os.getenv('DOMEGGOOK_API_KEY', ''),
        'api_url': 'https://openapi.domeggook.com'  # 실제 API URL
    }
    
    if not credentials['api_key']:
        print("[경고] 도매꾹 API 키가 설정되지 않았습니다.")
        print("환경 변수를 설정하세요:")
        print("- DOMEGGOOK_API_KEY")
        return
    
    api = DomeggookAPI(credentials)
    
    # 1. 연결 테스트
    print("\n1. 연결 테스트")
    test_result = await api.test_connection()
    print(f"결과: {json.dumps(test_result, indent=2, ensure_ascii=False)}")
    
    if not test_result['success']:
        print("연결 실패! API 키를 확인하세요.")
        return
    
    # 2. 카테고리 조회
    print("\n2. 카테고리 조회")
    categories = await api.get_categories()
    print(f"카테고리 수: {len(categories)}")
    if categories:
        print(f"첫 번째 카테고리: {categories[0]}")
    
    # 3. 상품 수집 (전체)
    print("\n3. 상품 수집")
    collected_count = 0
    products = []
    
    async for product in api.collect_products(
        collection_type=CollectionType.ALL,
        max_products=5
    ):
        collected_count += 1
        products.append({
            'id': product.wholesaler_product_id,
            'name': product.name,
            'price': product.wholesale_price,
            'stock': product.stock_quantity,
            'category': product.category_path
        })
        print(f"수집 {collected_count}: {product.name}")
    
    print(f"\n총 {collected_count}개 상품 수집 완료")
    
    # 결과 저장
    with open('domeggook_products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


async def search_products_all(keyword: str):
    """모든 도매처에서 상품 검색"""
    print("\n" + "=" * 60)
    print(f"통합 상품 검색: '{keyword}'")
    print("=" * 60)
    
    all_products = []
    
    # 오너클랜 검색
    if os.getenv('OWNERCLAN_USERNAME'):
        print("\n[오너클랜 검색]")
        credentials = {
            'username': os.getenv('OWNERCLAN_USERNAME'),
            'password': os.getenv('OWNERCLAN_PASSWORD'),
            'api_url': 'https://api.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth.ownerclan.com/auth'
        }
        
        api = OwnerClanAPI(credentials)
        
        # 인증
        if await api.authenticate():
            count = 0
            async for product in api.collect_products(
                collection_type=CollectionType.ALL,
                filters={'keywords': [keyword]},
                max_products=5
            ):
                count += 1
                all_products.append({
                    'wholesaler': 'ownerclan',
                    'id': product.wholesaler_product_id,
                    'name': product.name,
                    'price': product.wholesale_price,
                    'stock': product.stock_quantity
                })
                
            print(f"오너클랜: {count}개 상품 검색됨")
    
    # 도매꾹 검색
    if os.getenv('DOMEGGOOK_API_KEY'):
        print("\n[도매꾹 검색]")
        credentials = {
            'api_key': os.getenv('DOMEGGOOK_API_KEY'),
            'api_url': 'https://openapi.domeggook.com'
        }
        
        api = DomeggookAPI(credentials)
        
        # 인증
        if await api.authenticate():
            count = 0
            # 도매꾹은 키워드 검색을 직접 지원하지 않을 수 있음
            # 전체 상품을 가져와서 필터링하거나 별도 API 사용
            async for product in api.collect_products(
                collection_type=CollectionType.ALL,
                max_products=100
            ):
                if keyword.lower() in product.name.lower():
                    count += 1
                    all_products.append({
                        'wholesaler': 'domeggook',
                        'id': product.wholesaler_product_id,
                        'name': product.name,
                        'price': product.wholesale_price,
                        'stock': product.stock_quantity
                    })
                    
                if count >= 5:
                    break
                    
            print(f"도매꾹: {count}개 상품 검색됨")
    
    # 결과 출력
    print(f"\n총 {len(all_products)}개 상품 검색 완료")
    
    # 결과 저장
    filename = f'search_results_{keyword}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
        
    print(f"\n결과가 {filename} 파일에 저장되었습니다.")
    
    return all_products


async def main():
    """메인 실행 함수"""
    print("실제 도매처 API 통합 테스트")
    print("=" * 60)
    
    # 환경 변수 확인
    print("\n환경 변수 확인:")
    print(f"- OWNERCLAN_USERNAME: {'설정됨' if os.getenv('OWNERCLAN_USERNAME') else '미설정'}")
    print(f"- OWNERCLAN_PASSWORD: {'설정됨' if os.getenv('OWNERCLAN_PASSWORD') else '미설정'}")
    print(f"- DOMEGGOOK_API_KEY: {'설정됨' if os.getenv('DOMEGGOOK_API_KEY') else '미설정'}")
    
    # 테스트 실행
    print("\n어떤 테스트를 실행하시겠습니까?")
    print("1. 오너클랜 API 테스트")
    print("2. 도매꾹 API 테스트")
    print("3. 통합 상품 검색")
    print("4. 전체 테스트")
    
    choice = input("\n선택 (1-4): ")
    
    if choice == '1':
        await test_ownerclan()
    elif choice == '2':
        await test_domeggook()
    elif choice == '3':
        keyword = input("검색어 입력: ")
        await search_products_all(keyword)
    elif choice == '4':
        await test_ownerclan()
        await test_domeggook()
        await search_products_all("이어폰")
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    # 실행
    asyncio.run(main())