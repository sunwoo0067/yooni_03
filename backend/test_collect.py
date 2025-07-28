"""
도매처 상품 수집 테스트 스크립트
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

async def test_collection():
    try:
        from wholesaler_collector import KoreanWholesalerCollector
        
        print("도매처 상품 수집 테스트 시작...")
        
        collector = KoreanWholesalerCollector()
        
        # 오너클랜에서 상품 검색
        print("오너클랜에서 '무선이어폰' 검색 중...")
        results = await collector.collect_products(
            source='ownerclan',
            keyword='무선이어폰',
            page=1
        )
        
        print(f"수집 완료: {len(results)}개 상품")
        
        # 결과 출력
        for i, product in enumerate(results[:3], 1):  # 최대 3개만 출력
            print(f"\n{i}. 상품명: {product.get('name', '이름 없음')}")
            print(f"   가격: {product.get('price', 0):,}원")
            print(f"   URL: {product.get('url', 'URL 없음')}")
            
        return results
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    results = asyncio.run(test_collection())
    print(f"\n총 {len(results)}개 상품 수집 완료!")