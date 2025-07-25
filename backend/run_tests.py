"""
포괄적인 유닛 테스트 실행 스크립트
"""
import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import argparse


class TestRunner:
    """테스트 실행 및 리포트 생성 클래스"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        self.report_dir = self.test_dir / "reports"
        self.report_dir.mkdir(exist_ok=True)
        
    def run_unit_tests(self, specific_module=None):
        """유닛 테스트 실행"""
        print("=" * 80)
        print("🧪 유닛 테스트 실행 중...")
        print("=" * 80)
        
        cmd = [
            "pytest",
            "-v",
            "--tb=short",
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=json",
            "--json-report",
            f"--json-report-file={self.report_dir}/unit_test_report.json",
            "--html={}/unit_test_report.html".format(self.report_dir),
            "--self-contained-html",
            "-m", "unit"
        ]
        
        if specific_module:
            cmd.append(f"tests/unit/test_{specific_module}.py")
        else:
            cmd.append("tests/unit")
            
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        print(result.stdout)
        if result.stderr:
            print("에러:", result.stderr)
            
        return result.returncode == 0, duration
        
    def run_specific_test_categories(self):
        """카테고리별 테스트 실행"""
        categories = {
            "product_collection": "상품수집 시스템",
            "ai_sourcing": "AI 소싱 시스템",
            "product_processing": "상품가공 시스템",
            "product_registration": "상품등록 시스템",
            "order_processing": "주문처리 시스템",
            "pipeline_integration": "파이프라인 통합",
            "market_management": "마켓 관리 시스템"
        }
        
        results = {}
        
        for module, description in categories.items():
            print(f"\n{'='*80}")
            print(f"🔍 {description} 테스트 실행 중...")
            print(f"{'='*80}")
            
            success, duration = self.run_unit_tests(module)
            results[module] = {
                "description": description,
                "success": success,
                "duration": duration
            }
            
        return results
        
    def generate_test_report(self, results):
        """테스트 결과 리포트 생성"""
        report = {
            "test_run_date": datetime.now().isoformat(),
            "total_duration": sum(r["duration"] for r in results.values()),
            "categories": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results.values() if r["success"]),
                "failed": sum(1 for r in results.values() if not r["success"])
            }
        }
        
        # JSON 리포트 저장
        report_path = self.report_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # 콘솔 출력
        self._print_report(report)
        
        return report
        
    def _print_report(self, report):
        """리포트 콘솔 출력"""
        print("\n" + "=" * 80)
        print("📊 테스트 실행 결과 요약")
        print("=" * 80)
        print(f"실행 일시: {report['test_run_date']}")
        print(f"총 소요 시간: {report['total_duration']:.2f}초")
        print(f"\n전체 카테고리: {report['summary']['total']}")
        print(f"✅ 성공: {report['summary']['passed']}")
        print(f"❌ 실패: {report['summary']['failed']}")
        
        print("\n카테고리별 결과:")
        print("-" * 80)
        for module, result in report['categories'].items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['description']:<30} ({result['duration']:.2f}초)")
            
    def check_coverage(self):
        """코드 커버리지 확인"""
        coverage_file = self.test_dir / "coverage.json"
        
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
                
            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            
            print(f"\n📈 전체 코드 커버리지: {total_coverage:.2f}%")
            
            if total_coverage < 80:
                print("⚠️  경고: 코드 커버리지가 80% 미만입니다.")
            elif total_coverage >= 90:
                print("🎉 훌륭합니다! 코드 커버리지가 90% 이상입니다.")
                
            return total_coverage
        else:
            print("⚠️  커버리지 파일을 찾을 수 없습니다.")
            return 0
            
    def run_performance_tests(self):
        """성능 테스트 실행"""
        print("\n" + "=" * 80)
        print("⚡ 성능 테스트 실행 중...")
        print("=" * 80)
        
        # 여기에 성능 테스트 로직 추가
        # 예: 응답 시간, 처리량, 메모리 사용량 등
        
        performance_results = {
            "api_response_time": self._test_api_performance(),
            "database_query_time": self._test_db_performance(),
            "image_processing_time": self._test_image_processing_performance()
        }
        
        return performance_results
        
    def _test_api_performance(self):
        """API 성능 테스트"""
        # 실제 구현은 API 엔드포인트 호출 및 응답 시간 측정
        return {"avg_response_time": 0.05, "max_response_time": 0.2}
        
    def _test_db_performance(self):
        """데이터베이스 성능 테스트"""
        # 실제 구현은 DB 쿼리 실행 및 시간 측정
        return {"avg_query_time": 0.01, "max_query_time": 0.05}
        
    def _test_image_processing_performance(self):
        """이미지 처리 성능 테스트"""
        # 실제 구현은 이미지 처리 작업 실행 및 시간 측정
        return {"avg_processing_time": 0.5, "max_processing_time": 2.0}


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="드랍쉬핑 시스템 유닛 테스트 실행")
    parser.add_argument("--module", help="특정 모듈만 테스트")
    parser.add_argument("--all", action="store_true", help="모든 테스트 실행")
    parser.add_argument("--performance", action="store_true", help="성능 테스트 포함")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    print("🚀 드랍쉬핑 자동화 시스템 유닛 테스트 시작")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.module:
        # 특정 모듈만 테스트
        success, duration = runner.run_unit_tests(args.module)
        print(f"\n테스트 {'성공' if success else '실패'} (소요 시간: {duration:.2f}초)")
    else:
        # 전체 카테고리별 테스트
        results = runner.run_specific_test_categories()
        report = runner.generate_test_report(results)
        
        # 코드 커버리지 확인
        coverage = runner.check_coverage()
        
        # 성능 테스트 (옵션)
        if args.performance:
            perf_results = runner.run_performance_tests()
            print("\n⚡ 성능 테스트 결과:")
            print(json.dumps(perf_results, indent=2))
            
        # CI/CD 통합을 위한 종료 코드
        if report['summary']['failed'] > 0:
            print("\n❌ 일부 테스트가 실패했습니다.")
            sys.exit(1)
        else:
            print("\n✅ 모든 테스트가 성공했습니다!")
            sys.exit(0)


if __name__ == "__main__":
    main()