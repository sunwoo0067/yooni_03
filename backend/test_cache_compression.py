"""
캐시 압축 기능 테스트
"""
import asyncio
import json
from app.core.cache import cache_manager

async def test_cache_compression():
    """캐시 압축 기능 테스트"""
    print("=== 캐시 압축 기능 테스트 ===\n")
    
    # 캐시 매니저 연결
    await cache_manager.connect()
    
    # 테스트 데이터 준비
    small_data = {"message": "작은 데이터"}
    large_data = {
        "products": [
            {
                "id": i,
                "name": f"상품 {i}",
                "description": f"이것은 상품 {i}의 상세 설명입니다. " * 10,
                "price": 10000 + i * 1000,
                "stock": 100 - i,
                "tags": [f"태그{j}" for j in range(10)]
            }
            for i in range(50)
        ]
    }
    
    # 통계 초기화
    cache_manager.reset_stats()
    
    print("1. 작은 데이터 캐싱 (압축 안됨)")
    await cache_manager.set("test:small", small_data, ttl=60)
    
    print("2. 큰 데이터 캐싱 (압축됨)")
    await cache_manager.set("test:large", large_data, ttl=60)
    
    print("\n3. 데이터 조회")
    retrieved_small = await cache_manager.get("test:small")
    retrieved_large = await cache_manager.get("test:large")
    
    # 데이터 검증
    assert retrieved_small == small_data, "작은 데이터 불일치"
    assert retrieved_large == large_data, "큰 데이터 불일치"
    print("V 데이터 무결성 확인 완료")
    
    # 통계 출력
    print("\n4. 캐시 통계:")
    stats = cache_manager.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 압축 효과 계산
    if "compression" in stats and stats["compression"]["compressed_count"] > 0:
        comp_stats = stats["compression"]
        print(f"\n5. 압축 효과:")
        print(f"   - 압축된 항목 수: {comp_stats['compressed_count']}")
        print(f"   - 원본 크기: {comp_stats['total_original_size']:,} bytes")
        print(f"   - 압축 후 크기: {comp_stats['total_compressed_size']:,} bytes")
        print(f"   - 절약된 공간: {comp_stats['space_saved_bytes']:,} bytes ({comp_stats['space_saved_percentage']})")
        print(f"   - 평균 압축률: {comp_stats['avg_compression_ratio_percentage']}")
    
    # 정리
    await cache_manager.delete("test:small")
    await cache_manager.delete("test:large")
    
    print("\n[완료] 캐시 압축 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_cache_compression())