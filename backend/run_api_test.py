#!/usr/bin/env python3
"""
백엔드 API 간단 테스트 스크립트
"""

import requests
import json
import time
import subprocess
import sys
import os
import threading

def test_api():
    """API 테스트 실행"""
    BASE_URL = "http://localhost:8003"
    API_V1_URL = f"{BASE_URL}/api/v1"
    
    print("=" * 60)
    print("[TEST] 백엔드 API 테스트")
    print("=" * 60)
    
    # 1. Health Check
    print("\n[1] Health Check 테스트")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            print("[PASS] Health Check 성공")
        else:
            print("[FAIL] Health Check 실패")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # 2. 상품 목록 조회
    print("\n[2] 상품 목록 조회")
    try:
        response = requests.get(f"{API_V1_URL}/products", timeout=5)
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            products = response.json()
            print(f"조회된 상품 수: {len(products)}")
            if products:
                print("첫 번째 상품:")
                print(json.dumps(products[0], indent=2, ensure_ascii=False))
            print("[PASS] 상품 목록 조회 성공")
        else:
            print("[FAIL] 상품 목록 조회 실패")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # 3. 대시보드 통계
    print("\n[3] 대시보드 통계")
    try:
        response = requests.get(f"{API_V1_URL}/dashboard/stats", timeout=5)
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"통계: {json.dumps(stats, indent=2, ensure_ascii=False)}")
            print("[PASS] 대시보드 통계 조회 성공")
        else:
            print("[FAIL] 대시보드 통계 조회 실패")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # 4. 상품 생성 테스트
    print("\n[4] 상품 생성 테스트")
    new_product = {
        "name": f"테스트 상품 {int(time.time())}",
        "description": "API 테스트용 상품",
        "price": 25000,
        "cost": 15000,
        "category": "테스트",
        "stock_quantity": 100,
        "status": "active"
    }
    
    try:
        response = requests.post(
            f"{API_V1_URL}/products",
            json=new_product,
            timeout=5
        )
        print(f"상태 코드: {response.status_code}")
        if response.status_code in [200, 201]:
            created = response.json()
            print(f"생성된 상품: {json.dumps(created, indent=2, ensure_ascii=False)}")
            print("[PASS] 상품 생성 성공")
            
            # 생성된 상품 삭제
            if created.get('id'):
                delete_response = requests.delete(f"{API_V1_URL}/products/{created['id']}")
                if delete_response.status_code in [200, 204]:
                    print("[INFO] 테스트 상품 삭제 완료")
        else:
            print(f"응답: {response.text}")
            print("[FAIL] 상품 생성 실패")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # 5. 도매처 목록 조회
    print("\n[5] 도매처 목록 조회")
    try:
        response = requests.get(f"{API_V1_URL}/collect/sources", timeout=5)
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            sources = response.json()
            print(f"도매처 목록: {json.dumps(sources, indent=2, ensure_ascii=False)}")
            print("[PASS] 도매처 목록 조회 성공")
        else:
            print("[FAIL] 도매처 목록 조회 실패")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print("\n" + "=" * 60)
    print("[COMPLETE] API 테스트 완료")
    print("=" * 60)


def run_server_and_test():
    """서버 실행 후 테스트"""
    print("[INFO] 백엔드 서버 시작 중...")
    
    # 서버 프로세스 시작
    server_process = subprocess.Popen(
        [sys.executable, "simple_main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # 서버 시작 대기
    print("[INFO] 서버 시작 대기 중... (5초)")
    time.sleep(5)
    
    try:
        # API 테스트 실행
        test_api()
    finally:
        # 서버 종료
        print("\n[INFO] 서버 종료 중...")
        server_process.terminate()
        server_process.wait()
        print("[INFO] 서버 종료 완료")


if __name__ == "__main__":
    # 서버가 이미 실행 중인지 확인
    try:
        response = requests.get("http://localhost:8003/health", timeout=2)
        if response.status_code == 200:
            print("[INFO] 서버가 이미 실행 중입니다. 바로 테스트를 시작합니다.")
            test_api()
        else:
            print("[INFO] 서버가 실행되지 않고 있습니다. 서버를 시작합니다.")
            run_server_and_test()
    except:
        print("[INFO] 서버가 실행되지 않고 있습니다. 서버를 시작합니다.")
        run_server_and_test()