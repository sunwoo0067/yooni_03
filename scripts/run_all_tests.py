#!/usr/bin/env python3
"""
통합 테스트 실행 스크립트

백엔드와 프론트엔드 테스트를 통합하여 실행하고
커버리지 리포트를 생성하는 마스터 스크립트입니다.
"""

import os
import sys
import subprocess
import json
import argparse
from datetime import datetime
from pathlib import Path
import concurrent.futures
import time


class MasterTestRunner:
    """마스터 테스트 실행 클래스"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.scripts_dir = self.project_root / "scripts"
        
    def run_backend_tests(self, args: argparse.Namespace) -> dict:
        """백엔드 테스트 실행"""
        print("🔧 백엔드 테스트 실행 중...")
        
        cmd = ["python", "run_tests.py"]
        
        if args.parallel:
            cmd.append("--parallel")
        if args.performance:
            cmd.append("--performance")
        if args.quiet:
            cmd.append("--quiet")
        if args.ci:
            cmd.append("--ci")
        if args.min_coverage:
            cmd.extend(["--min-coverage", str(args.min_coverage)])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30분 타임아웃
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "duration": round(duration, 2),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": "백엔드 테스트 타임아웃 (30분)",
                "returncode": 124
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    def run_frontend_tests(self, args: argparse.Namespace) -> dict:
        """프론트엔드 테스트 실행"""
        print("🌐 프론트엔드 테스트 실행 중...")
        
        start_time = time.time()
        
        try:
            # 먼저 의존성 설치 확인
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "duration": time.time() - start_time,
                    "stdout": result.stdout,
                    "stderr": f"npm install 실패: {result.stderr}",
                    "returncode": result.returncode
                }
            
            # 테스트 실행
            test_cmd = ["npm", "run", "test:coverage"]
            if args.ci:
                test_cmd.extend(["--", "--reporter=json"])
            
            result = subprocess.run(
                test_cmd,
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "duration": round(duration, 2),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": "프론트엔드 테스트 타임아웃",
                "returncode": 124
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    def run_e2e_tests(self, args: argparse.Namespace) -> dict:
        """E2E 테스트 실행"""
        print("🎭 E2E 테스트 실행 중...")
        
        start_time = time.time()
        
        try:
            # Playwright 테스트 실행
            result = subprocess.run(
                ["npx", "playwright", "test", "tests/e2e/"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=900  # 15분 타임아웃
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "duration": round(duration, 2),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": "E2E 테스트 타임아웃",
                "returncode": 124
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    def generate_coverage_report(self, args: argparse.Namespace) -> dict:
        """커버리지 리포트 생성"""
        print("📊 통합 커버리지 리포트 생성 중...")
        
        cmd = ["python", "generate_coverage_report.py"]
        
        if args.format:
            cmd.extend(["--format", args.format])
        if args.trend_days:
            cmd.extend(["--trend-days", str(args.trend_days)])
        if args.ci:
            cmd.append("--ci")
        if args.quiet:
            cmd.append("--quiet")
        
        threshold_config = self.scripts_dir / "coverage_thresholds.json"
        if threshold_config.exists():
            cmd.extend(["--threshold-config", str(threshold_config)])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.scripts_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "duration": round(duration, 2),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": "커버리지 리포트 생성 타임아웃",
                "returncode": 124
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    def run_parallel_tests(self, args: argparse.Namespace) -> dict:
        """병렬 테스트 실행"""
        print("🚀 병렬 테스트 실행 중...")
        
        max_workers = 2  # 백엔드, 프론트엔드 동시 실행
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 백엔드와 프론트엔드 테스트 병렬 실행
            futures = {
                "backend": executor.submit(self.run_backend_tests, args),
                "frontend": executor.submit(self.run_frontend_tests, args)
            }
            
            # E2E 테스트는 선택사항
            if args.e2e:
                futures["e2e"] = executor.submit(self.run_e2e_tests, args)
            
            # 결과 수집
            for test_type, future in futures.items():
                try:
                    results[test_type] = future.result()
                    status = "✅" if results[test_type]["success"] else "❌"
                    duration = results[test_type]["duration"]
                    print(f"{status} {test_type} 완료 ({duration:.2f}초)")
                except Exception as e:
                    results[test_type] = {
                        "success": False,
                        "duration": 0,
                        "stdout": "",
                        "stderr": str(e),
                        "returncode": 1
                    }
                    print(f"❌ {test_type} 실패: {e}")
        
        return results
    
    def run_sequential_tests(self, args: argparse.Namespace) -> dict:
        """순차 테스트 실행"""
        print("📋 순차 테스트 실행 중...")
        
        results = {}
        
        # 백엔드 테스트
        results["backend"] = self.run_backend_tests(args)
        
        # 프론트엔드 테스트
        results["frontend"] = self.run_frontend_tests(args)
        
        # E2E 테스트 (선택사항)
        if args.e2e and results["backend"]["success"] and results["frontend"]["success"]:
            results["e2e"] = self.run_e2e_tests(args)
        
        return results
    
    def generate_final_report(self, test_results: dict, coverage_result: dict, args: argparse.Namespace) -> dict:
        """최종 리포트 생성"""
        total_duration = sum(result.get("duration", 0) for result in test_results.values())
        if coverage_result:
            total_duration += coverage_result.get("duration", 0)
        
        all_success = all(result.get("success", False) for result in test_results.values())
        if coverage_result:
            all_success = all_success and coverage_result.get("success", False)
        
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "success": all_success,
            "total_duration": round(total_duration, 2),
            "test_results": test_results,
            "coverage_result": coverage_result,
            "summary": {
                "tests_run": len(test_results),
                "tests_passed": sum(1 for r in test_results.values() if r.get("success", False)),
                "tests_failed": sum(1 for r in test_results.values() if not r.get("success", False)),
                "coverage_generated": coverage_result.get("success", False) if coverage_result else False
            }
        }
        
        return final_report
    
    def print_summary(self, final_report: dict, args: argparse.Namespace):
        """결과 요약 출력"""
        if args.quiet:
            return
        
        print("\n" + "=" * 80)
        print("🏁 테스트 실행 완료")
        print("=" * 80)
        
        summary = final_report["summary"]
        print(f"📅 실행 시간: {final_report['timestamp']}")
        print(f"⏱️  총 소요 시간: {final_report['total_duration']:.2f}초")
        print(f"📊 테스트 결과: {summary['tests_passed']}/{summary['tests_run']} 성공")
        
        if summary["coverage_generated"]:
            print("📈 커버리지 리포트: 생성 완료")
        
        print("\n상세 결과:")
        print("-" * 80)
        
        for test_type, result in final_report["test_results"].items():
            status = "✅ 성공" if result["success"] else "❌ 실패"
            duration = result["duration"]
            print(f"{test_type:>12}: {status} ({duration:.2f}초)")
            
            if not result["success"] and result["stderr"]:
                print(f"             오류: {result['stderr'][:100]}...")
        
        if final_report["coverage_result"]:
            coverage = final_report["coverage_result"]
            status = "✅ 성공" if coverage["success"] else "❌ 실패"
            print(f"{'coverage':>12}: {status} ({coverage['duration']:.2f}초)")
        
        print("\n" + "=" * 80)
        
        if final_report["success"]:
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            print("⚠️  일부 테스트가 실패했습니다. 상세 내용을 확인해주세요.")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="드랍쉬핑 시스템 통합 테스트 실행 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run_all_tests.py                    # 기본 실행
  python run_all_tests.py --parallel         # 병렬 실행
  python run_all_tests.py --e2e              # E2E 테스트 포함
  python run_all_tests.py --ci               # CI/CD 모드
  python run_all_tests.py --coverage-only    # 커버리지만 생성
        """
    )
    
    # 실행 옵션
    parser.add_argument("--parallel", action="store_true", help="병렬 테스트 실행")
    parser.add_argument("--e2e", action="store_true", help="E2E 테스트 포함")
    parser.add_argument("--performance", action="store_true", help="성능 테스트 포함")
    parser.add_argument("--coverage-only", action="store_true", help="커버리지 리포트만 생성")
    
    # 출력 및 형식 옵션
    parser.add_argument("--ci", action="store_true", help="CI/CD 모드")
    parser.add_argument("--quiet", "-q", action="store_true", help="최소 출력")
    parser.add_argument("--format", choices=["json", "html", "both"], default="both", help="리포트 형식")
    
    # 커버리지 옵션
    parser.add_argument("--min-coverage", type=float, default=80.0, help="최소 커버리지 임계값")
    parser.add_argument("--trend-days", type=int, default=30, help="트렌드 분석 기간")
    
    # 출력 파일 옵션
    parser.add_argument("--output", help="결과 출력 파일 경로")
    
    args = parser.parse_args()
    
    try:
        runner = MasterTestRunner()
        
        if not args.quiet:
            print("🚀 드랍쉬핑 시스템 통합 테스트 시작")
            print("=" * 80)
            print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
        
        # 커버리지만 생성하는 경우
        if args.coverage_only:
            coverage_result = runner.generate_coverage_report(args)
            success = coverage_result.get("success", False)
            
            if args.ci:
                output = {
                    "success": success,
                    "coverage_result": coverage_result,
                    "timestamp": datetime.now().isoformat()
                }
                print(json.dumps(output, indent=2, ensure_ascii=False))
            
            sys.exit(0 if success else 1)
        
        # 테스트 실행
        if args.parallel:
            test_results = runner.run_parallel_tests(args)
        else:
            test_results = runner.run_sequential_tests(args)
        
        # 커버리지 리포트 생성
        coverage_result = runner.generate_coverage_report(args)
        
        # 최종 리포트 생성
        final_report = runner.generate_final_report(test_results, coverage_result, args)
        
        # 결과 출력
        if args.ci:
            print(json.dumps(final_report, indent=2, ensure_ascii=False))
        else:
            runner.print_summary(final_report, args)
        
        # 결과 파일 저장
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)
            if not args.quiet:
                print(f"\\n📄 결과 파일 저장: {output_path}")
        
        # 종료 코드 결정
        sys.exit(0 if final_report["success"] else 1)
        
    except KeyboardInterrupt:
        print("\\n\\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\\n💥 예상치 못한 오류: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()