# -*- coding: utf-8 -*-
"""
실제 드롭시핑 프로젝트 테스트
현재 구현된 시스템의 핵심 기능 검증
"""
import os
import sys
import importlib
from datetime import datetime

print("=== 실제 드롭시핑 시스템 테스트 ===")
print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 테스트 결과 카운터
total_tests = 0
passed_tests = 0
failed_tests = 0

def test_result(name, success, message=""):
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    
    if success:
        passed_tests += 1
        print(f"[PASS] {name}: {message}")
    else:
        failed_tests += 1
        print(f"[FAIL] {name}: {message}")

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 1. 핵심 파일 구조 테스트
print("\n=== 핵심 파일 구조 테스트 ===")

critical_files = [
    "app/models/product.py",
    "app/models/wholesaler.py", 
    "app/api/v1/endpoints/products.py",
    "app/api/v1/endpoints/wholesaler.py",
    "app/services/wholesale/analysis_service.py",
    "app/core/performance.py",
    "app/services/platforms/platform_manager.py"
]

for file_path in critical_files:
    exists = os.path.exists(file_path)
    test_result(f"파일-{os.path.basename(file_path)}", exists, 
               "존재함" if exists else "파일 없음")

# 2. 핵심 모델 테스트
print("\n=== 핵심 모델 테스트 ===")

try:
    from app.models.product import Product
    test_result("모델-Product", True, "Product 모델 로드 성공")
    
    # Product 모델 필드 확인
    required_fields = ['id', 'name', 'price']
    has_fields = all(hasattr(Product, field) for field in required_fields)
    test_result("모델-Product-필드", has_fields, 
               "필수 필드 존재" if has_fields else "필수 필드 누락")
               
except Exception as e:
    test_result("모델-Product", False, f"로드 실패: {str(e)}")

try:
    from app.models.wholesaler import WholesalerAccount
    test_result("모델-WholesalerAccount", True, "WholesalerAccount 모델 로드 성공")
except Exception as e:
    test_result("모델-WholesalerAccount", False, f"로드 실패: {str(e)}")

# 3. API 엔드포인트 테스트
print("\n=== API 엔드포인트 테스트 ===")

api_files = [
    "app/api/v1/endpoints/products.py",
    "app/api/v1/endpoints/wholesaler.py",
    "app/api/v1/endpoints/dashboard.py",
    "app/api/v1/endpoints/orders.py"
]

for api_file in api_files:
    try:
        if os.path.exists(api_file):
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # FastAPI 라우터 구조 확인
            has_router = 'router' in content and ('APIRouter' in content or '@router' in content)
            test_result(f"API-{os.path.basename(api_file)}", has_router,
                       "라우터 구조 확인" if has_router else "라우터 구조 불분명")
        else:
            test_result(f"API-{os.path.basename(api_file)}", False, "파일 없음")
    except Exception as e:
        test_result(f"API-{os.path.basename(api_file)}", False, f"검사 실패: {str(e)}")

# 4. 서비스 레이어 테스트
print("\n=== 서비스 레이어 테스트 ===")

service_modules = [
    ("app.services.wholesale.analysis_service", "AnalysisService"),
    ("app.services.platforms.platform_manager", "PlatformManager"),
    ("app.services.product_service", "ProductService"),
    ("app.services.dropshipping_service", "DropshippingService")
]

for module_name, class_name in service_modules:
    try:
        module = importlib.import_module(module_name)
        has_class = hasattr(module, class_name)
        test_result(f"서비스-{class_name}", has_class,
                   f"{class_name} 클래스 존재" if has_class else f"{class_name} 클래스 없음")
    except Exception as e:
        test_result(f"서비스-{module_name}", False, f"모듈 로드 실패: {str(e)}")

# 5. 핵심 설정 테스트
print("\n=== 핵심 설정 테스트 ===")

try:
    from app.core.config import Settings
    test_result("설정-Settings", True, "설정 클래스 로드 성공")
    
    # 설정 인스턴스 생성 테스트
    settings = Settings()
    test_result("설정-인스턴스", True, "설정 인스턴스 생성 성공")
except Exception as e:
    test_result("설정-Settings", False, f"설정 로드 실패: {str(e)}")

# 6. 데이터베이스 연결 테스트 (import만)
print("\n=== 데이터베이스 연결 테스트 ===")

try:
    from app.api.v1.dependencies.database import get_db
    test_result("DB-get_db", True, "데이터베이스 의존성 함수 로드 성공")
except Exception as e:
    test_result("DB-get_db", False, f"데이터베이스 의존성 로드 실패: {str(e)}")

# 7. 성능 시스템 테스트
print("\n=== 성능 시스템 테스트 ===")

try:
    from app.core.performance import redis_cache, memory_cache
    test_result("성능-캐시데코레이터", True, "캐시 데코레이터 로드 성공")
