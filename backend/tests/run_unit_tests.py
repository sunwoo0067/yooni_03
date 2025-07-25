"""
유닛 테스트 실행 스크립트
"""
import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path


def run_tests():
    """전체 유닛 테스트 실행"""
    print("=" * 80)
    print("드랍쉬핑 자동화 시스템 유닛 테스트 실행")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    test_categories = {
        "sample": "샘플 테스트",
        "product_collection": "상품수집 시스템",
        "ai_sourcing": "AI 소싱 시스템",
        "product_processing": "상품가공 시스템",
        "product_registration": "상품등록 시스템",
        "order_processing": "주문처리 시스템",
        "pipeline_integration": "파이프라인 통합",
        "market_management": "마켓 관리 시스템"
    }
    
    results = {}
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for module, description in test_categories.items():
        print(f"\n{'='*80}")
        print(f"{description} 테스트 실행 중...")
        print(f"{'='*80}")
        
        test_file = f"tests/unit/test_{module}.py"
        
        # 파일이 존재하는지 확인
        if not Path(test_file).exists():
            print(f"WARNING: {test_file} 파일을 찾을 수 없습니다.")
            continue
            
        start_time = time.time()
        
        # pytest 실행
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--no-header",
            "-q"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = time.time() - start_time
            
            # 결과 파싱
            output = result.stdout
            if "passed" in output:
                # 성공한 테스트 수 추출
                import re
                match = re.search(r'(\d+) passed', output)
                if match:
                    passed_count = int(match.group(1))
                    passed_tests += passed_count
                    total_tests += passed_count
                    
                results[module] = {
                    "description": description,
                    "status": "PASSED",
                    "duration": f"{duration:.2f}초",
                    "passed": passed_count
                }
                print(f"성공: {passed_count}개 테스트 통과")
            else:
                results[module] = {
                    "description": description,
                    "status": "FAILED",
                    "duration": f"{duration:.2f}초",
                    "error": result.stderr
                }
                failed_tests += 1
                print(f"실패: {result.stderr}")
                
        except Exception as e:
            results[module] = {
                "description": description,
                "status": "ERROR",
                "error": str(e)
            }
            print(f"에러 발생: {e}")
    
    # 최종 리포트 출력
    print("\n" + "=" * 80)
    print("테스트 실행 결과 요약")
    print("=" * 80)
    print(f"총 테스트: {total_tests}")
    print(f"성공: {passed_tests}")
    print(f"실패: {failed_tests}")
    print(f"성공률: {(passed_tests/total_tests*100 if total_tests > 0 else 0):.1f}%")
    
    print("\n카테고리별 결과:")
    print("-" * 80)
    for module, result in results.items():
        print(f"{result['status']} {result['description']:<30} ({result.get('duration', 'N/A')})")
    
    # JSON 리포트 저장
    report = {
        "test_run_date": datetime.now().isoformat(),
        "summary": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": passed_tests/total_tests*100 if total_tests > 0 else 0
        },
        "categories": results
    }
    
    report_path = Path("tests/reports")
    report_path.mkdir(exist_ok=True)
    
    with open(report_path / f"unit_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n리포트 저장됨: {report_path}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)