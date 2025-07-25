# -*- coding: utf-8 -*-
"""
Simple Test Runner for Dropshipping System
간단한 테스트 실행기
"""
import os
import sys
import importlib
from datetime import datetime

print("=== SuperClaude 드롭시핑 시스템 테스트 ===")
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

# 1. 파일 구조 테스트
print("\n=== 파일 구조 테스트 ===")

critical_files = [
    "app/models/wholesale.py",
    "app/api/wholesale.py", 
    "app/services/wholesale/profitability_analyzer.py",
    "app/core/performance.py",
    "app/services/notifications/notification_service.py",
    "app/core/optimization_config.py"
]

for file_path in critical_files:
    exists = os.path.exists(file_path)
    test_result(f"파일-{os.path.basename(file_path)}", exists, 
               "존재함" if exists else "파일 없음")

# 2. 문법 검사
print("\n=== 문법 검사 ===")

key_files = [
    "app/models/wholesale.py",
    "app/core/performance.py"
]

for file_path in key_files:
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                compile(content, file_path, 'exec')
            test_result(f"문법-{os.path.basename(file_path)}", True, "문법 올바름")
        else:
            test_result(f"문법-{os.path.basename(file_path)}", False, "파일 없음")
    except Exception as e:
        test_result(f"문법-{os.path.basename(file_path)}", False, f"오류: {str(e)}")

# 3. Import 테스트
print("\n=== Import 테스트 ===")

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import_tests = [
    ("app.models.wholesale", "WholesaleSupplier"),
    ("app.core.performance", "redis_cache")
]

for module_name, item_name in import_tests:
    try:
        module = importlib.import_module(module_name)
        has_item = hasattr(module, item_name)
        test_result(f"Import-{module_name}.{item_name}", has_item,
                   "Import 성공" if has_item else f"{item_name} 없음")
    except Exception as e:
        test_result(f"Import-{module_name}", False, f"Import 실패: {str(e)}")

# 4. 모델 구조 테스트
print("\n=== 모델 구조 테스트 ===")

try:
    from app.models.wholesale import WholesaleSupplier
    
    # 테이블명 확인
    has_table = hasattr(WholesaleSupplier, '__tablename__')
    test_result("모델-WholesaleSupplier-테이블명", has_table,
               f"테이블: {WholesaleSupplier.__tablename__}" if has_table else "테이블명 없음")
    
    # 필수 필드 확인
    required_fields = ['id', 'supplier_name', 'supplier_code']
    missing_fields = [f for f in required_fields if not hasattr(WholesaleSupplier, f)]
    
    test_result("모델-WholesaleSupplier-필드", len(missing_fields) == 0,
               "모든 필드 존재" if len(missing_fields) == 0 else f"누락: {missing_fields}")
               
except Exception as e:
    test_result("모델-WholesaleSupplier", False, f"로드 실패: {str(e)}")

# 5. API 파일 구조 테스트
print("\n=== API 구조 테스트 ===")

api_files = [
    "app/api/wholesale.py",
    "app/api/notifications.py",
    "app/api/performance.py"
]

for api_file in api_files:
    try:
        if os.path.exists(api_file):
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_router = 'APIRouter' in content and 'router' in content
            test_result(f"API-{os.path.basename(api_file)}", has_router,
                       "라우터 구조 확인" if has_router else "라우터 구조 불분명")
        else:
            test_result(f"API-{os.path.basename(api_file)}", False, "파일 없음")
    except Exception as e:
        test_result(f"API-{os.path.basename(api_file)}", False, f"검사 실패: {str(e)}")

# 6. 성능 시스템 테스트
print("\n=== 성능 시스템 테스트 ===")

try:
    from app.core.performance import redis_cache, memory_cache
    test_result("성능-데코레이터-redis_cache", callable(redis_cache), "Redis 캐시 데코레이터")
    test_result("성능-데코레이터-memory_cache", callable(memory_cache), "메모리 캐시 데코레이터")
except Exception as e:
    test_result("성능-데코레이터", False, f"로드 실패: {str(e)}")

try:
    from app.core.optimization_config import optimization_settings
    has_cache_config = hasattr(optimization_settings, 'cache')
    test_result("성능-최적화설정", has_cache_config, "최적화 설정 로드됨")
except Exception as e:
    test_result("성능-최적화설정", False, f"설정 로드 실패: {str(e)}")

# 결과 요약
print("\n" + "="*50)
print("테스트 결과 요약")
print("="*50)
print(f"전체 테스트: {total_tests}개")
print(f"성공: {passed_tests}개")
print(f"실패: {failed_tests}개")

success_rate = (passed_tests / max(total_tests, 1)) * 100
print(f"성공률: {success_rate:.1f}%")

if success_rate >= 80:
    print("결과: 우수 - 시스템이 안정적입니다!")
elif success_rate >= 60:
    print("결과: 양호 - 일부 개선이 필요합니다.")
else:
    print("결과: 주의 - 문제가 발견되었습니다.")

print(f"\n테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*50)