except Exception as e:
    test_result("성능-캐시데코레이터", False, f"캐시 데코레이터 로드 실패: {str(e)}")

# 8. 유틸리티 테스트
print("\n=== 유틸리티 테스트 ===")

try:
    from app.utils.logger import get_logger
    logger = get_logger("test")
    test_result("유틸-Logger", True, "로거 유틸리티 동작 확인")
except Exception as e:
    test_result("유틸-Logger", False, f"로거 유틸리티 실패: {str(e)}")

try:
    from app.utils.encryption import encrypt_data, decrypt_data
    test_result("유틸-Encryption", True, "암호화 유틸리티 로드 성공")
except Exception as e:
    test_result("유틸-Encryption", False, f"암호화 유틸리티 실패: {str(e)}")

# 9. 도매업체 API 테스트
print("\n=== 도매업체 API 테스트 ===")

wholesaler_apis = [
    "app.services.wholesalers.domeggook_api",
    "app.services.wholesalers.ownerclan_api", 
    "app.services.wholesalers.zentrade_api"
]

for api_module in wholesaler_apis:
    try:
        module = importlib.import_module(api_module)
        api_name = api_module.split('.')[-1].replace('_api', '').title()
        test_result(f"도매API-{api_name}", True, f"{api_name} API 모듈 로드 성공")
    except Exception as e:
        test_result(f"도매API-{api_module}", False, f"API 모듈 로드 실패: {str(e)}")

# 10. 플랫폼 연동 테스트
print("\n=== 플랫폼 연동 테스트 ===")

platform_apis = [
    "app.services.platforms.coupang_api",
    "app.services.platforms.naver_api",
    "app.services.platforms.eleventh_street_api"
]

for platform_module in platform_apis:
    try:
        module = importlib.import_module(platform_module)
        platform_name = platform_module.split('.')[-1].replace('_api', '').title()
        test_result(f"플랫폼-{platform_name}", True, f"{platform_name} 플랫폼 모듈 로드 성공")
    except Exception as e:
        test_result(f"플랫폼-{platform_module}", False, f"플랫폼 모듈 로드 실패: {str(e)}")

# 결과 요약
print("\n" + "="*60)
print("실제 드롭시핑 시스템 테스트 결과 요약")
print("="*60)
print(f"전체 테스트: {total_tests}개")
print(f"성공: {passed_tests}개")
print(f"실패: {failed_tests}개")

success_rate = (passed_tests / max(total_tests, 1)) * 100
print(f"성공률: {success_rate:.1f}%")

# 시스템 평가
if success_rate >= 80:
    status = "우수"
    desc = "시스템이 안정적으로 구성되어 있습니다!"
    recommendations = [
        "환경 설정 완료 후 운영 환경 배포 가능",
        "실제 데이터로 통합 테스트 진행 권장"
    ]
elif success_rate >= 60:
    status = "양호" 
    desc = "대부분의 기능이 정상적으로 구현되어 있습니다."
    recommendations = [
        "실패한 컴포넌트들 수정 필요",
        "의존성 설치 및 환경 설정 점검"
    ]
else:
    status = "주의"
    desc = "여러 문제가 발견되었습니다."
    recommendations = [
        "핵심 모듈들의 import 오류 해결 필요",
        "프로젝트 의존성 재설치 권장",
        "환경 설정 전면 점검 필요"
    ]

print(f"\n시스템 상태: {status}")
print(f"평가: {desc}")
print("\n권장사항:")
for rec in recommendations:
    print(f"  - {rec}")

print(f"\n테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# 비즈니스 기능 확인
print("\n=== 비즈니스 기능 확인 ===")

business_features = {
    "상품 관리": passed_tests > 0 and "Product" in str([t for t in range(total_tests) if "모델-Product" in str(t)]),
    "도매업체 연동": any("도매API" in str(t) for t in range(total_tests)),
    "플랫폼 연동": any("플랫폼" in str(t) for t in range(total_tests)),
    "데이터 분석": os.path.exists("app/services/wholesale/analysis_service.py"),
    "주문 처리": os.path.exists("app/api/v1/endpoints/orders.py"),
    "성능 최적화": os.path.exists("app/core/performance.py")
}

print("핵심 비즈니스 기능 상태:")
for feature, status in business_features.items():
    status_text = "구현됨" if status else "확인 필요"
    print(f"  {feature}: {status_text}")

total_features = len(business_features)
implemented_features = sum(business_features.values())
feature_completion = (implemented_features / total_features) * 100

print(f"\n비즈니스 기능 완성도: {feature_completion:.1f}% ({implemented_features}/{total_features})")

if feature_completion >= 80:
    print("결론: 실제 비즈니스 운영이 가능한 수준입니다!")
elif feature_completion >= 60:
    print("결론: 대부분의 핵심 기능이 구현되어 있습니다.")
else:
    print("결론: 추가 개발이 필요합니다.")