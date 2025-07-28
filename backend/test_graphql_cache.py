"""
GraphQL 캐싱 기능 테스트
"""
import asyncio
import json
from app.core.graphql_cache import graphql_cache_manager
from app.core.cache import cache_manager

async def test_graphql_caching():
    """GraphQL 캐싱 기능 테스트"""
    print("=== GraphQL 캐싱 기능 테스트 ===\n")
    
    # 캐시 매니저 연결
    await cache_manager.connect()
    
    # 테스트용 GraphQL 쿼리와 변수
    test_query = """
        query GetProducts($category: String!, $limit: Int) {
            products(category: $category, limit: $limit) {
                id
                name
                price
                stock
            }
        }
    """
    
    test_variables = {
        "category": "electronics",
        "limit": 10
    }
    
    # 테스트 결과 데이터
    test_result = {
        "data": {
            "products": [
                {"id": "1", "name": "노트북", "price": 1500000, "stock": 10},
                {"id": "2", "name": "마우스", "price": 30000, "stock": 50}
            ]
        }
    }
    
    print("1. GraphQL 쿼리 결과 캐싱 테스트")
    
    # 결과 캐싱
    success = await graphql_cache_manager.cache_result(
        test_query, 
        test_result, 
        test_variables,
        operation_name="GetProducts",
        ttl=60
    )
    print(f"   캐싱 성공: {success}")
    
    # 캐시된 결과 조회
    print("\n2. 캐시된 결과 조회")
    cached_result = await graphql_cache_manager.get_cached_result(
        test_query,
        test_variables,
        operation_name="GetProducts"
    )
    
    if cached_result:
        print("   캐시 히트!")
        print(f"   결과: {json.dumps(cached_result, indent=2, ensure_ascii=False)}")
    else:
        print("   캐시 미스")
    
    # 다른 변수로 조회 (캐시 미스 예상)
    print("\n3. 다른 변수로 조회 (캐시 미스 예상)")
    different_variables = {"category": "books", "limit": 5}
    cached_result2 = await graphql_cache_manager.get_cached_result(
        test_query,
        different_variables,
        operation_name="GetProducts"
    )
    
    if cached_result2:
        print("   예상외의 캐시 히트")
    else:
        print("   예상대로 캐시 미스")
    
    # 캐시 통계
    print("\n4. 캐시 통계:")
    stats = cache_manager.get_stats()
    print(f"   히트: {stats['hits']}")
    print(f"   미스: {stats['misses']}")
    print(f"   히트율: {stats['hit_rate']}")
    
    # 캐시 무효화
    print("\n5. GraphQL 캐시 무효화")
    deleted = await graphql_cache_manager.invalidate_by_type("Product")
    print(f"   삭제된 캐시 항목 수: {deleted}")
    
    # 무효화 후 조회
    print("\n6. 무효화 후 조회")
    cached_result3 = await graphql_cache_manager.get_cached_result(
        test_query,
        test_variables,
        operation_name="GetProducts"
    )
    
    if cached_result3:
        print("   예상외의 캐시 히트")
    else:
        print("   예상대로 캐시 미스 (무효화됨)")
    
    print("\n[완료] GraphQL 캐싱 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_graphql_caching())