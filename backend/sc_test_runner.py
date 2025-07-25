#!/usr/bin/env python3
"""
SuperClaude 테스트 실행기
드롭시핑 시스템의 핵심 기능을 체계적으로 테스트
"""
import os
import sys
import importlib
import traceback
from datetime import datetime
from typing import Dict, List, Any
import json

# 결과 저장
results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0}
}

def log_result(test_name: str, status: str, message: str, details: Any = None):
    """테스트 결과 로깅"""
    results["tests"].append({
        "name": test_name,
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    
    results["summary"]["total"] += 1
    if status == "PASS":
        results["summary"]["passed"] += 1
        print(f"[PASS] {test_name}: {message}")
    elif status == "FAIL":
        results["summary"]["failed"] += 1
        print(f"[FAIL] {test_name}: {message}")
    elif status == "WARN":
        results["summary"]["warnings"] += 1
        print(f"[WARN] {test_name}: {message}")

def test_file_structure():
    """파일 구조 테스트"""
    print("\n[INFO] 파일 구조 검증...")
    
    critical_files = [
        "app/models/wholesale.py",
        "app/api/wholesale.py", 
        "app/services/wholesale/profitability_analyzer.py",
        "app/core/performance.py",
        "app/services/notifications/notification_service.py"
    ]
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            log_result(f"파일존재-{file_path}", "PASS", "파일이 존재합니다")
        else:
            log_result(f"파일존재-{file_path}", "FAIL", "파일이 없습니다")

def test_python_syntax():
    """파이썬 문법 검사"""
    print("\n🐍 파이썬 문법 검증...")
    
    key_files = [
        "app/models/wholesale.py",
        "app/core/performance.py",
        "app/services/wholesale/profitability_analyzer.py"
    ]
    
    for file_path in key_files:
        if os.path.exists(file_path):
            try:
                # 문법 검사
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                compile(content, file_path, 'exec')
                log_result(f"문법검사-{file_path}", "PASS", "문법이 올바릅니다")
                
            except SyntaxError as e:
                log_result(f"문법검사-{file_path}", "FAIL", f"문법 오류: {e}")
            except Exception as e:
                log_result(f"문법검사-{file_path}", "WARN", f"검사 중 오류: {e}")

def test_imports():
    """핵심 모듈 import 테스트"""
    print("\n📦 모듈 import 검증...")
    
    # 프로젝트 경로를 sys.path에 추가
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    import_tests = [
        ("app.models.wholesale", "WholesaleSupplier"),
        ("app.core.performance", "redis_cache"),
        ("app.core.optimization_config", "optimization_settings")
    ]
    
    for module_name, item_name in import_tests:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, item_name):
                log_result(f"Import-{module_name}.{item_name}", "PASS", f"성공적으로 import됨")
            else:
                log_result(f"Import-{module_name}.{item_name}", "FAIL", f"{item_name}이 없음")
        except ImportError as e:
            log_result(f"Import-{module_name}", "FAIL", f"Import 실패: {e}")
        except Exception as e:
            log_result(f"Import-{module_name}", "WARN", f"예상치 못한 오류: {e}")

def test_class_definitions():
    """클래스 정의 테스트"""
    print("\n🏗️ 클래스 정의 검증...")
    
    try:
        # 핵심 클래스들 확인
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # 모델 클래스 테스트
        try:
            from app.models.wholesale import WholesaleSupplier, WholesaleProduct
            log_result("클래스-WholesaleSupplier", "PASS", "클래스 정의됨")
            log_result("클래스-WholesaleProduct", "PASS", "클래스 정의됨")
        except Exception as e:
            log_result("클래스-Wholesale모델", "FAIL", f"모델 클래스 로드 실패: {e}")
        
        # 서비스 클래스 테스트  
        try:
            from app.services.wholesale.profitability_analyzer import ProfitabilityAnalyzer
            log_result("클래스-ProfitabilityAnalyzer", "PASS", "클래스 정의됨")
        except Exception as e:
            log_result("클래스-ProfitabilityAnalyzer", "FAIL", f"분석기 클래스 로드 실패: {e}")
            
    except Exception as e:
        log_result("클래스정의", "FAIL", f"클래스 정의 테스트 실패: {e}")

def test_database_models():
    """데이터베이스 모델 테스트"""
    print("\n🗄️ 데이터베이스 모델 검증...")
    
    try:
        from app.models.wholesale import WholesaleSupplier, WholesaleProduct
        
        # 테이블명 확인
        if hasattr(WholesaleSupplier, '__tablename__'):
            log_result("모델-WholesaleSupplier테이블", "PASS", f"테이블명: {WholesaleSupplier.__tablename__}")
        else:
            log_result("모델-WholesaleSupplier테이블", "FAIL", "테이블명이 정의되지 않음")
            
        # 필수 필드 확인
        required_fields = ['id', 'supplier_name', 'supplier_code']
        missing_fields = [f for f in required_fields if not hasattr(WholesaleSupplier, f)]
        
        if not missing_fields:
            log_result("모델-WholesaleSupplier필드", "PASS", "모든 필수 필드 존재")
        else:
            log_result("모델-WholesaleSupplier필드", "FAIL", f"누락된 필드: {missing_fields}")
            
    except Exception as e:
        log_result("데이터베이스모델", "FAIL", f"모델 테스트 실패: {e}")

def test_api_structure():
    """API 구조 테스트"""
    print("\n🌐 API 구조 검증...")
    
    api_files = [
        "app/api/wholesale.py",
        "app/api/notifications.py", 
        "app/api/reports.py",
        "app/api/performance.py"
    ]
    
    for api_file in api_files:
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # FastAPI 라우터 확인
                if 'APIRouter' in content and 'router =' in content:
                    log_result(f"API-{api_file}", "PASS", "FastAPI 라우터 구조 확인됨")
                else:
                    log_result(f"API-{api_file}", "WARN", "라우터 구조를 확인할 수 없음")
                    
            except Exception as e:
                log_result(f"API-{api_file}", "FAIL", f"API 파일 검사 실패: {e}")
        else:
            log_result(f"API-{api_file}", "FAIL", "API 파일이 존재하지 않음")

def test_performance_system():
    """성능 시스템 테스트"""
    print("\n⚡ 성능 시스템 검증...")
    
    try:
        from app.core.performance import redis_cache, memory_cache, performance_monitor
        log_result("성능-데코레이터", "PASS", "성능 데코레이터들이 로드됨")
        
        from app.core.optimization_config import optimization_settings
        log_result("성능-최적화설정", "PASS", "최적화 설정이 로드됨")
        
        # 설정값 확인
        if hasattr(optimization_settings, 'cache'):
            log_result("성능-캐시설정", "PASS", "캐시 설정이 존재함")
        else:
            log_result("성능-캐시설정", "FAIL", "캐시 설정이 없음")
            
    except Exception as e:
        log_result("성능시스템", "FAIL", f"성능 시스템 테스트 실패: {e}")

def generate_report():
    """테스트 리포트 생성"""
    print("\n📊 테스트 리포트 생성...")
    
    total = results["summary"]["total"]
    passed = results["summary"]["passed"]
    failed = results["summary"]["failed"]
    warnings = results["summary"]["warnings"]
    
    success_rate = (passed / max(total, 1)) * 100
    
    print(f"\n{'='*60}")
    print("🧪 SuperClaude 드롭시핑 시스템 테스트 결과")
    print(f"{'='*60}")
    print(f"📅 테스트 시간: {results['timestamp']}")
    print(f"📊 전체 테스트: {total}개")
    print(f"✅ 성공: {passed}개")
    print(f"❌ 실패: {failed}개") 
    print(f"⚠️ 경고: {warnings}개")
    print(f"🎯 성공률: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print(f"🎉 결과: 우수 - 시스템이 안정적으로 구성되어 있습니다!")
    elif success_rate >= 60:
        print(f"👍 결과: 양호 - 일부 개선이 필요합니다.")
    else:
        print(f"⚠️ 결과: 주의 - 여러 문제가 발견되었습니다.")
    
    # JSON 파일로 저장
    with open("sc_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 상세 결과가 'sc_test_results.json'에 저장되었습니다.")

def main():
    """메인 실행 함수"""
    print("SuperClaude 드롭시핑 시스템 테스트 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_file_structure()
        test_python_syntax()
        test_imports()
        test_class_definitions() 
        test_database_models()
        test_api_structure()
        test_performance_system()
        
        generate_report()
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        traceback.print_exc()
    
    print("\n🏁 SuperClaude 테스트 완료!")

if __name__ == "__main__":
    main()