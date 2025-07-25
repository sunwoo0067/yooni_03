"""
전체 시스템 통합 테스트
모든 주요 기능을 순차적으로 테스트
"""

import requests
import json
import time
from datetime import datetime

# 설정
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# 테스트 결과 저장
test_results = []
created_resources = []  # 생성된 리소스 추적 (정리용)


def log_test(test_name, success, message=""):
    """테스트 결과 로깅"""
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {test_name}: {message}")
    test_results.append((test_name, success, message))
    return success


def cleanup_resources():
    """테스트 중 생성된 리소스 정리"""
    print("\n=== 테스트 리소스 정리 ===")
    for resource_type, resource_id in reversed(created_resources):
        try:
            if resource_type == "platform_account":
                requests.delete(f"{API_URL}/platform-accounts/{resource_id}")
            elif resource_type == "product":
                requests.delete(f"{API_URL}/products/{resource_id}")
            elif resource_type == "wholesaler_account":
                requests.delete(f"{API_URL}/wholesaler/accounts/{resource_id}")
            print(f"  - {resource_type} {resource_id} 삭제됨")
        except:
            pass


def test_system_health():
    """시스템 헬스체크"""
    print("\n=== 1. 시스템 헬스체크 ===")
    
    try:
        # 서버 헬스체크
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            return log_test("서버 헬스체크", False, f"HTTP {response.status_code}")
        
        health_data = response.json()
        if health_data.get('status') != 'healthy':
            return log_test("서버 헬스체크", False, "서버 상태가 healthy가 아님")
        
        log_test("서버 헬스체크", True, "서버 정상 작동")
        
        # API 상태 확인
        response = requests.get(f"{API_URL}/status")
        return log_test("API 상태", response.status_code == 200, f"API v{response.json().get('version', 'unknown')}")
        
    except requests.exceptions.ConnectionError:
        return log_test("서버 연결", False, "서버에 연결할 수 없음")
    except Exception as e:
        return log_test("시스템 헬스체크", False, str(e))


def test_platform_accounts():
    """플랫폼 계정 관리 테스트"""
    print("\n=== 2. 플랫폼 계정 관리 테스트 ===")
    
    # 테스트 데이터
    test_account = {
        "platform": "coupang",
        "account_name": "테스트_쿠팡_계정",
        "is_active": True,
        "api_credentials": {
            "access_key": "test_key_123",
            "secret_key": "test_secret_456",
            "vendor_id": "A00012345"
        }
    }
    
    try:
        # 계정 생성
        response = requests.post(f"{API_URL}/platform-accounts/", json=test_account)
        if response.status_code not in [200, 201]:
            return log_test("플랫폼 계정 생성", False, f"HTTP {response.status_code}: {response.text}")
        
        created_account = response.json()
        account_id = created_account.get('id')
        created_resources.append(("platform_account", account_id))
        
        log_test("플랫폼 계정 생성", True, f"계정 ID: {account_id}")
        
        # 계정 조회
        response = requests.get(f"{API_URL}/platform-accounts/{account_id}")
        log_test("플랫폼 계정 조회", response.status_code == 200, 
                f"계정명: {response.json().get('account_name') if response.status_code == 200 else 'N/A'}")
        
        # 계정 목록 조회
        response = requests.get(f"{API_URL}/platform-accounts/")
        accounts = response.json() if response.status_code == 200 else []
        log_test("플랫폼 계정 목록", response.status_code == 200, f"총 {len(accounts)}개 계정")
        
        return True
        
    except Exception as e:
        return log_test("플랫폼 계정 테스트", False, str(e))


def test_product_management():
    """상품 관리 테스트"""
    print("\n=== 3. 상품 관리 테스트 ===")
    
    test_product = {
        "product_code": "TEST-001",
        "name": "테스트 상품 - 블루투스 이어폰",
        "description": "고품질 무선 이어폰",
        "category": "전자제품",
        "price": 49900,
        "cost": 30000,
        "stock_quantity": 50,
        "is_active": True
    }
    
    try:
        # 상품 생성
        response = requests.post(f"{API_URL}/products/", json=test_product)
        if response.status_code not in [200, 201]:
            return log_test("상품 생성", False, f"HTTP {response.status_code}: {response.text}")
        
        created_product = response.json()
        product_id = created_product.get('id')
        created_resources.append(("product", product_id))
        
        log_test("상품 생성", True, f"상품 ID: {product_id}")
        
        # 상품 검색
        response = requests.get(f"{API_URL}/products/search", params={"query": "블루투스"})
        search_results = response.json() if response.status_code == 200 else []
        log_test("상품 검색", response.status_code == 200, f"검색 결과: {len(search_results)}개")
        
        return True
        
    except Exception as e:
        return log_test("상품 관리 테스트", False, str(e))


def test_wholesaler_integration():
    """도매처 연동 테스트"""
    print("\n=== 4. 도매처 연동 테스트 ===")
    
    # 도매처 계정 테스트 데이터
    test_wholesaler = {
        "wholesaler_type": "domeggook",
        "account_name": "테스트_도매매_계정",
        "api_credentials": {
            "api_key": "test_domeggook_key"
        },
        "is_active": True
    }
    
    try:
        # 도매처 계정 생성
        response = requests.post(f"{API_URL}/wholesaler/accounts", json=test_wholesaler)
        if response.status_code not in [200, 201]:
            return log_test("도매처 계정 생성", False, f"HTTP {response.status_code}")
        
        wholesaler_account = response.json()
        account_id = wholesaler_account.get('id')
        created_resources.append(("wholesaler_account", account_id))
        
        log_test("도매처 계정 생성", True, f"도매처 계정 ID: {account_id}")
        
        # 도매처 상품 조회 테스트
        response = requests.get(f"{API_URL}/wholesaler/products/{account_id}")
        log_test("도매처 상품 조회", response.status_code in [200, 404], 
                "상품 조회 API 정상" if response.status_code == 200 else "상품 없음")
        
        return True
        
    except Exception as e:
        return log_test("도매처 연동 테스트", False, str(e))


