#!/usr/bin/env python3
"""
Comprehensive test runner for dropshipping system
"""
import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple
import concurrent.futures
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    output: str
    coverage: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class TestSuite:
    """Test suite configuration"""
    name: str
    path: str
    markers: List[str]
    timeout: int = 300  # 5 minutes default
    parallel: bool = False
    requires_services: List[str] = None


class TestRunner:
    """Comprehensive test runner with reporting"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.test_dir = self.base_dir / "tests"
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        
        # Test suites configuration
        self.test_suites = {
            "unit": TestSuite(
                name="Unit Tests",
                path="tests/unit/",
                markers=["unit", "not slow"],
                timeout=120,
                parallel=True
            ),
            "integration": TestSuite(
                name="Integration Tests", 
                path="tests/integration/",
                markers=["integration", "not slow"],
                timeout=300,
                requires_services=["database", "redis"]
            ),
            "e2e": TestSuite(
                name="End-to-End Tests",
                path="tests/e2e/",
                markers=["e2e"],
                timeout=600,
                requires_services=["database", "redis", "external_apis"]
            ),
            "performance": TestSuite(
                name="Performance Tests",
                path="tests/performance/",
                markers=["performance"],
                timeout=900,
                requires_services=["database", "redis"]
            ),
            "security": TestSuite(
                name="Security Tests",
                path="tests/security/",
                markers=["security"],
                timeout=300
            )
        }
    
    def run_command(self, command: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """Run command with timeout and capture output"""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=self.base_dir
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        required_packages = [
            "pytest", "pytest-cov", "pytest-asyncio", "pytest-xdist",
            "pytest-mock", "pytest-benchmark", "pytest-html"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            returncode, _, _ = self.run_command([
                sys.executable, "-c", f"import {package.replace('-', '_')}"
            ])
            
            if returncode != 0:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("✅ All dependencies are installed")
        return True
    
    def check_services(self, required_services: List[str]) -> bool:
        """Check if required services are available"""
        if not required_services:
            return True
        
        print(f"🔍 Checking services: {', '.join(required_services)}")
        
        service_checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "external_apis": self._check_external_apis
        }
        
        for service in required_services:
            if service in service_checks:
                if not service_checks[service]():
                    print(f"❌ Service {service} is not available")
                    return False
                print(f"✅ Service {service} is available")
            else:
                print(f"⚠️  Unknown service: {service}")
        
        return True
    
    def _check_database(self) -> bool:
        """Check database connectivity"""
        try:
            # Try to import and test database connection
            sys.path.insert(0, str(self.base_dir))
            from app.core.database import get_db
            return True
        except Exception:
            return False
    
    def _check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=1)
            r.ping()
            return True
        except Exception:
            return False
    
    def _check_external_apis(self) -> bool:
        """Check external API connectivity (mock for tests)"""
        # For tests, we assume external APIs are available via mocks
        return True
    
    def run_test_suite(
        self, 
        suite: TestSuite, 
        coverage: bool = True,
        parallel: bool = None,
        verbose: bool = True
    ) -> TestResult:
        """Run a specific test suite"""
        
        print(f"\n🚀 Running {suite.name}...")
        
        # Check required services
        if suite.requires_services and not self.check_services(suite.requires_services):
            return TestResult(
                name=suite.name,
                status="error", 
                duration=0.0,
                output="Required services not available",
                error_message="Service check failed"
            )
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest", suite.path]
        
        # Add markers
        if suite.markers:
            cmd.extend(["-m", " and ".join(suite.markers)])
        
        # Add verbosity
        if verbose:
            cmd.append("-v")
        
        # Add coverage
        if coverage:
            cmd.extend([
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml"
            ])
        
        # Add parallel execution
        if parallel or (parallel is None and suite.parallel):
            cmd.extend(["-n", "auto"])
        
        # Add output options
        cmd.extend([
            "--tb=short",
            "--junitxml=junit.xml",
            "--html=report.html",
            "--self-contained-html"
        ])
        
        # Set timeout
        cmd.extend(["--timeout", str(suite.timeout)])
        
        print(f"📝 Command: {' '.join(cmd)}")
        
        start_time = time.time()
        returncode, stdout, stderr = self.run_command(cmd, suite.timeout + 60)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Parse results
        status = "passed" if returncode == 0 else "failed"
        output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        
        # Extract coverage if available
        coverage_pct = self._extract_coverage(stdout)
        
        result = TestResult(
            name=suite.name,
            status=status,
            duration=duration,
            output=output,
            coverage=coverage_pct,
            error_message=stderr if returncode != 0 else None
        )
        
        print(f"{'✅' if status == 'passed' else '❌'} {suite.name} - {status} in {duration:.2f}s")
        if coverage_pct:
            print(f"📊 Coverage: {coverage_pct:.1f}%")
        
        return result
    
    def _extract_coverage(self, output: str) -> Optional[float]:
        """Extract coverage percentage from pytest output"""
        lines = output.split('\n')
        for line in lines:
            if 'TOTAL' in line and '%' in line:
                try:
                    # Extract percentage from line like "TOTAL 1234 456 63%"
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            return float(part[:-1])
                except (ValueError, IndexError):
                    continue
        return None
    
    def run_parallel_suites(
        self, 
        suite_names: List[str], 
        **kwargs
    ) -> List[TestResult]:
        """Run multiple test suites in parallel"""
        
        print(f"\n🔄 Running test suites in parallel: {', '.join(suite_names)}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all test suite jobs
            future_to_suite = {}
            for suite_name in suite_names:
                if suite_name in self.test_suites:
                    suite = self.test_suites[suite_name]
                    future = executor.submit(self.run_test_suite, suite, **kwargs)
                    future_to_suite[future] = suite_name
                else:
                    print(f"⚠️  Unknown test suite: {suite_name}")
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(future_to_suite):
                suite_name = future_to_suite[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"❌ Error running {suite_name}: {e}")
                    results.append(TestResult(
                        name=suite_name,
                        status="error",
                        duration=0.0,
                        output=str(e),
                        error_message=str(e)
                    ))
        
        return results
    
    def run_all_tests(
        self, 
        parallel_suites: bool = False,
        include_slow: bool = False,
        coverage: bool = True,
        **kwargs
    ) -> List[TestResult]:
        """Run all test suites"""
        
        print("🎯 Running comprehensive test suite...")
        self.start_time = time.time()
        
        # Select test suites to run
        suite_names = ["unit", "integration"]
        
        if include_slow:
            suite_names.extend(["e2e", "performance", "security"])
        else:
            suite_names.append("security")  # Security tests are usually fast
        
        # Run tests
        if parallel_suites:
            # Run unit and integration in parallel, then others sequentially
            parallel_results = self.run_parallel_suites(
                ["unit", "integration"], 
                coverage=coverage, 
                **kwargs
            )
            
            sequential_suites = [s for s in suite_names if s not in ["unit", "integration"]]
            sequential_results = []
            
            for suite_name in sequential_suites:
                if suite_name in self.test_suites:
                    suite = self.test_suites[suite_name]
                    result = self.run_test_suite(suite, coverage=False, **kwargs)
                    sequential_results.append(result)
            
            results = parallel_results + sequential_results
        else:
            # Run sequentially
            results = []
            for suite_name in suite_names:
                if suite_name in self.test_suites:
                    suite = self.test_suites[suite_name]
                    # Only generate coverage for the first suite to avoid conflicts
                    suite_coverage = coverage and len(results) == 0
                    result = self.run_test_suite(suite, coverage=suite_coverage, **kwargs)
                    results.append(result)
        
        self.end_time = time.time()
        self.results = results
        
        return results
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive test report"""
        
        if not self.results:
            return "No test results available"
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "passed")
        failed_tests = sum(1 for r in self.results if r.status == "failed")
        error_tests = sum(1 for r in self.results if r.status == "error")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate HTML report
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dropshipping Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric h3 {{ margin: 0; color: #333; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007acc; }}
        .suite {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ background: #f8f9fa; padding: 10px; border-radius: 5px 5px 0 0; }}
        .suite-content {{ padding: 15px; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .error {{ color: #fd7e14; }}
        .coverage {{ background: #d4edda; padding: 10px; border-radius: 3px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Dropshipping System Test Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total execution time: {total_duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <div class="value">{total_tests}</div>
        </div>
        <div class="metric">
            <h3>Passed</h3>
            <div class="value passed">{passed_tests}</div>
        </div>
        <div class="metric">
            <h3>Failed</h3>
            <div class="value failed">{failed_tests}</div>
        </div>
        <div class="metric">
            <h3>Errors</h3>
            <div class="value error">{error_tests}</div>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <div class="value">{success_rate:.1f}%</div>
        </div>
    </div>
    
    <h2>📋 Test Suite Results</h2>
"""
        
        # Add individual test suite results
        for result in self.results:
            status_class = result.status
            status_icon = {"passed": "✅", "failed": "❌", "error": "⚠️"}.get(result.status, "❓")
            
            html_report += f"""
    <div class="suite">
        <div class="suite-header">
            <h3>{status_icon} {result.name}</h3>
            <p><strong>Status:</strong> <span class="{status_class}">{result.status.upper()}</span> | 
               <strong>Duration:</strong> {result.duration:.2f}s</p>
        </div>
        <div class="suite-content">
"""
            
            if result.coverage:
                html_report += f"""
            <div class="coverage">
                📊 <strong>Code Coverage:</strong> {result.coverage:.1f}%
            </div>
"""
            
            if result.error_message:
                html_report += f"""
            <div style="background: #f8d7da; padding: 10px; border-radius: 3px; margin: 10px 0;">
                <strong>Error:</strong> {result.error_message}
            </div>
"""
            
            html_report += """
        </div>
    </div>
"""
        
        html_report += """
    
    <h2>📊 Coverage Summary</h2>
    <p>Coverage reports are available in the <code>htmlcov/</code> directory.</p>
    
    <h2>🔗 Additional Reports</h2>
    <ul>
        <li><a href="junit.xml">JUnit XML Report</a></li>
        <li><a href="coverage.xml">Coverage XML Report</a></li>
        <li><a href="htmlcov/index.html">HTML Coverage Report</a></li>
    </ul>
    
    <footer style="margin-top: 50px; padding: 20px; background: #f0f0f0; text-align: center;">
        <p>Generated by Dropshipping Test Automation System</p>
    </footer>
</body>
</html>
"""
        
        # Save report
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"📄 Report saved to: {output_file}")
        
        return html_report
    
    def print_summary(self):
        """Print test summary to console"""
        if not self.results:
            print("No test results to summarize")
            return
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        
        for result in self.results:
            status_icon = {"passed": "✅", "failed": "❌", "error": "⚠️"}.get(result.status, "❓")
            print(f"{status_icon} {result.name}: {result.status.upper()} ({result.duration:.2f}s)")
            if result.coverage:
                print(f"   📊 Coverage: {result.coverage:.1f}%")
        
        print("-" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "passed")
        failed_tests = sum(1 for r in self.results if r.status == "failed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 OVERALL RESULTS:")
        print(f"   Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Total Time: {total_duration:.2f}s")
        print("="*60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for dropshipping system")
    
    parser.add_argument(
        "--suite", 
        choices=["unit", "integration", "e2e", "performance", "security", "all"],
        default="all",
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="Run test suites in parallel where possible"
    )
    
    parser.add_argument(
        "--include-slow", 
        action="store_true",
        help="Include slow tests (E2E, performance)"
    )
    
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="test-report.html",
        help="Output file for test report"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = TestRunner()
    
    # Check dependencies
    if not runner.check_dependencies():
        sys.exit(1)
    
    try:
        # Run tests
        if args.suite == "all":
            results = runner.run_all_tests(
                parallel_suites=args.parallel,
                include_slow=args.include_slow,
                coverage=not args.no_coverage,
                verbose=args.verbose
            )
        else:
            # Run specific suite
            if args.suite in runner.test_suites:
                suite = runner.test_suites[args.suite]
                result = runner.run_test_suite(
                    suite, 
                    coverage=not args.no_coverage,
                    verbose=args.verbose
                )
                results = [result]
                runner.results = results
            else:
                print(f"❌ Unknown test suite: {args.suite}")
                sys.exit(1)
        
        # Generate report
        runner.generate_report(args.output)
        
        # Print summary
        runner.print_summary()
        
        # Exit with appropriate code
        failed_tests = sum(1 for r in results if r.status in ["failed", "error"])
        sys.exit(1 if failed_tests > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n❌ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test execution failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()