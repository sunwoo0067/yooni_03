"""
API 엔드포인트 테스트
FastAPI 서버의 주요 API 엔드포인트 테스트
"""

import requests
import json
import time
from datetime import datetime

# 기본 설정
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# 테스트 데이터
TEST_PLATFORM_ACCOUNT = {
    "platform": "coupang",
    "account_name": "테스트_쿠팡_계정",
    "is_active": True,
    "api_credentials": {
        "access_key": "test_access_key_123",
        "secret_key": "test_secret_key_456",
        "vendor_id": "A00012345"
    }
}

TEST_PRODUCT = {
    "product_code": "TEST-PROD-001",
    "name": "테스트 상품 - 무선 이어폰",
    "description": "고품질 블루투스 5.0 무선 이어폰",
    "category": "전자제품",
    "price": 39900,
    "cost": 25000,
    "stock_quantity": 100,
    "is_active": True,
    "product_attributes": {
        "brand": "TestBrand",
        "color": "블랙",
        "warranty": "1년"
    }
}


def test_health_check():
    """헬스체크 엔드포인트 테스트"""
    print("\n=== 헬스체크 테스트 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            print("[OK] 헬스체크 성공")
            data = response.json()
            print(f"  - 상태: {data.get('status')}")
            print(f"  - 버전: {data.get('version')}")
            return True
        else:
            print(f"[FAIL] 헬스체크 실패: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[FAIL] 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        return False


def test_api_status():
    """API 상태 엔드포인트 테스트"""
    print("\n=== API 상태 테스트 ===")
    
    try:
        response = requests.get(f"{API_URL}/status")
        
        if response.status_code == 200:
            print("[OK] API 상태 확인 성공")
            data = response.json()
            print(f"  - 메시지: {data.get('status')}")
            print(f"  - 버전: {data.get('version')}")
            return True
        else:
            print(f"[FAIL] API 상태 확인 실패: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        return False


def test_platform_accounts_crud():
    """플랫폼 계정 CRUD 테스트"""
    print("\n=== 플랫폼 계정 CRUD 테스트 ===")
    
    created_account_id = None
    
    try:
        # 1. 계정 생성 (Create)
        print("\n1. 계정 생성 테스트")
        response = requests.post(
            f"{API_URL}/platform-accounts/",
            json=TEST_PLATFORM_ACCOUNT
        )
        
        if response.status_code in [200, 201]:
            print("[OK] 계정 생성 성공")
            created_account = response.json()
            created_account_id = created_account.get('id')
            print(f"  - 계정 ID: {created_account_id}")
            print(f"  - 계정명: {created_account.get('account_name')}")
        else:
            print(f"[FAIL] 계정 생성 실패: HTTP {response.status_code}")
            print(f"  - 응답: {response.text}")
            return False
        
        # 2. 계정 조회 (Read)
        print("\n2. 계정 조회 테스트")
        response = requests.get(f"{API_URL}/platform-accounts/{created_account_id}")
        
        if response.status_code == 200:
            print("[OK] 계정 조회 성공")
            account = response.json()
            print(f"  - 플랫폼: {account.get('platform')}")
            print(f"  - 활성 상태: {account.get('is_active')}")
        else:
            print(f"[FAIL] 계정 조회 실패: HTTP {response.status_code}")
        
        # 3. 계정 목록 조회
        print("\n3. 계정 목록 조회 테스트")
        response = requests.get(f"{API_URL}/platform-accounts/")
        
        if response.status_code == 200:
            print("[OK] 계정 목록 조회 성공")
            accounts = response.json()
            print(f"  - 총 계정 수: {len(accounts)}")
        else:
            print(f"[FAIL] 계정 목록 조회 실패: HTTP {response.status_code}")
        
        # 4. 계정 수정 (Update)
        print("\n4. 계정 수정 테스트")
        update_data = {
            "account_name": "수정된_테스트_계정",
            "is_active": False
        }
        response = requests.put(
            f"{API_URL}/platform-accounts/{created_account_id}",
            json=update_data
        )
        
        if response.status_code == 200:
            print("[OK] 계정 수정 성공")
            updated_account = response.json()
            print(f"  - 새 계정명: {updated_account.get('account_name')}")
            print(f"  - 새 활성 상태: {updated_account.get('is_active')}")
        else:
            print(f"[FAIL] 계정 수정 실패: HTTP {response.status_code}")
        
        # 5. 계정 삭제 (Delete)
        print("\n5. 계정 삭제 테스트")
        response = requests.delete(f"{API_URL}/platform-accounts/{created_account_id}")
        
        if response.status_code in [200, 204]:
            print("[OK] 계정 삭제 성공")
            return True
        else:
            print(f"[FAIL] 계정 삭제 실패: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        
        # 정리: 생성된 계정이 있으면 삭제
        if created_account_id:
            try:
                requests.delete(f"{API_URL}/platform-accounts/{created_account_id}")
            except:
                pass
                
        return False


def test_products_api():
    """상품 API 테스트"""
    print("\n=== 상품 API 테스트 ===")
    
    created_product_id = None
    
    try:
        # 1. 상품 생성
        print("\n1. 상품 생성 테스트")
        response = requests.post(
            f"{API_URL}/products/",
            json=TEST_PRODUCT
        )
        
        if response.status_code in [200, 201]:
            print("[OK] 상품 생성 성공")
            created_product = response.json()
            created_product_id = created_product.get('id')
            print(f"  - 상품 ID: {created_product_id}")
            print(f"  - 상품명: {created_product.get('name')}")
        else:
            print(f"[FAIL] 상품 생성 실패: HTTP {response.status_code}")
            print(f"  - 응답: {response.text}")
            return False
        
        # 2. 상품 검색
        print("\n2. 상품 검색 테스트")
        response = requests.get(
            f"{API_URL}/products/search",
            params={"query": "무선"}
        )
        
        if response.status_code == 200:
            print("[OK] 상품 검색 성공")
            results = response.json()
            print(f"  - 검색 결과 수: {len(results)}")
        else:
            print(f"[FAIL] 상품 검색 실패: HTTP {response.status_code}")
        
        # 3. 상품 삭제
        if created_product_id:
            response = requests.delete(f"{API_URL}/products/{created_product_id}")
            if response.status_code in [200, 204]:
                print("\n[OK] 테스트 상품 정리 완료")
            
        return True
        
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        
        # 정리
        if created_product_id:
            try:
                requests.delete(f"{API_URL}/products/{created_product_id}")
            except:
                pass
                
        return False


def test_ai_service():
    """AI 서비스 엔드포인트 테스트"""
    print("\n=== AI 서비스 테스트 ===")
    
    try:
        # 1. 상품 설명 생성
        print("\n1. AI 상품 설명 생성 테스트")
        
        product_info = {
            "name": "블루투스 이어폰",
            "category": "전자제품",
            "features": ["노이즈 캔슬링", "30시간 재생", "방수 기능"]
        }
        
        response = requests.post(
            f"{API_URL}/ai/generate-description",
            json={"product_info": product_info}
        )
        
        if response.status_code == 200:
            print("[OK] AI 설명 생성 성공")
            result = response.json()
            description = result.get('description', '')
            print(f"  - 생성된 설명 길이: {len(description)}자")
            print(f"  - 설명 일부: {description[:100]}...")
            return True
        else:
            print(f"[FAIL] AI 설명 생성 실패: HTTP {response.status_code}")
            print(f"  - 응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        return False


def test_dashboard_api():
    """대시보드 API 테스트"""
    print("\n=== 대시보드 API 테스트 ===")
    
    try:
        # 1. 대시보드 요약 정보
        print("\n1. 대시보드 요약 정보 테스트")
        response = requests.get(f"{API_URL}/dashboard/summary")
        
        if response.status_code == 200:
            print("[OK] 대시보드 요약 조회 성공")
            summary = response.json()
            print(f"  - 총 상품 수: {summary.get('total_products', 0)}")
            print(f"  - 총 주문 수: {summary.get('total_orders', 0)}")
            print(f"  - 활성 플랫폼 수: {summary.get('active_platforms', 0)}")
            return True
        else:
            print(f"[FAIL] 대시보드 요약 조회 실패: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*60)
    print("Yooni 드랍쉬핑 시스템 - API 엔드포인트 테스트")
    print("="*60)
    
    test_results = []
    
    # 서버 연결 확인
    server_available = test_health_check()
    test_results.append(("헬스체크", server_available))
    
    if not server_available:
        print("\n[ERROR] 서버에 연결할 수 없습니다!")
        print("다음 명령으로 서버를 실행하세요:")
        print("  cd backend && python main.py")
        return
    
    # 각 테스트 실행
    test_results.append(("API 상태", test_api_status()))
    test_results.append(("플랫폼 계정 CRUD", test_platform_accounts_crud()))
    test_results.append(("상품 API", test_products_api()))
    test_results.append(("AI 서비스", test_ai_service()))
    test_results.append(("대시보드 API", test_dashboard_api()))
    
    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    
    total = len(test_results)
    passed = sum(1 for _, result in test_results if result)
    
    for test_name, result in test_results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 성공")
    
    if passed == total:
        print("\n[SUCCESS] 모든 API 테스트가 성공했습니다!")
    else:
        print(f"\n[WARNING] {total - passed}개의 테스트가 실패했습니다.")


if __name__ == "__main__":
    run_all_tests()