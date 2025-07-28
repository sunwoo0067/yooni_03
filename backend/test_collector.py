"""
도매처 상품 수집 API 테스트 스크립트
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """헬스 체크"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)

def test_collect_products():
    """상품 수집 테스트"""
    url = f"{BASE_URL}/api/v1/product-collector/collect"
    data = {
        "source": "ownerclan",
        "keyword": "무선이어폰",
        "limit": 5
    }
    
    response = requests.post(url, data=data)
    print(f"Collect Products: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        print(f"Total Collected: {result['total_collected']}")
        print(f"Batch ID: {result['batch_id']}")
        print("\nCollected Products:")
        for i, product in enumerate(result['products'], 1):
            print(f"\n{i}. {product['name']}")
            print(f"   Price: {product['price']:,}원")
            print(f"   Category: {product['category']}")
            print(f"   ID: {product['id']}")
    else:
        print(f"Error Response: {response.text}")
    
    print("-" * 50)

def test_get_sources():
    """도매처 목록 조회"""
    response = requests.get(f"{BASE_URL}/api/v1/product-collector/sources")
    print(f"Get Sources: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nAvailable Sources:")
        for source in result['sources']:
            print(f"\n- {source['name']} ({source['id']})")
            print(f"  Description: {source['description']}")
            print(f"  Categories: {', '.join(source['categories'])}")
    else:
        print(f"Error Response: {response.text}")
    
    print("-" * 50)

def test_get_collected_products():
    """수집된 상품 목록 조회"""
    response = requests.get(f"{BASE_URL}/api/v1/product-collector/collected?limit=10")
    print(f"Get Collected Products: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total Products: {result['total']}")
        print(f"Page: {result['page']}/{result['total_pages']}")
        
        if result['products']:
            print("\nProducts:")
            for i, product in enumerate(result['products'], 1):
                print(f"\n{i}. {product['name']}")
                print(f"   Source: {product['source']}")
                print(f"   Price: {product['price']:,}원")
                print(f"   Status: {product['status']}")
        else:
            print("\nNo products found.")
    else:
        print(f"Error Response: {response.text}")
    
    print("-" * 50)

def test_api_docs():
    """API 문서 확인"""
    response = requests.get(f"{BASE_URL}/docs")
    print(f"API Docs: {response.status_code}")
    if response.status_code == 200:
        print("API documentation is available at http://localhost:8000/docs")
    print("-" * 50)

if __name__ == "__main__":
    print("=== 도매처 상품 수집 API 테스트 ===\n")
    
    # 1. 헬스 체크
    test_health()
    
    # 2. API 문서 확인
    test_api_docs()
    
    # 3. 도매처 목록 조회
    test_get_sources()
    
    # 4. 상품 수집
    test_collect_products()
    
    # 5. 수집된 상품 목록 조회
    test_get_collected_products()
    
    print("\n테스트 완료!")