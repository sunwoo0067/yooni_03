#!/usr/bin/env python3
"""
도매매(Domeggook) API 테스트
"""

import os
import sys
import asyncio
import json
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

from app.services.wholesalers.domeggook_api_fixed import DomeggookAPIFixed


async def test_domeggook_connection():
    """도매매 API 연결 테스트"""
    print("\n" + "=" * 60)
    print("도매매 API 연결 테스트")
    print("=" * 60)
    
    # API 키 확인
    api_key = os.getenv('DOMEGGOOK_API_KEY')
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key not found")
    
    # API 클라이언트 생성
    client = DomeggookAPIFixed(api_key)
    
    # 연결 테스트
    print("\n1. 연결 테스트...")
    connected = await client.test_connection()
    
    if connected:
        print("✓ API 연결 성공")
        return client
    else:
        print("✗ API 연결 실패")
        return None


async def test_category_api(client):
    """카테고리 API 테스트"""
    print("\n" + "=" * 60)
    print("도매매 카테고리 API 테스트")
    print("=" * 60)
    
    # 카테고리 조회
    print("\n1. 전체 카테고리 조회...")
    categories = client.get_categories()
    
    if categories:
        print(f"✓ 총 {len(categories)}개 카테고리 조회 성공")
        
        # 샘플 출력
        print("\n카테고리 샘플 (처음 5개):")
        for i, category in enumerate(categories[:5], 1):
            print(f"  {i}. {category.get('category_name', 'N/A')} ({category.get('category_code', 'N/A')})")
        
        # 중분류 필터링
        print("\n2. 중분류 카테고리 필터링...")
        middle_categories = client.filter_middle_categories(categories)
        print(f"✓ {len(middle_categories)}개 중분류 카테고리 추출")
        
        print("\n중분류 카테고리 샘플 (처음 5개):")
        for i, code in enumerate(middle_categories[:5], 1):
            # 원본 카테고리에서 이름 찾기
            cat_name = next((c['category_name'] for c in categories if c['category_code'] == code), 'N/A')
            print(f"  {i}. {cat_name} ({code})")
        
        return middle_categories
    else:
        print("✗ 카테고리 조회 실패")
        return []


async def test_product_list_api(client, category_code):
    """상품 목록 API 테스트"""
    print("\n" + "=" * 60)
    print(f"도매매 상품 목록 API 테스트 (카테고리: {category_code})")
    print("=" * 60)
    
    # 상품 목록 조회
    print("\n상품 목록 조회 중...")
    response = client.get_product_list(category_code, page=1, per_page=10)
    
    if response and 'data' in response:
        data = response.get('data', {})
        items = data.get('items', [])
        pagination = data.get('pagination', {})
        
        print(f"✓ 상품 조회 성공")
        print(f"  - 현재 페이지: {pagination.get('current_page', 1)}")
        print(f"  - 전체 페이지: {pagination.get('total_pages', 'N/A')}")
        print(f"  - 전체 상품 수: {pagination.get('total_items', 'N/A')}")
        print(f"  - 조회된 상품 수: {len(items)}")
        
        if items:
            print("\n상품 샘플 (처음 3개):")
            for i, item in enumerate(items[:3], 1):
                print(f"\n  {i}. {item.get('product_name', 'N/A')}")
                print(f"     ID: {item.get('product_id', 'N/A')}")
                print(f"     가격: {item.get('price_info', {}).get('dom_price', 0):,}원")
                print(f"     재고: {item.get('stock_info', {}).get('quantity', 0)}개")
                print(f"     공급사: {item.get('supplier_name', 'N/A')}")
        
        return items
    else:
        print("✗ 상품 조회 실패")
        return []


async def test_product_collection(client):
    """상품 수집 테스트"""
    print("\n" + "=" * 60)
    print("도매매 상품 수집 테스트")
    print("=" * 60)
    
    print("\n전체 상품 수집 시작 (최대 20개)...")
    
    products = await client.collect_all_products(limit=20)
    
    if products:
        print(f"\n✓ 총 {len(products)}개 상품 수집 성공")
        
        # 카테고리별 통계
        categories = {}
        for product in products:
            cat = product.get('category', '미분류')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n카테고리별 상품 수:")
        for cat, count in categories.items():
            print(f"  - {cat}: {count}개")
        
        # 가격 통계
        prices = [p['price'] for p in products if p.get('price', 0) > 0]
        if prices:
            print(f"\n가격 통계:")
            print(f"  - 최저가: {min(prices):,}원")
            print(f"  - 최고가: {max(prices):,}원")
            print(f"  - 평균가: {sum(prices)//len(prices):,}원")
        
        return products
    else:
        print("✗ 상품 수집 실패")
        return []


async def main():
    """메인 함수"""
    print("도매매 API 테스트")
    print("실행 시간:", datetime.now())
    
    # 1. API 연결 테스트
    client = await test_domeggook_connection()
    if not client:
        print("\nAPI 연결 실패로 테스트 종료")
        return
    
    # 2. 카테고리 API 테스트
    middle_categories = await test_category_api(client)
    
    # 3. 상품 목록 API 테스트 (첫 번째 카테고리 사용)
    if middle_categories:
        await test_product_list_api(client, middle_categories[0])
    
    # 4. 상품 수집 테스트
    products = await test_product_collection(client)
    
    # 5. 결과 저장
    if products:
        filename = f'domeggook_test_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_products': len(products),
                'products': products[:10]  # 처음 10개만 저장
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n결과가 {filename}에 저장되었습니다.")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())