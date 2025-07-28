#!/usr/bin/env python3
"""
API 엔드포인트 테스트
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    """API 테스트"""
    print("API 엔드포인트 테스트")
    print("=" * 50)
    
    # 1. 헬스 체크
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"[OK] Health Check: {response.status_code}")
        print(f"  {response.json()}")
    except Exception as e:
        print(f"[FAIL] Health Check 실패: {e}")
        print("\nAPI 서버가 실행 중이 아닙니다!")
        print("다음 명령으로 서버를 시작하세요:")
        print("python -m uvicorn api.main:app --reload")
        return
    
    # 2. 공급사 목록
    try:
        response = requests.get(f"{BASE_URL}/suppliers")
        print(f"\n[OK] Suppliers: {response.status_code}")
        suppliers = response.json()
        for s in suppliers:
            print(f"  - {s['supplier_name']} ({s['supplier_code']})")
    except Exception as e:
        print(f"[FAIL] Suppliers 실패: {e}")
    
    # 3. 상품 목록
    try:
        response = requests.get(f"{BASE_URL}/products?limit=5")
        print(f"\n[OK] Products: {response.status_code}")
        data = response.json()
        print(f"  총 상품 수: {data['total']}")
        print(f"  조회된 상품: {len(data['products'])}개")
    except Exception as e:
        print(f"[FAIL] Products 실패: {e}")
    
    # 4. 수집 로그
    try:
        response = requests.get(f"{BASE_URL}/collection-logs?limit=5")
        print(f"\n[OK] Collection Logs: {response.status_code}")
        logs = response.json()
        print(f"  최근 수집 로그: {len(logs)}개")
        for log in logs[:3]:
            print(f"  - [{log['supplier']}] {log['status']} - {log['total_count']}개")
    except Exception as e:
        print(f"[FAIL] Collection Logs 실패: {e}")
    
    # 5. 수집 엔드포인트 확인
    try:
        # 수집 상태 확인
        response = requests.get(f"{BASE_URL}/collection/sync/status")
        print(f"\n[OK] Sync Status: {response.status_code}")
        status = response.json()
        print("  공급사별 상태:")
        for s in status.get('suppliers', []):
            print(f"  - {s['supplier']}: {s['product_count']}개")
    except Exception as e:
        print(f"[FAIL] Sync Status 실패: {e}")
        
    print("\n" + "=" * 50)
    print("API 테스트 완료!")

if __name__ == "__main__":
    test_api()