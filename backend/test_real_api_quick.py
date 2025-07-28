#!/usr/bin/env python3
"""
실제 API 빠른 테스트
"""

import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("실제 API 테스트")
print("=" * 60)

# 1. 서버 상태 확인
print("\n[1] 서버 상태 확인")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"상태: {response.status_code}")
    print(f"응답: {response.json()}")
except Exception as e:
    print(f"에러: {e}")

# 2. API 키 설정 확인
print("\n[2] API 키 설정 확인")
try:
    response = requests.get(BASE_URL)
    print(f"상태: {response.status_code}")
    data = response.json()
    print(f"앱: {data['message']}")
    print(f"API 키 설정 상태:")
    for key, value in data['api_keys_configured'].items():
        print(f"  - {key}: {'설정됨' if value else '미설정'}")
except Exception as e:
    print(f"에러: {e}")

# 3. Gemini AI 테스트
print("\n[3] Google Gemini AI 분석 테스트")
try:
    product_data = {
        "title": "프리미엄 무선 블루투스 이어폰",
        "description": "최신 노이즈 캔슬링 기능과 긴 배터리 수명",
        "price": 89000,
        "category": "전자제품"
    }
    
    print(f"분석할 상품: {product_data['title']}")
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/analyze-product",
        json=product_data,
        timeout=30
    )
    
    print(f"상태: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"분석 상태: {result['status']}")
        if result['status'] == 'success':
            print(f"\n[AI 분석 결과]")
            print(result['analysis'])
        else:
            print(f"에러: {result.get('message', 'Unknown error')}")
except Exception as e:
    print(f"에러: {e}")

# 4. 쿠팡 API 테스트
print("\n[4] 쿠팡 API 연결 테스트")
try:
    response = requests.get(f"{BASE_URL}/api/v1/test/coupang")
    print(f"상태: {response.status_code}")
    print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"에러: {e}")

# 5. 네이버 API 테스트
print("\n[5] 네이버 API 연결 테스트")
try:
    response = requests.get(f"{BASE_URL}/api/v1/test/naver")
    print(f"상태: {response.status_code}")
    print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"에러: {e}")

# 6. 도매처 수집 테스트
print("\n[6] 도매처 상품 수집 테스트 (Ownerclan)")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/wholesaler-sync/collect/ownerclan",
        params={"limit": 5}
    )
    print(f"상태: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"수집 상태: {result['status']}")
        print(f"수집된 상품 수: {result['collected_count']}")
        if result['products']:
            print(f"첫 번째 상품: {result['products'][0]['name']}")
except Exception as e:
    print(f"에러: {e}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)