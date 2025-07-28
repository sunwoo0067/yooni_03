#!/usr/bin/env python3
"""
백엔드 API 테스트 스크립트
실제 API 엔드포인트를 테스트합니다.
"""

import requests
import json
import time
from datetime import datetime
import subprocess
import sys
import threading
import os

# API 기본 URL
BASE_URL = "http://localhost:8002"
API_V1_URL = f"{BASE_URL}/api/v1"


def start_server():
    """백엔드 서버를 백그라운드로 실행"""
    print("[START] 백엔드 서버 시작 중...")
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # simple_main.py를 포트 8002로 실행
    cmd = [sys.executable, "simple_main.py"]
    env = os.environ.copy()
    env['PORT'] = '8002'
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # 서버 시작 대기
    time.sleep(5)
    return process


def stop_server(process):
    """서버 종료"""
    print("\n[STOP] 서버 종료 중...")
    process.terminate()
    process.wait()


def test_health_check():
    """헬스 체크 API 테스트"""
    print("\n[1] Health Check 테스트")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return False


def test_product_list():
    """상품 목록 조회 API 테스트"""
    print("\n[2] 상품 목록 조회 테스트")
    print("-" * 50)
    
    try:
        response = requests.get(f"{API_V1_URL}/products")
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            products = response.json()
            print(f"조회된 상품 수: {len(products)}")
            
            if products:
                print("\n첫 번째 상품:")
                print(json.dumps(products[0], indent=2, ensure_ascii=False))
        else:
            print(f"응답: {response.text}")
            
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return False


def test_collect_products():
    """도매처 상품 수집 API 테스트"""
    print("\n[3] 도매처 상품 수집 테스트")
    print("-" * 50)
    
    # 테스트할 도매처 목록
    wholesalers = ["ownerclan", "domeggook", "zentrade"]
    
    for wholesaler in wholesalers:
        print(f"\n[SHOP] {wholesaler} 상품 수집:")
        
        try:
            response = requests.post(
                f"{API_V1_URL}/wholesaler-sync/collect/{wholesaler}",
                params={"limit": 5}  # 테스트용으로 5개만
            )
            
            print(f"상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"수집된 상품 수: {result.get('collected_count', 0)}")
                print(f"실패 수: {result.get('failed_count', 0)}")
                
                # 첫 번째 수집 상품 출력
                if result.get('products'):
                    print("\n수집된 첫 번째 상품:")
                    print(json.dumps(result['products'][0], indent=2, ensure_ascii=False))
            else:
                print(f"응답: {response.text}")
                
        except Exception as e:
            print(f"[ERROR] 에러 발생: {e}")


def test_ai_endpoints():
    """AI 관련 API 테스트"""
    print("\n[4] AI 분석 API 테스트")
    print("-" * 50)
    
    # 테스트 상품 데이터
    test_product = {
        "title": "겨울 남성 패딩 자켓",
        "description": "따뜻하고 가벼운 겨울 패딩",
        "price": 89000,
        "category": "의류"
    }
    
    # 상품 분석 테스트
    print("\n[ANALYSIS] 상품 분석:")
    try:
        response = requests.post(
            f"{API_V1_URL}/ai/analyze-product",
            json=test_product
        )
        
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"분석 결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")


def test_dashboard_metrics():
    """대시보드 메트릭 API 테스트"""
    print("\n[5] 대시보드 메트릭 테스트")
    print("-" * 50)
    
    try:
        response = requests.get(f"{API_V1_URL}/dashboard/metrics")
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"메트릭: {json.dumps(metrics, indent=2, ensure_ascii=False)}")
        else:
            print(f"응답: {response.text}")
            
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return False


def test_create_product():
    """상품 생성 API 테스트"""
    print("\n[6] 상품 생성 테스트")
    print("-" * 50)
    
    # 테스트 상품 데이터
    new_product = {
        "name": "테스트 상품 " + datetime.now().strftime("%Y%m%d%H%M%S"),
        "description": "API 테스트를 위한 상품입니다",
        "price": 25000,
        "cost": 15000,
        "stock_quantity": 100,
        "category": "테스트",
        "source_platform": "manual",
        "is_active": True
    }
    
    try:
        response = requests.post(
            f"{API_V1_URL}/products",
            json=new_product
        )
        
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code in [200, 201]:
            created_product = response.json()
            print(f"생성된 상품: {json.dumps(created_product, indent=2, ensure_ascii=False)}")
            return created_product.get('id')
        else:
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return None


def test_update_product(product_id):
    """상품 수정 API 테스트"""
    print("\n[7] 상품 수정 테스트")
    print("-" * 50)
    
    if not product_id:
        print("[ERROR] 수정할 상품 ID가 없습니다")
        return False
    
    # 수정할 데이터
    update_data = {
        "name": "수정된 테스트 상품",
        "price": 30000,
        "stock_quantity": 150
    }
    
    try:
        response = requests.put(
            f"{API_V1_URL}/products/{product_id}",
            json=update_data
        )
        
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            updated_product = response.json()
            print(f"수정된 상품: {json.dumps(updated_product, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return False


def test_delete_product(product_id):
    """상품 삭제 API 테스트"""
    print("\n[8] 상품 삭제 테스트")
    print("-" * 50)
    
    if not product_id:
        print("[ERROR] 삭제할 상품 ID가 없습니다")
        return False
    
    try:
        response = requests.delete(f"{API_V1_URL}/products/{product_id}")
        
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print("[SUCCESS] 상품이 성공적으로 삭제되었습니다")
            return True
        else:
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return False


def run_api_tests():
    """모든 API 테스트 실행"""
    print("=" * 60)
    print("[TEST] 백엔드 API 테스트 시작")
    print("=" * 60)
    
    # 서버 시작
    server_process = start_server()
    
    try:
        # 각 테스트 실행
        results = []
        
        # 1. Health Check
        results.append(("Health Check", test_health_check()))
        
        # 2. 상품 목록 조회
        results.append(("상품 목록 조회", test_product_list()))
        
        # 3. 도매처 상품 수집
        test_collect_products()
        
        # 4. AI 분석
        test_ai_endpoints()
        
        # 5. 대시보드 메트릭
        results.append(("대시보드 메트릭", test_dashboard_metrics()))
        
        # 6. CRUD 테스트
        product_id = test_create_product()
        if product_id:
            results.append(("상품 생성", True))
            results.append(("상품 수정", test_update_product(product_id)))
            results.append(("상품 삭제", test_delete_product(product_id)))
        else:
            results.append(("상품 생성", False))
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("[RESULT] 테스트 결과 요약")
        print("=" * 60)
        
        for test_name, result in results:
            status = "[PASS] 성공" if result else "[FAIL] 실패"
            print(f"{test_name}: {status}")
        
        success_count = sum(1 for _, result in results if result)
        total_count = len(results)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공 (성공률: {success_rate:.1f}%)")
        
    finally:
        # 서버 종료
        stop_server(server_process)


if __name__ == "__main__":
    # 테스트 실행
    run_api_tests()