"""
베스트셀러 수집 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from collectors.bestseller_collector import CoupangBestsellerCollector, NaverShoppingCollector


async def test_bestseller_collection():
    """베스트셀러 수집 테스트"""
    print("베스트셀러 수집 테스트 시작...")
    print("=" * 50)
    
    # 쿠팡 베스트셀러 수집
    print("\n1. 쿠팡 베스트셀러 수집 중...")
    coupang_collector = CoupangBestsellerCollector()
    coupang_products = await coupang_collector.get_bestsellers(limit=5)
    
    print(f"   수집된 상품: {len(coupang_products)}개")
    if coupang_products:
        for idx, product in enumerate(coupang_products[:3]):
            print(f"\n   [{idx+1}위]")
            print(f"   상품명: {product['product_name'][:50]}...")
            print(f"   가격: {product['price']:,}원")
            print(f"   리뷰: {product['review_count']:,}개")
            print(f"   평점: {product['rating']}")
    
    # 네이버 쇼핑 수집
    print("\n\n2. 네이버 쇼핑 베스트셀러 수집 중...")
    naver_collector = NaverShoppingCollector()
    naver_products = await naver_collector.get_bestsellers(limit=5)
    
    print(f"   수집된 상품: {len(naver_products)}개")
    if naver_products:
        for idx, product in enumerate(naver_products[:3]):
            print(f"\n   [{idx+1}위]")
            print(f"   상품명: {product['product_name'][:50]}...")
            print(f"   가격: {product['price']:,}원")
            print(f"   브랜드: {product['brand']}")
            print(f"   리뷰: {product['review_count']:,}개")
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    
    return {
        'coupang': coupang_products,
        'naver': naver_products
    }

if __name__ == "__main__":
    asyncio.run(test_bestseller_collection())