def test_ai_services():
    """AI 서비스 테스트"""
    print("\n=== 5. AI 서비스 테스트 ===")
    
    try:
        # AI 상태 확인
        response = requests.get(f"{API_URL}/ai/status")
        if response.status_code != 200:
            return log_test("AI 서비스 상태", False, f"HTTP {response.status_code}")
        
        ai_status = response.json()
        log_test("AI 서비스 상태", True, 
                f"Gemini: {ai_status.get('gemini_available', False)}, "
                f"Ollama: {ai_status.get('ollama_available', False)}")
        
        # 상품 설명 생성 테스트
        test_data = {
            "product_info": {
                "name": "스마트 워치",
                "category": "전자제품",
                "features": ["심박수 측정", "수면 추적", "방수"]
            }
        }
        
        response = requests.post(f"{API_URL}/ai/generate-description", json=test_data)
        if response.status_code == 200:
            result = response.json()
            description = result.get('description', '')
            log_test("AI 상품 설명 생성", True, f"생성된 설명 길이: {len(description)}자")
        else:
            log_test("AI 상품 설명 생성", False, "AI 서비스 응답 오류")
        
        return True
        
    except Exception as e:
        return log_test("AI 서비스 테스트", False, str(e))


def test_dashboard_and_analytics():
    """대시보드 및 분석 테스트"""
    print("\n=== 6. 대시보드 및 분석 테스트 ===")
    
    try:
        # 대시보드 요약
        response = requests.get(f"{API_URL}/dashboard/summary")
        if response.status_code == 200:
            summary = response.json()
            log_test("대시보드 요약", True, 
                    f"상품: {summary.get('total_products', 0)}, "
                    f"주문: {summary.get('total_orders', 0)}")
        else:
            log_test("대시보드 요약", False, f"HTTP {response.status_code}")
        
        # 판매 통계
        response = requests.get(f"{API_URL}/dashboard/sales-statistics")
        log_test("판매 통계", response.status_code == 200, 
                "통계 데이터 로드 성공" if response.status_code == 200 else "통계 데이터 없음")
        
        return True
        
    except Exception as e:
        return log_test("대시보드 테스트", False, str(e))


def test_performance_monitoring():
    """성능 모니터링 테스트"""
    print("\n=== 7. 성능 모니터링 테스트 ===")
    
    try:
        # 시스템 메트릭
        response = requests.get(f"{API_URL}/performance/metrics/system")
        if response.status_code == 200:
            metrics = response.json()
            log_test("시스템 메트릭", True, 
                    f"CPU: {metrics.get('cpu_percent', 0)}%, "
                    f"메모리: {metrics.get('memory_percent', 0)}%")
        else:
            log_test("시스템 메트릭", False, f"HTTP {response.status_code}")
        
        # 캐시 상태
        response = requests.get(f"{API_URL}/performance/cache/stats")
        if response.status_code == 200:
            cache_stats = response.json()
            hit_rate = cache_stats.get('hit_rate_percent', 0)
            log_test("캐시 상태", True, f"캐시 적중률: {hit_rate}%")
        else:
            log_test("캐시 상태", False, "캐시 통계 조회 실패")
        
        return True
        
    except Exception as e:
        return log_test("성능 모니터링 테스트", False, str(e))


def run_complete_test():
    """전체 시스템 테스트 실행"""
    print("\n" + "="*70)
    print("Yooni 드랍쉬핑 시스템 - 전체 통합 테스트")
    print("="*70)
    print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 순차적 테스트 실행
    test_system_health()
    test_platform_accounts()
    test_product_management()
    test_wholesaler_integration()
    test_ai_services()
    test_dashboard_and_analytics()
    test_performance_monitoring()
    
    # 리소스 정리
    cleanup_resources()
    
    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success, _ in test_results if success)
    failed_tests = total_tests - passed_tests
    
    # 카테고리별 결과
    categories = {
        "시스템 헬스": [],
        "플랫폼 계정": [],
        "상품 관리": [],
        "도매처 연동": [],
        "AI 서비스": [],
        "대시보드": [],
        "성능 모니터링": []
    }
    
    for test_name, success, message in test_results:
        for category in categories:
            if category in test_name:
                categories[category].append((test_name, success))
                break
    
    # 카테고리별 출력
    for category, results in categories.items():
        if results:
            passed = sum(1 for _, success in results if success)
            print(f"\n{category}: {passed}/{len(results)} 성공")
            for test_name, success in results:
                status = "[OK]" if success else "[FAIL]"
                print(f"  {status} {test_name}")
    
    # 전체 요약
    print(f"\n전체 결과: {passed_tests}/{total_tests} 테스트 성공 ({(passed_tests/total_tests)*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n[SUCCESS] 모든 테스트가 성공했습니다! 시스템이 정상 작동합니다.")
    else:
        print(f"\n[WARNING] {failed_tests}개의 테스트가 실패했습니다.")
        print("\n실패한 테스트:")
        for test_name, success, message in test_results:
            if not success:
                print(f"  - {test_name}: {message}")
    
    print(f"\n테스트 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    run_complete_test()